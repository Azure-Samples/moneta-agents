from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AzureAISearchTool, FunctionTool, ToolSet
from azure.core.exceptions import HttpResponseError
from sk.skills.crm_facade import CRMFacade
from sk.skills.news_facade import NewsFacade
import yaml
from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env file
load_dotenv()


class AgentInitializer:
    def __init__(self, project_client: AIProjectClient):
        self.project_client = project_client
        self.logger = logging.getLogger(__name__)
        self.logger.debug("AI Foundry AgentInitializer init")
        

    def load_yaml(self, yaml_filename: str):
        # 1) Identify this file’s own directory
        script_dir = os.path.dirname(os.path.realpath(__file__))
        #   e.g. <...>/sk/aifoundry

        # 2) Go up one level (..) to sk/, then down into agents/banking
        #    Put the yaml_filename at the end
        absolute_path = os.path.join(
            script_dir, 
            "..",         # to go from sk/aifoundry -> sk/
            "agents", 
            "banking", 
            yaml_filename
        )

        # Normalize e.g. remove .. or . so it’s a proper absolute path
        absolute_path = os.path.normpath(absolute_path)
        self.logger.info(f"YAML abs path: {absolute_path}")
        # 3) Read the file
        if not os.path.exists(absolute_path):
            raise FileNotFoundError(f"File not found: {absolute_path}")
        
        with open(absolute_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
        
    def create_agent_cio(self, agent_definition: dict):
        self.logger.info("AI Foundry create_agent_cio init")
        # Retrieves AI Search connection from Project connections 
        # Further checks should be made if more AI Search connections were created in Foundry
        conn_list = self.project_client.connections.list()
        conn_id = ""
        for conn in conn_list:
            if conn.connection_type == "AZURE_AI_SEARCH":
                conn_id = conn.id

        ai_search = AzureAISearchTool(index_connection_id=conn_id, index_name="cio-index")

        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        agent = self.project_client.agents.create_agent(
            model=deployment_name,
            name=agent_definition["name"],
            description=agent_definition["description"],
            instructions=agent_definition["instructions"],
            temperature=agent_definition["temperature"],
            tools=ai_search.definitions,
            tool_resources=ai_search.resources,
        )
        self.logger.debug(f"Created agent, ID: {agent.id}")
        return agent
    
    def create_agent_crm(self, agent_definition: dict):
        self.logger.info("AI Foundry create_agent_crm init")
        # Initialize function tool
        functions = FunctionTool(functions=CRMFacade.crm_functions)
        toolset = ToolSet()
        toolset.add(functions)
        
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        agent = self.project_client.agents.create_agent(
            model=deployment_name,
            name=agent_definition["name"],
            description=agent_definition["description"],
            instructions=agent_definition["instructions"],
            temperature=agent_definition["temperature"],
            toolset=toolset,
        )
        self.logger.debug(f"Created agent, ID: {agent.id}")
        return agent    
        
    def create_agent_funds(self, agent_definition: dict):
        self.logger.info("AI Foundry create_agent_funds init")
        # Retrieves AI Search connection from Project connections 
        # Further checks should be made if more AI Search connections were created in Foundry
        conn_list = self.project_client.connections.list()
        conn_id = ""
        for conn in conn_list:
            if conn.connection_type == "AZURE_AI_SEARCH":
                conn_id = conn.id

        ai_search = AzureAISearchTool(index_connection_id=conn_id, index_name="funds-index")

        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        agent = self.project_client.agents.create_agent(
            model=deployment_name,
            name=agent_definition["name"],
            description=agent_definition["description"],
            instructions=agent_definition["instructions"],
            temperature=agent_definition["temperature"],
            tools=ai_search.definitions,
            tool_resources=ai_search.resources,
        )
        self.logger.debug(f"Created agent, ID: {agent.id}")
        return agent
    
    def create_agent_news(self, agent_definition: dict):
        self.logger.info("AI Foundry create_agent_news init")
        # Initialize function tool
        functions = FunctionTool(functions=NewsFacade.news_functions)
        toolset = ToolSet()
        toolset.add(functions)
        
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        agent = self.project_client.agents.create_agent(
            model=deployment_name,
            name=agent_definition["name"],
            description=agent_definition["description"],
            instructions=agent_definition["instructions"],
            temperature=agent_definition["temperature"],
            toolset=toolset,
        )
        self.logger.debug(f"Created agent, ID: {agent.id}")
        return agent    
    
    def create_agent_responder(self, agent_definition: dict):

        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        agent = self.project_client.agents.create_agent(
            model=deployment_name,
            name=agent_definition["name"],
            description=agent_definition["description"],
            instructions=agent_definition["instructions"],
        )
        self.logger.debug(f"Created agent, ID: {agent.id}")
        return agent

    def create_agent(self, agent_type:str):

        self.logger.info("AI Foundry create_agent")

        # Load agent definition from yaml files
        agent_definition = self.load_yaml(agent_type + ".yaml")

        try:
            self.logger.info("Listing all agents from Project...")
            agents_list = self.project_client.agents.list_agents()
            self.logger.info("Checking if agent already exists...")
            # If that's the case, just return it and don't create a new one
            for agent in agents_list.data:
                if agent.name == agent_definition["name"]:
                    return self.project_client.agents.get_agent(agent.id)
                
        except HttpResponseError as e:
            self.logger.error(f"create_agent: failed to list available agents: {e.status_code} ({e.reason})")
            self.logger.error(e.message)    
       

        self.logger.info("Creating agents...")
        # Create agent 
        # This could be improved to have a single create function
        if agent_type == "cio":
            return self.create_agent_cio(agent_definition)
        elif agent_type == "crm":
            return self.create_agent_crm(agent_definition)
        elif agent_type == "funds":
            return self.create_agent_funds(agent_definition)
        elif agent_type == "news":
            return self.create_agent_news(agent_definition)
        elif agent_type == "responder":
            return self.create_agent_responder(agent_definition)
            
        
            