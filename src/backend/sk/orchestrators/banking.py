import logging
import os
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from semantic_kernel.agents import AgentGroupChat
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.agents.strategies.termination.termination_strategy import TerminationStrategy
from semantic_kernel.agents.strategies import KernelFunctionSelectionStrategy
from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from semantic_kernel.kernel import Kernel
from semantic_kernel.functions import KernelPlugin, KernelFunctionFromPrompt

from sk.orchestrators.semantic_orchestrator import SemanticOrchastrator

from semantic_kernel.connectors.ai.azure_ai_inference import AzureAIInferenceChatCompletion
import azure.ai.inference.aio as aio_inference
import azure.identity.aio as aio_identity

import asyncio
from azure.ai.projects import AIProjectClient
from sk.aifoundry.agent_initialiazer import AgentInitializer

class BankingOrchestrator(SemanticOrchastrator):
    def __init__(self):
        super().__init__()
        self.logger.setLevel(logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Banking Orchestrator init")
        
        # Initialize required services and kernel
        # self.crm = CRMFacade(
        #     key=DefaultAzureCredential(),
        #     cosmosdb_endpoint=os.getenv("COSMOSDB_ENDPOINT"),
        #     crm_database_name=os.getenv("COSMOSDB_DATABASE_NAME"),
        #     crm_container_name=os.getenv("COSMOSDB_CONTAINER_CLIENT_NAME"))

        # self.product = FundsFacade(
        #     credential=DefaultAzureCredential(),
        #     service_endpoint=os.getenv('AI_SEARCH_ENDPOINT'),
        #     index_name=os.getenv('AI_SEARCH_FUNDS_INDEX_NAME'),
        #     semantic_configuration_name="default")

        # self.cio = CIOFacade(
        #     credential=DefaultAzureCredential(),
        #     service_endpoint=os.getenv('AI_SEARCH_ENDPOINT'),
        #     index_name=os.getenv('AI_SEARCH_CIO_INDEX_NAME'),
        #     semantic_configuration_name="default")
        
        # self.news = NewsFacade()
        
        self.kernel = Kernel(
            services=[self.gpt4o_service],
            # plugins=[
            #     KernelPlugin.from_object(plugin_instance=self.crm, plugin_name="crm"),
            #     KernelPlugin.from_object(plugin_instance=self.product, plugin_name="funds"),
            #     KernelPlugin.from_object(plugin_instance=self.cio, plugin_name="cio"),
            #     KernelPlugin.from_object(plugin_instance=self.news, plugin_name="news"),
            # ]
        )

    # --------------------------------------------
    # Selection Strategy
    # --------------------------------------------
    def create_selection_strategy(self, agents, default_agent):
        """Speaker selection strategy for the agent group chat."""
        definitions = "\n".join([f"{agent.name}: {agent.description}" for agent in agents])
        selection_function = KernelFunctionFromPrompt(
                function_name="SpeakerSelector",
                prompt_execution_settings=AzureChatPromptExecutionSettings(
                    temperature=0),
                prompt=fr"""
                    You are the next speaker selector.

                    - You MUST return ONLY agent name from the list of available agents below.
                    - You MUST return the agent name and nothing else.
                    - Check the history, if any, and decide WHAT agent is the best next speaker
                    - The names are case-sensitive and should not be abbreviated or changed.
                    - YOU MUST OBSERVE AGENT USAGE INSTRUCTIONS.

# AVAILABLE AGENTS

{definitions}

# CHAT HISTORY

{{{{$history}}}}
""")

        # Could be lambda. Keeping as function for clarity
        def parse_selection_output(output):
            self.logger.debug(f"Parsing selection: {output}")
            if output.value is not None:
                return output.value[0].content
            return default_agent.name

        return KernelFunctionSelectionStrategy(
                    kernel=self.kernel,
                    function=selection_function,
                    result_parser=parse_selection_output,
                    agent_variable_name="agents",
                    history_variable_name="history")

    # --------------------------------------------
    # Termination Strategy
    # --------------------------------------------
    def create_termination_strategy(self, agents, final_agent, maximum_iterations):
        """
        Create a chat termination strategy that terminates when the final agent is reached.
        params:
            agents: List of agents to trigger termination evaluation
            final_agent: The agent that should trigger termination
            maximum_iterations: Maximum number of iterations before termination
        """
        class CompletionTerminationStrategy(TerminationStrategy):
            async def should_agent_terminate(self, agent, history):
                """Terminate if the last actor is the Responder Agent."""
                logging.getLogger(__name__).debug(history[-1])
                return (agent.name == final_agent.name)

        return CompletionTerminationStrategy(agents=agents,
                                             maximum_iterations=maximum_iterations)

    # --------------------------------------------
    # Create Agent Group Chat - LEGACY:without AI Foundry
    # --------------------------------------------
    # def create_agent_group_chat(self):
    #     self.logger.debug("Creating chat")

    #     crm_agent = self.create_agent(service_id="gpt-4o",
    #                                   kernel=self.kernel,
    #                                   definition_file_path="sk/agents/banking/crm.yaml")
    #     funds_agent = self.create_agent(service_id="gpt-4o",
    #                                   kernel=self.kernel,
    #                                   definition_file_path="sk/agents/banking/funds.yaml")
    #     cio_agent = self.create_agent(service_id="gpt-4o",
    #                                   kernel=self.kernel,
    #                                   definition_file_path="sk/agents/banking/cio.yaml")
    #     news_agent = self.create_agent(service_id="gpt-4o",
    #                                   kernel=self.kernel,
    #                                   definition_file_path="sk/agents/banking/news.yaml")
    #     responder_agent = self.create_agent(service_id="gpt-4o",
    #                                   kernel=self.kernel,
    #                                   definition_file_path="sk/agents/banking/responder.yaml")

    #     agents = [crm_agent, funds_agent, cio_agent, news_agent, responder_agent]

    #     agent_group_chat = AgentGroupChat(
    #         agents=agents,
    #         selection_strategy=self.create_selection_strategy(agents, responder_agent),
    #         termination_strategy=self.create_termination_strategy(
    #             agents=[funds_agent, crm_agent, responder_agent],
    #             final_agent=responder_agent,
    #             maximum_iterations=8
    #         )
    #     )

    #     return agent_group_chat
    

    async def create_agent_group_chat(self):
        self.logger.debug("Creating chat")

        # 1) Create an AgentInitializer from the AI Foundry SDK
        # We assume you already have or can build an AIProjectClient:

        self.logger.info("Getting Foundry project")
        foundry_client = AIProjectClient.from_connection_string(
            credential = DefaultAzureCredential(),
            conn_str=os.environ["AI_PROJECT_CONNECTION_STRING"],
            logging_enable = True
        )
        self.logger.info(f"Foundry project = {foundry_client}")
        agent_initializer = AgentInitializer(foundry_client)

        # List all agents from Project
        agents_list = foundry_client.agents.list_agents()

        # Check if agent already exists
        for agent in agents_list.data:
            foundry_client.agents.delete_agent(agent.id)

        self.logger.debug("All agents deleted")

        # 2) For each agent type, create the SK ChatCompletionAgent from Foundry
        crm_agent = await self.create_agent_from_foundry(
            kernel=self.kernel, 
            service_id="gpt-4o", 
            agent_initializer=agent_initializer, 
            agent_type="crm",
            foundry_client=foundry_client
        )
        funds_agent = await self.create_agent_from_foundry(
            kernel=self.kernel, 
            service_id="gpt-4o", 
            agent_initializer=agent_initializer, 
            agent_type="funds",
            foundry_client=foundry_client
        )
        cio_agent = await self.create_agent_from_foundry(
            kernel=self.kernel, 
            service_id="gpt-4o", 
            agent_initializer=agent_initializer, 
            agent_type="cio",
            foundry_client=foundry_client
        )
        news_agent = await self.create_agent_from_foundry(
            kernel=self.kernel, 
            service_id="gpt-4o", 
            agent_initializer=agent_initializer, 
            agent_type="news",
            foundry_client=foundry_client
        )
        responder_agent = await self.create_agent_from_foundry(
            kernel=self.kernel, 
            service_id="gpt-4o", 
            agent_initializer=agent_initializer, 
            agent_type="responder",
            foundry_client=foundry_client
        )

        agents = [crm_agent, funds_agent, cio_agent, news_agent, responder_agent]

        # 3) Build the selection strategy as you do now
        selection_strategy = self.create_selection_strategy(agents, responder_agent)

        # 4) Build the termination strategy
        termination_strategy = self.create_termination_strategy(
            agents=[funds_agent, crm_agent, responder_agent],
            final_agent=responder_agent,
            maximum_iterations=8
        )

        # 5) Create the AgentGroupChat
        agent_group_chat = AgentGroupChat(
            agents=agents,
            selection_strategy=selection_strategy,
            termination_strategy=termination_strategy
        )

        return agent_group_chat
