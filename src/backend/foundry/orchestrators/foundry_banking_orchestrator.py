"""
Moneta Banking Orchestrator - Microsoft Foundry Implementation
Multi-agent orchestration using HandoffBuilder pattern for banking services.

This orchestrator coordinates three specialized agents:
1. CRM Agent - Client data and portfolio information
2. CIO Agent - Investment research and market analysis
3. Funds Agent - Funds and ETFs information
4. News Agent - Investment news for stock positions

The orchestration uses the Handoff pattern where a coordinator agent routes
user requests to appropriate specialist agents.

This implementation uses Microsoft Foundry with hosted agents (AzureAIClient).
For Azure OpenAI in-memory agents, use OpenAIBankingOrchestrator instead.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional

# Microsoft Agent Framework imports
from agent_framework import (
    ChatAgent,
    ChatMessage,
    HandoffBuilder,
    RequestInfoEvent,
    WorkflowOutputEvent,
    WorkflowEvent,
    ExecutorCompletedEvent
)
from agent_framework._workflows._events import AgentRunEvent
from agent_framework.azure import AzureAIAgentClient, AzureAIClient
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

# Import specialist agent functions from banking agents subfolder
from foundry.agents.banking.crm.crm_functions import crm_functions
from foundry.agents.banking.cio.cio_functions import cio_functions
from foundry.agents.banking.funds.funds_functions import funds_functions
from foundry.agents.banking.news.news_functions import news_functions

# Import agent management for Foundry mode
from foundry.agents.agent_management import AgentManager

# Import tool schema utilities for Foundry tool registration
from foundry.agents.tool_schema_utils import functions_to_tool_schemas

# Load environment
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)

# Setup tracing for App Insights + Foundry UI
from tracing import setup_tracing, get_tracer, set_conversation_context, clear_conversation_context
setup_tracing()
_tracer = get_tracer("moneta-foundry-banking-orchestrator")


# Agent definitions
# Names must be valid for Foundry API: alphanumeric + hyphens, no underscores
# Using 'bank-' prefix to distinguish from insurance agents
AGENT_DEFINITIONS = {
    "bank-coordinator": {
        "name": "bank-coordinator",
        "instructions": (
            "You are the Moneta Banking Coordinator. Analyze customer requests and route them to the appropriate specialist:\n"
            "- bank-crm-agent: For client data, portfolio information, account details, customer inquiries. "
            "Use when the request mentions a specific client name or ID.\n"
            "- bank-cio-agent: For investment research, market analysis, CIO views, strategic investment recommendations.\n"
            "- bank-funds-agent: For information about funds, ETFs, fund performance, and investment products.\n"
            "- bank-news-agent: For fetching latest investment news for specific stock positions/tickers.\n"
            "\n"
            "When you receive a request, immediately call the matching handoff tool "
            "(handoff_to_bank-crm-agent, handoff_to_bank-cio-agent, handoff_to_bank-funds-agent, or handoff_to_bank-news-agent) without explaining."
        ),
        "description": "Moneta Banking Coordinator - routes requests to specialist agents"
    },
    "bank-crm-agent": {
        "name": "bank-crm-agent",
        "instructions": (
            "You are a CRM specialist. Help with client data and portfolio information. "
            "Use your CRM functions to retrieve accurate customer data. "
            "ONLY use the provided functions - don't guess or use general knowledge. "
            "If client ID or name is not provided, politely inform the user that you need this information."
        ),
        "description": "CRM Banking Agent - handles client data and portfolio information"
    },
    "bank-cio-agent": {
        "name": "bank-cio-agent",
        "instructions": (
            "You are a Chief Investment Office specialist. Provide investment research and strategic insights. "
            "Use the search function to find relevant CIO views and market analysis. "
            "Provide CONCISE and actionable investment recommendations."
        ),
        "description": "CIO Agent - provides investment research and market analysis"
    },
    "bank-funds-agent": {
        "name": "bank-funds-agent",
        "instructions": (
            "You are a Funds specialist. Provide information about investment funds and ETFs. "
            "Use the search function to find relevant fund information. "
            "Explain fund characteristics, performance, and suitability clearly and concisely."
        ),
        "description": "Funds Agent - provides funds and ETF information"
    },
    "bank-news-agent": {
        "name": "bank-news-agent",
        "instructions": (
            "You are a News specialist for Moneta Banking. "
            "You fetch and analyze the latest investment news for specific stock positions. "
            "Use the fetch_news function to retrieve news for stock ticker symbols. "
            "When presenting news, summarize the key headlines and their potential impact on the portfolio."
        ),
        "description": "News Agent - fetches investment news for portfolio positions"
    }
}


class FoundryBankingOrchestrator:
    """
    Foundry Banking Orchestrator with hosted agents.
    
    This orchestrator uses Microsoft Agent Framework with HandoffBuilder pattern
    for multi-agent coordination in banking services using Microsoft Foundry.
    """
    
    def __init__(self):
        """
        Initialize the Foundry Banking Orchestrator.
        Uses Microsoft Foundry mode with hosted agents.
        """
        import logging
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Foundry Banking Orchestrator init")
        
        self._workflow = None
        self._initialized = False
        
        # Configuration from environment
        self.foundry_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("PROJECT_ENDPOINT")
        self.foundry_deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")

    async def _ensure_initialized(self):
        """Lazily initialize the workflow and agents."""
        if self._initialized:
            return
        
        credential = AzureCliCredential()
        
        # Foundry mode - use hosted agents via AzureAIClient
        if not self.foundry_endpoint:
            raise ValueError(
                "AZURE_AI_PROJECT_ENDPOINT or PROJECT_ENDPOINT is required for Foundry mode."
            )
        
        self.logger.info(f"Using Foundry endpoint for workflow: {self.foundry_endpoint}")
        
        # Use existing Foundry-hosted agents (requires agents to be pre-created)
        coordinator, crm_agent, cio_agent, funds_agent, news_agent = await create_foundry_agents(
            project_endpoint=self.foundry_endpoint,
            credential=credential,
            model_deployment_name=self.foundry_deployment_name,
            use_latest_version=True
        )
        
        # Build the handoff workflow
        self._workflow = (
            HandoffBuilder(
                name="moneta_banking_handoff",
                participants=[coordinator, crm_agent, cio_agent, funds_agent, news_agent],
            )
            .with_start_agent(coordinator)
            .with_termination_condition(
                lambda conv: sum(1 for msg in conv if msg.role.value == "user") >= 10
            )
            .build()
        )
        
        self._initialized = True
        self.logger.info("✅ Foundry Banking Orchestrator initialized (Foundry hosted agents)")
    
    async def process_conversation(self, user_id: str, conversation_messages: list, session_id: str = None) -> dict:
        """
        Process a conversation and return the agent's reply.
        
        Args:
            user_id: The user identifier
            conversation_messages: List of message dicts with 'role', 'name', 'content' keys
            session_id: Session/chat ID for tracing (typically the chat_id)
            
        Returns:
            Dict with 'role', 'name', 'content' keys representing the agent's reply
        """
        await self._ensure_initialized()
        
        # Use session_id for tracing, generate one if not provided
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())[:8]
        
        self.logger.info(f"Processing conversation with session_id: {session_id}")
        
        # Convert conversation history to ChatMessage objects for the workflow
        chat_messages = []
        for msg in conversation_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            author_name = msg.get('name')
            
            if content:
                chat_msg = ChatMessage(
                    role=role,
                    text=content,
                    author_name=author_name
                )
                chat_messages.append(chat_msg)
        
        if not chat_messages:
            return {
                'role': 'assistant',
                'name': 'coordinator',
                'content': 'I didn\'t receive a message. How can I help you?'
            }
        
        self.logger.info(f"Injecting {len(chat_messages)} messages as conversation history")
        
        try:
            from opentelemetry.trace import SpanKind
            
            # Set conversation context for attribute propagation to child agent spans
            set_conversation_context(
                conversation_id=session_id,
                user_id=user_id,
                mode="foundry"
            )
            
            with _tracer.start_as_current_span(
                "banking_conversation",
                kind=SpanKind.SERVER,
                attributes={
                    "gen_ai.conversation.id": session_id,
                    "gen_ai.operation.name": "invoke_agent",
                    "gen_ai.provider.name": "microsoft.foundry",
                    "gen_ai.agent.name": "banking_coordinator",
                    "session.id": session_id,
                    "user.id": user_id,
                    "session.mode": "foundry",
                    "conversation.message_count": len(chat_messages)
                }
            ) as session_span:
                final_response = ""
                responding_agent = "bank-coordinator"
                
                async for event in self._workflow.run_stream(chat_messages):
                    if isinstance(event, RequestInfoEvent):
                        # Handle HandoffAgentUserRequest with agent_response
                        if hasattr(event.data, 'agent_response') and event.data.agent_response:
                            agent_response = event.data.agent_response
                            if hasattr(agent_response, 'text') and agent_response.text:
                                final_response = agent_response.text
                                responding_agent = event.source_executor_id or "bank-coordinator"
                    
                    elif isinstance(event, ExecutorCompletedEvent):
                        if event.data is not None:
                            if hasattr(event.data, 'text') and event.data.text:
                                final_response = event.data.text
                                responding_agent = event.executor_id or "bank-coordinator"
                
                self.logger.info(f"Final response: {len(final_response)} chars from '{responding_agent}'")
                
                session_span.set_attribute("response.agent", responding_agent)
                session_span.set_attribute("response.length", len(final_response))
                
                return {
                    'role': 'assistant',
                    'name': responding_agent,
                    'content': final_response or 'I apologize, but I was unable to generate a response.'
                }
            
        except Exception as e:
            self.logger.error(f"Error processing conversation: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'role': 'assistant',
                'name': 'coordinator',
                'content': f'I encountered an error while processing your request. Please try again.'
            }
        finally:
            clear_conversation_context()


async def get_existing_agent_ids(
    project_endpoint: str,
    credential: AzureCliCredential
) -> dict[str, str]:
    """
    Get IDs of existing agents in the Foundry project.
    
    Returns:
        Dictionary mapping agent names to their IDs (most recent version)
    """
    from azure.ai.agents.aio import AgentsClient
    
    agent_ids = {}
    async with AgentsClient(endpoint=project_endpoint, credential=credential) as client:
        async for agent in client.list_agents():
            if agent.name and agent.id:
                if agent.name not in agent_ids:
                    agent_ids[agent.name] = agent.id
    
    return agent_ids


async def create_persistent_foundry_agents(
    project_endpoint: str,
    credential: AzureCliCredential,
    model_deployment_name: str
) -> tuple[ChatAgent, ChatAgent, ChatAgent, ChatAgent, ChatAgent]:
    """
    Create persistent agents in Microsoft Foundry using AgentManager, then wrap them
    with ChatAgent for use in the orchestrator workflow.
    
    This creates actual Foundry-hosted agents that are visible in the Foundry UI
    and persist across sessions.
    
    Args:
        project_endpoint: The Azure AI Project endpoint URL
        credential: Azure credential for authentication
        model_deployment_name: The model deployment name to use
        
    Returns:
        Tuple of (coordinator, crm_agent, cio_agent, funds_agent, news_agent)
    """
    print(f"\n🔧 Creating persistent Foundry agents...")
    print(f"   Agents will be visible in Foundry UI")
    print(f"   Tools are registered with Foundry and bound locally for execution")
    print()
    
    agents = []
    
    specialist_agent_names = ["bank-crm-agent", "bank-cio-agent", "bank-funds-agent", "bank-news-agent"]
    
    async with AgentManager() as manager:
        for agent_key in ["bank-coordinator", "bank-crm-agent", "bank-cio-agent", "bank-funds-agent", "bank-news-agent"]:
            agent_def = AGENT_DEFINITIONS[agent_key]
            
            tools = None
            tool_schemas = None
            
            # Coordinator gets no tools here - HandoffBuilder will add handoff tools automatically
            if agent_key == "bank-crm-agent":
                tools = crm_functions
                tool_schemas = functions_to_tool_schemas(tools)
                print(f"   📦 {agent_key}: Registering {len(tool_schemas)} tools with Foundry")
            elif agent_key == "bank-cio-agent":
                tools = cio_functions
                tool_schemas = functions_to_tool_schemas(tools)
                print(f"   📦 {agent_key}: Registering {len(tool_schemas)} tools with Foundry")
            elif agent_key == "bank-funds-agent":
                tools = funds_functions
                tool_schemas = functions_to_tool_schemas(tools)
                print(f"   📦 {agent_key}: Registering {len(tool_schemas)} tools with Foundry")
            elif agent_key == "bank-news-agent":
                tools = news_functions
                tool_schemas = functions_to_tool_schemas(tools)
                print(f"   📦 {agent_key}: Registering {len(tool_schemas)} tools with Foundry")
            
            agent_name = agent_def["name"]
            
            foundry_agent = await manager.create_agent(
                agent_name=agent_name,
                instructions=agent_def["instructions"],
                model=model_deployment_name,
                tools=tool_schemas
            )
            
            print(f"✅ Created in Foundry: {foundry_agent['name']} (ID: {foundry_agent['id']})")
            
            client = AzureAIClient(
                project_endpoint=project_endpoint,
                model_deployment_name=model_deployment_name,
                credential=credential,
                agent_name=agent_name,
                use_latest_version=True
            )
            
            agent = client.as_agent(
                name=agent_key,
                instructions=agent_def["instructions"],
                tools=tools
            )
            
            agents.append(agent)
    
    print(f"\n✅ All {len(agents)} agents created and registered in Foundry")
    return tuple(agents)


async def create_foundry_agents(
    project_endpoint: str,
    credential: AzureCliCredential,
    model_deployment_name: str,
    agent_version: str | None = None,
    use_latest_version: bool = True,
    force_new_version: bool = False
) -> tuple[ChatAgent, ChatAgent, ChatAgent, ChatAgent, ChatAgent]:
    """
    Create or reuse agents using AzureAIClient (v2 API) for Microsoft Foundry project.
    
    Args:
        project_endpoint: The Azure AI Project endpoint URL
        credential: Azure credential for authentication
        model_deployment_name: The model deployment name to use
        agent_version: Specific agent version to use (e.g., "1.0")
        use_latest_version: If True, use latest existing version in Foundry
        force_new_version: If True, create new version even if agent exists
        
    Returns:
        Tuple of (coordinator, crm_agent, cio_agent, funds_agent, news_agent)
    """
    agents = []
    
    print(f"\n🔧 Agent Configuration:")
    print(f"   agent_version: {agent_version or 'auto'}")
    print(f"   use_latest_version: {use_latest_version}")
    print(f"   force_new_version: {force_new_version}")
    print()
    
    specialist_agent_names = ["bank-crm-agent", "bank-cio-agent", "bank-funds-agent", "bank-news-agent"]
    
    for agent_key in ["bank-coordinator", "bank-crm-agent", "bank-cio-agent", "bank-funds-agent", "bank-news-agent"]:
        agent_def = AGENT_DEFINITIONS[agent_key]
        tools = None
        
        # Coordinator gets no tools here - HandoffBuilder will add handoff tools automatically
        if agent_key == "bank-crm-agent":
            tools = crm_functions
        elif agent_key == "bank-cio-agent":
            tools = cio_functions
        elif agent_key == "bank-funds-agent":
            tools = funds_functions
        elif agent_key == "bank-news-agent":
            tools = news_functions
        
        agent_name = agent_def["name"]
        
        client = AzureAIClient(
            project_endpoint=project_endpoint,
            model_deployment_name=model_deployment_name,
            credential=credential,
            agent_name=agent_name,
            agent_version=agent_version if not use_latest_version else None,
            use_latest_version=use_latest_version and not force_new_version
        )
        
        agent = client.as_agent(
            name=agent_key,
            instructions=agent_def["instructions"],
            tools=tools
        )
        
        version_info = f"v{agent_version}" if agent_version else ("latest" if use_latest_version else "new")
        print(f"✅ Agent ready: {agent_name} ({version_info})")
        
        agents.append(agent)
    
    return tuple(agents)


async def handle_workflow_events(events: list[WorkflowEvent]) -> list[RequestInfoEvent]:
    """
    Process workflow events and return any pending input requests.
    
    Args:
        events: List of workflow events to process
        
    Returns:
        List of pending input requests
    """
    pending_requests = []
    
    for event in events:
        if isinstance(event, RequestInfoEvent):
            pending_requests.append(event)
            request_data = event.data
            awaiting_agent = request_data.awaiting_agent_id.upper()
            
            print(f"\n{'='*60}")
            print(f"AWAITING INPUT FROM: {awaiting_agent}")
            print(f"{'='*60}")
            
            for msg in request_data.conversation[-3:]:
                author = msg.author_name or msg.role.value
                print(f"    [{author}]: {msg.text}")
                
        elif isinstance(event, WorkflowOutputEvent):
            print("\n✅ Workflow completed!")
            
    return pending_requests


async def main():
    """
    Main function to initialize and run the Foundry Banking orchestrator.
    Uses Microsoft Foundry mode with hosted agents.
    
    Foundry mode supports agent versioning:
    - --version X.Y: Use specific agent version
    - --latest: Use latest existing version (default)
    - --force-new: Create new version even if agents exist
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Moneta Banking Multi-Agent Orchestrator (Foundry)")
    parser.add_argument("--new", action="store_true", help="Create new persistent agents in Foundry")
    parser.add_argument("--version", type=str, default=None, help="Specific agent version to use (e.g., 1.0)")
    parser.add_argument("--latest", action="store_true", default=True, help="Use latest existing version (default)")
    parser.add_argument("--force-new-version", action="store_true", help="Create new version even if agents exist")
    
    args = parser.parse_args()
    
    use_existing = not args.new
    agent_version = args.version
    use_latest_version = args.latest and agent_version is None
    force_new_version = args.force_new_version
    
    os.system('cls' if os.name=='nt' else 'clear')
    
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("PROJECT_ENDPOINT")
    deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")
    
    print("🏗️  Using Microsoft Foundry mode (hosted agents)")
    
    if not endpoint:
        print("❌ Error: AZURE_AI_PROJECT_ENDPOINT or PROJECT_ENDPOINT is required")
        return
    
    try:
        async with AzureCliCredential() as credential:
            if not use_existing:
                print("📝 Creating new persistent agents in Foundry...")
                coordinator, crm_agent, cio_agent, funds_agent, news_agent = await create_persistent_foundry_agents(
                    project_endpoint=endpoint,
                    credential=credential,
                    model_deployment_name=deployment_name
                )
            else:
                coordinator, crm_agent, cio_agent, funds_agent, news_agent = await create_foundry_agents(
                    project_endpoint=endpoint,
                    credential=credential,
                    model_deployment_name=deployment_name,
                    agent_version=agent_version,
                    use_latest_version=use_latest_version,
                    force_new_version=force_new_version
                )
            
            await run_workflow(coordinator, crm_agent, cio_agent, funds_agent, news_agent)
    
    except Exception as e:
        print(f"❌ Failed to initialize orchestrator: {str(e)}")
        import traceback
        traceback.print_exc()


async def run_workflow(
    coordinator: ChatAgent,
    crm_agent: ChatAgent,
    cio_agent: ChatAgent,
    funds_agent: ChatAgent,
    news_agent: ChatAgent
):
    """
    Run the multi-agent workflow with the given agents.
    """
    import uuid
    from opentelemetry.trace import SpanKind
    
    session_id = str(uuid.uuid4())[:8]
    
    workflow = (
        HandoffBuilder(
            name="moneta_banking_handoff",
            participants=[coordinator, crm_agent, cio_agent, funds_agent, news_agent],
        )
        .with_start_agent(coordinator)
        .with_termination_condition(
            lambda conv: sum(1 for msg in conv if msg.role.value == "user") >= 10
        )
        .build()
    )
    
    print("\n" + "="*60)
    print("🏦 MONETA BANKING MULTI-AGENT ORCHESTRATOR")
    print("   Mode: Microsoft Foundry (hosted agents)")
    print(f"   Session ID: {session_id}")
    print("="*60)
    print("\n🎭 Orchestrator with Specialist Agents:")
    print("   • Coordinator - Routes your requests")
    print("   • CRM Banking Agent - Client data & portfolios")
    print("   • CIO Agent - Investment research & analysis")
    print("   • Funds Agent - Funds & ETFs information")
    print("   • News Agent - Investment news for positions")
    print("\nType 'exit' or 'quit' to end the conversation.")
    print("="*60 + "\n")
    
    turn_counter = 0
    
    with _tracer.start_as_current_span(
        "banking_session",
        kind=SpanKind.SERVER,
        attributes={
            "gen_ai.conversation.id": session_id,
            "session.id": session_id,
            "session.mode": "foundry"
        }
    ) as session_span:
        
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ["exit", "quit", "q"]:
                session_span.set_attribute("session.total_turns", turn_counter)
                session_span.set_attribute("session.status", "completed")
                print("\n👋 Thank you for using Moneta Banking Services!")
                break
            
            if not user_input:
                print("Please enter a valid query.")
                continue
            
            turn_counter += 1
            
            try:
                with _tracer.start_as_current_span(
                    f"conversation_turn_{turn_counter}",
                    kind=SpanKind.INTERNAL,
                    attributes={
                        "gen_ai.conversation.id": session_id,
                        "turn.number": turn_counter,
                        "turn.user_input": user_input[:500],
                        "session.id": session_id
                    }
                ) as turn_span:
                    handoffs = []
                    
                    events = [event async for event in workflow.run_stream(user_input)]
                    
                    for event in events:
                        if isinstance(event, RequestInfoEvent):
                            if hasattr(event, 'data') and hasattr(event.data, 'awaiting_agent_id'):
                                handoffs.append(event.data.awaiting_agent_id)
                    
                    pending_requests = await handle_workflow_events(events)
                    
                    if handoffs:
                        turn_span.set_attribute("turn.handoffs", ",".join(handoffs))
                        turn_span.set_attribute("turn.handoff_count", len(handoffs))
                
                while pending_requests:
                    user_response = input("\nYou: ").strip()
                    if not user_response:
                        break
                    
                    with _tracer.start_as_current_span(
                        f"followup_turn_{turn_counter}",
                        kind=SpanKind.INTERNAL,
                        attributes={
                            "gen_ai.conversation.id": session_id,
                            "turn.number": turn_counter,
                            "turn.is_followup": True,
                            "turn.user_input": user_response[:500],
                            "session.id": session_id
                        }
                    ):
                        responses = {req.request_id: user_response for req in pending_requests}
                        events = [event async for event in workflow.send_responses_streaming(responses)]
                        pending_requests = await handle_workflow_events(events)
                
                print()
                
            except Exception as e:
                print(f"❌ Error processing request: {str(e)}")
                session_span.set_attribute("session.has_errors", True)
                session_span.record_exception(e)
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
