import logging
import os
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from semantic_kernel.agents import AgentGroupChat
from semantic_kernel.agents.strategies.termination.termination_strategy import TerminationStrategy
from semantic_kernel.agents.strategies import KernelFunctionSelectionStrategy
from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from semantic_kernel.kernel import Kernel
from semantic_kernel.functions import KernelPlugin, KernelFunctionFromPrompt

from sk.skills.crm_facade import CRMFacade
from sk.skills.funds_facade import FundsFacade
from sk.skills.cio_facade import CIOFacade
from sk.orchestrators.semantic_orchestrator import SemanticOrchastrator

class BankingOrchestrator(SemanticOrchastrator):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Banking Orchestrator init")
        
        
        # Initialize required services and kernel
        self.crm = CRMFacade(
            key=DefaultAzureCredential(),
            cosmosdb_endpoint=os.getenv("COSMOSDB_ENDPOINT"),
            crm_database_name=os.getenv("COSMOSDB_DATABASE_NAME"),
            crm_container_name=os.getenv("COSMOSDB_CONTAINER_CLIENT_NAME"))

        self.product = FundsFacade(
            credential=DefaultAzureCredential(),
            service_endpoint=os.getenv('AI_SEARCH_ENDPOINT'),
            index_name=os.getenv('AI_SEARCH_FUNDS_INDEX_NAME'),
            semantic_configuration_name=os.getenv('AI_SEARCH_FUNDS_SEMANTIC_CONFIGURATION'))

        self.cio = CIOFacade(
            credential=DefaultAzureCredential(),
            service_endpoint=os.getenv('AI_SEARCH_ENDPOINT'),
            index_name=os.getenv('AI_SEARCH_CIO_INDEX_NAME'),
            semantic_configuration_name=os.getenv('AI_SEARCH_CIO_SEMANTIC_CONFIGURATION'))

        
        gpt4o_service = AzureChatCompletion(service_id="gpt-4o",
                                            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                                            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                                            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                                            ad_token_provider=get_bearer_token_provider(DefaultAzureCredential(),"https://cognitiveservices.azure.com/.default"))

        self.kernel = Kernel(
            services=[gpt4o_service],
            plugins=[
                KernelPlugin.from_object(plugin_instance=self.crm, plugin_name="crm"),
                KernelPlugin.from_object(plugin_instance=self.product, plugin_name="funds"),
                KernelPlugin.from_object(plugin_instance=self.cio, plugin_name="cio"),
            ]
        )

    # --------------------------------------------
    # Selection Strategy
    # --------------------------------------------
    def create_selection_strategy(self, agents, default_agent):
        """Speaker selection strategy for the agent group chat."""
        definitions = "\n".join([f"{agent.name}: {agent.description}" for agent in agents])
        selection_function = KernelFunctionFromPrompt(
                function_name="selection",
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
    # Create Agent Group Chat
    # --------------------------------------------
    def create_agent_group_chat(self):
        self.logger.debug("Creating chat")

        crm_agent = self.create_agent(service_id="gpt-4o",
                                      kernel=self.kernel,
                                      definition_file_path="sk/agents/banking/crm.yaml")
        funds_agent = self.create_agent(service_id="gpt-4o",
                                      kernel=self.kernel,
                                      definition_file_path="sk/agents/banking/funds.yaml")
        cio_agent = self.create_agent(service_id="gpt-4o",
                                      kernel=self.kernel,
                                      definition_file_path="sk/agents/banking/cio.yaml")
        responder_agent = self.create_agent(service_id="gpt-4o",
                                      kernel=self.kernel,
                                      definition_file_path="sk/agents/banking/responder.yaml")

        agents = [crm_agent, funds_agent, cio_agent, responder_agent]

        agent_group_chat = AgentGroupChat(
            agents=agents,
            selection_strategy=self.create_selection_strategy(agents, responder_agent),
            termination_strategy=self.create_termination_strategy(
                agents=[funds_agent, crm_agent, responder_agent],
                final_agent=responder_agent,
                maximum_iterations=8
            )
        )

        return agent_group_chat