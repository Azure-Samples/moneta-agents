#!/usr/bin/env python3
"""
Agent Management Utility for Microsoft Foundry Project.

This utility provides functions to list, create, get, and delete agents
in a Microsoft Foundry (Azure AI Foundry) project. It supports both
the Agent Framework and direct Azure AI Projects SDK operations.

Usage:
    python agent_management.py                     # List all agents
    python agent_management.py list                # List all agents
    python agent_management.py get <agent_name>    # Get agent details
    python agent_management.py delete <agent_name> # Delete agent by name
    python agent_management.py delete-all          # Delete all agents (with confirmation)
"""

import os
import sys
import asyncio
from typing import Optional, Any
from pathlib import Path
from dotenv import load_dotenv

# Azure SDK imports
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.core.exceptions import ResourceNotFoundError


class AgentManager:
    """
    Manager class for Microsoft Foundry Project agents.
    
    Provides functionality to list, create, get, and delete agents
    in a Microsoft Foundry project.
    """
    
    def __init__(
        self,
        project_endpoint: Optional[str] = None,
        model_deployment_name: Optional[str] = None,
        env_path: Optional[str] = None
    ):
        """
        Initialize the AgentManager.
        
        Args:
            project_endpoint: The Azure AI Project endpoint URL.
                             Falls back to AZURE_AI_PROJECT_ENDPOINT or AZURE_OPENAI_ENDPOINT env vars.
            model_deployment_name: The model deployment name.
                                   Falls back to AZURE_AI_MODEL_DEPLOYMENT_NAME or AZURE_OPENAI_DEPLOYMENT env vars.
            env_path: Path to .env file. Defaults to searching in parent directories.
        """
        # Load environment variables
        if env_path:
            load_dotenv(dotenv_path=env_path)
        else:
            # Try to find .env in current and parent directories
            current_dir = Path(__file__).parent
            for i in range(3):  # Check up to 3 levels
                env_file = current_dir / ".env"
                if env_file.exists():
                    load_dotenv(dotenv_path=str(env_file))
                    break
                current_dir = current_dir.parent
        
        # Get Foundry configuration from environment 
        self.project_endpoint = (
            project_endpoint or 
            os.getenv("PROJECT_ENDPOINT")
        )
        self.model_deployment_name = (
            model_deployment_name or 
            os.getenv("MODEL_DEPLOYMENT_NAME") 
        )
        
        self._credential: Optional[AzureCliCredential] = None
        self._project_client: Optional[AIProjectClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_client(self):
        """Ensure the project client is initialized."""
        if self._project_client is None:
            if not self.project_endpoint:
                raise ValueError(
                    "Project endpoint is required. Set AZURE_AI_PROJECT_ENDPOINT or "
                    "AZURE_OPENAI_ENDPOINT environment variable, or pass project_endpoint parameter."
                )
            
            self._credential = AzureCliCredential()
            self._project_client = AIProjectClient(
                endpoint=self.project_endpoint,
                credential=self._credential
            )
    
    async def close(self):
        """Close the client connections."""
        if self._project_client:
            await self._project_client.close()
            self._project_client = None
        if self._credential:
            await self._credential.close()
            self._credential = None
    
    async def list_agents(self) -> list[dict[str, Any]]:
        """
        List all agents in the Microsoft Foundry project.
        
        Returns:
            List of agent information dictionaries.
        """
        await self._ensure_client()
        
        agents_list = []
        try:
            # Use the agents client to list agents
            async for agent in self._project_client.agents.list():
                agent_info = {
                    "name": agent.name,
                    "id": getattr(agent, "id", None),
                    "description": getattr(agent, "description", None),
                    "created_at": str(getattr(agent, "created_at", None)),
                    "versions": []
                }
                
                # Get version information if available
                if hasattr(agent, "versions"):
                    if hasattr(agent.versions, "latest"):
                        latest = agent.versions.latest
                        agent_info["latest_version"] = getattr(latest, "version", None)
                        agent_info["model"] = getattr(latest.definition, "model", None) if hasattr(latest, "definition") else None
                        if hasattr(latest, "definition") and hasattr(latest.definition, "instructions"):
                            instructions = latest.definition.instructions or ""
                            agent_info["instructions_preview"] = instructions[:100] + "..." if len(instructions) > 100 else instructions
                
                agents_list.append(agent_info)
                
        except Exception as e:
            print(f"❌ Error listing agents: {str(e)}")
            raise
        
        return agents_list
    
    async def get_agent(self, agent_name: str) -> Optional[dict[str, Any]]:
        """
        Get detailed information about a specific agent.
        
        Args:
            agent_name: The name of the agent to retrieve.
            
        Returns:
            Agent information dictionary, or None if not found.
        """
        await self._ensure_client()
        
        try:
            agent = await self._project_client.agents.get(agent_name)
            
            agent_info = {
                "name": agent.name,
                "id": getattr(agent, "id", None),
                "description": getattr(agent, "description", None),
                "created_at": str(getattr(agent, "created_at", None)),
            }
            
            # Get all versions if available
            if hasattr(agent, "versions"):
                if hasattr(agent.versions, "latest"):
                    latest = agent.versions.latest
                    agent_info["latest_version"] = getattr(latest, "version", None)
                    
                    if hasattr(latest, "definition"):
                        definition = latest.definition
                        agent_info["model"] = getattr(definition, "model", None)
                        agent_info["instructions"] = getattr(definition, "instructions", None)
                        agent_info["tools"] = getattr(definition, "tools", None)
            
            return agent_info
            
        except ResourceNotFoundError:
            return None
        except Exception as e:
            print(f"❌ Error getting agent '{agent_name}': {str(e)}")
            raise
    
    async def create_agent(
        self,
        agent_name: str,
        instructions: str,
        description: Optional[str] = None,
        model: Optional[str] = None,
        tools: Optional[list] = None
    ) -> dict[str, Any]:
        """
        Create a new agent version in the Microsoft Foundry project.
        
        Args:
            agent_name: The name of the agent to create.
            instructions: The agent's system instructions.
            description: Optional description of the agent.
            model: Model deployment name. Defaults to configured model.
            tools: Optional list of tools for the agent.
            
        Returns:
            Created agent information dictionary.
        """
        await self._ensure_client()
        
        model = model or self.model_deployment_name
        
        try:
            definition_args = {
                "model": model,
                "instructions": instructions
            }
            if tools:
                definition_args["tools"] = tools
            
            definition = PromptAgentDefinition(**definition_args)
            
            agent_version = await self._project_client.agents.create_version(
                agent_name=agent_name,
                definition=definition
            )
            
            return {
                "name": agent_version.name,
                "version": agent_version.version,
                "id": getattr(agent_version, "id", f"{agent_version.name}:{agent_version.version}"),
                "model": model,
                "instructions_preview": instructions[:100] + "..." if len(instructions) > 100 else instructions
            }
            
        except Exception as e:
            print(f"❌ Error creating agent '{agent_name}': {str(e)}")
            raise
    
    async def get_or_create_agent(
        self,
        agent_name: str,
        instructions: str,
        description: Optional[str] = None,
        model: Optional[str] = None,
        tools: Optional[list] = None,
        use_latest_version: bool = True
    ) -> dict[str, Any]:
        """
        Get an existing agent or create it if it doesn't exist.
        
        This follows the pattern recommended by Microsoft Agent Framework
        for reusing agents in production scenarios.
        
        Args:
            agent_name: The name of the agent.
            instructions: The agent's system instructions (used if creating).
            description: Optional description of the agent.
            model: Model deployment name. Defaults to configured model.
            tools: Optional list of tools for the agent.
            use_latest_version: If True, use the latest version of existing agent.
            
        Returns:
            Agent information dictionary.
        """
        await self._ensure_client()
        
        if use_latest_version:
            try:
                existing_agent = await self._project_client.agents.get(agent_name)
                if hasattr(existing_agent, "versions") and hasattr(existing_agent.versions, "latest"):
                    latest = existing_agent.versions.latest
                    return {
                        "name": existing_agent.name,
                        "version": latest.version,
                        "id": getattr(latest, "id", f"{existing_agent.name}:{latest.version}"),
                        "model": getattr(latest.definition, "model", None) if hasattr(latest, "definition") else None,
                        "reused": True
                    }
            except ResourceNotFoundError:
                pass  # Agent doesn't exist, create it
        
        # Create new agent version
        result = await self.create_agent(
            agent_name=agent_name,
            instructions=instructions,
            description=description,
            model=model,
            tools=tools
        )
        result["reused"] = False
        return result
    
    async def delete_agent(self, agent_name: str, confirm: bool = True) -> bool:
        """
        Delete an agent by name.
        
        Args:
            agent_name: The name of the agent to delete.
            confirm: If True, prompt for confirmation in interactive mode.
            
        Returns:
            True if deleted successfully, False otherwise.
        """
        await self._ensure_client()
        
        try:
            # Check if agent exists
            agent = await self.get_agent(agent_name)
            if not agent:
                print(f"❌ Agent '{agent_name}' not found")
                return False
            
            # Confirm deletion if requested
            if confirm:
                response = input(f"⚠️  Are you sure you want to delete agent '{agent_name}'? (y/N): ")
                if response.lower().strip() not in ['y', 'yes']:
                    print("❌ Deletion cancelled")
                    return False
            
            # Delete the agent
            await self._project_client.agents.delete(agent_name)
            print(f"✅ Agent '{agent_name}' deleted successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting agent '{agent_name}': {str(e)}")
            return False
    
    async def delete_agent_version(self, agent_name: str, version: str, confirm: bool = True) -> bool:
        """
        Delete a specific version of an agent.
        
        Args:
            agent_name: The name of the agent.
            version: The version to delete.
            confirm: If True, prompt for confirmation in interactive mode.
            
        Returns:
            True if deleted successfully, False otherwise.
        """
        await self._ensure_client()
        
        try:
            if confirm:
                response = input(f"⚠️  Are you sure you want to delete agent '{agent_name}' version {version}? (y/N): ")
                if response.lower().strip() not in ['y', 'yes']:
                    print("❌ Deletion cancelled")
                    return False
            
            await self._project_client.agents.delete_version(
                agent_name=agent_name,
                agent_version=version
            )
            print(f"✅ Agent '{agent_name}' version {version} deleted successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error deleting agent version: {str(e)}")
            return False
    
    async def delete_all_agents(self, confirm: bool = True) -> int:
        """
        Delete all agents in the project.
        
        Args:
            confirm: If True, prompt for confirmation.
            
        Returns:
            Number of agents deleted.
        """
        agents = await self.list_agents()
        
        if not agents:
            print("📭 No agents found to delete")
            return 0
        
        if confirm:
            print(f"\n⚠️  Found {len(agents)} agents:")
            for agent in agents:
                print(f"   - {agent['name']}")
            
            response = input(f"\n⚠️  Are you sure you want to delete ALL {len(agents)} agents? (y/N): ")
            if response.lower().strip() not in ['y', 'yes']:
                print("❌ Deletion cancelled")
                return 0
        
        deleted_count = 0
        for agent in agents:
            try:
                await self._project_client.agents.delete(agent['name'])
                print(f"✅ Deleted: {agent['name']}")
                deleted_count += 1
            except Exception as e:
                print(f"❌ Failed to delete {agent['name']}: {str(e)}")
        
        print(f"\n📊 Deleted {deleted_count}/{len(agents)} agents")
        return deleted_count


async def print_agents_table(agents: list[dict[str, Any]]):
    """Print agents in a formatted table."""
    if not agents:
        print("📭 No agents found in the project.")
        return
    
    print("\n" + "=" * 80)
    print("🔍 AGENTS IN MICROSOFT FOUNDRY PROJECT")
    print("=" * 80)
    
    for i, agent in enumerate(agents, 1):
        print(f"\n{i}. 🤖 {agent['name']}")
        if agent.get('latest_version'):
            print(f"   Version: {agent['latest_version']}")
        if agent.get('model'):
            print(f"   Model: {agent['model']}")
        if agent.get('description'):
            print(f"   Description: {agent['description']}")
        if agent.get('instructions_preview'):
            print(f"   Instructions: {agent['instructions_preview']}")
        if agent.get('created_at') and agent['created_at'] != 'None':
            print(f"   Created: {agent['created_at']}")
        print("-" * 80)
    
    print(f"\n📊 Total agents: {len(agents)}")


async def main():
    """CLI entry point for agent management."""
    args = sys.argv[1:]
    
    if not args or args[0] == "list":
        # List all agents
        async with AgentManager() as manager:
            agents = await manager.list_agents()
            await print_agents_table(agents)
    
    elif args[0] == "get" and len(args) > 1:
        # Get specific agent
        agent_name = args[1]
        async with AgentManager() as manager:
            agent = await manager.get_agent(agent_name)
            if agent:
                print(f"\n🤖 Agent: {agent['name']}")
                print("-" * 40)
                for key, value in agent.items():
                    if key != 'name' and value:
                        print(f"   {key}: {value}")
            else:
                print(f"❌ Agent '{agent_name}' not found")
    
    elif args[0] == "delete" and len(args) > 1:
        # Delete specific agent
        agent_name = args[1]
        async with AgentManager() as manager:
            await manager.delete_agent(agent_name)
    
    elif args[0] == "delete-all":
        # Delete all agents
        async with AgentManager() as manager:
            await manager.delete_all_agents()
    
    else:
        print("Usage:")
        print("  python agent_management.py                     # List all agents")
        print("  python agent_management.py list                # List all agents")
        print("  python agent_management.py get <agent_name>    # Get agent details")
        print("  python agent_management.py delete <agent_name> # Delete agent by name")
        print("  python agent_management.py delete-all          # Delete all agents")


if __name__ == "__main__":
    asyncio.run(main())
