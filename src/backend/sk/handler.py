# handlers.py
import logging
import json
import os
import yaml
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies.termination.termination_strategy import TerminationStrategy
from semantic_kernel.agents.strategies import KernelFunctionSelectionStrategy
from semantic_kernel.connectors.ai.open_ai.services.azure_chat_completion import AzureChatCompletion
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.kernel import Kernel
from semantic_kernel.functions import KernelPlugin, KernelFunctionFromPrompt

from sk.skills.crm_facade import CRMFacade
from sk.skills.product_facade import ProductFacade
from conversation_store import ConversationStore

load_dotenv(override=True)

class SemanticKernelHandler:
    def __init__(self, db):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Semantic Kernel Handler init")
        
        self.db = ConversationStore(
            key=DefaultAzureCredential(),
            url=os.getenv("COSMOSDB_ENDPOINT"),
            database_name=os.getenv("COSMOSDB_DATABASE_NAME"),
            container_name=os.getenv("COSMOSDB_CONTAINER_FSI_INS_USER_NAME"),
        )
        
        crm = CRMFacade(
                key=DefaultAzureCredential(),
                cosmosdb_endpoint=os.getenv("COSMOSDB_ENDPOINT"),
                crm_database_name=os.getenv("COSMOSDB_DATABASE_NAME"),
                crm_container_name=os.getenv("COSMOSDB_CONTAINER_CLIENT_NAME"))
        
        product = ProductFacade(
            credential=DefaultAzureCredential(),
            service_endpoint = os.getenv('AI_SEARCH_ENDPOINT'),
            index_name = os.getenv('AI_SEARCH_INS_INDEX_NAME'),
            semantic_configuration_name = os.getenv('AI_SEARCH_INS_SEMANTIC_CONFIGURATION'))

        gpt4o_service = AzureChatCompletion(service_id="gpt-4o",
                                            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                                            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                                            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                                            api_key=os.getenv("AZURE_OPENAI_KEY"))
        
        self.kernel = Kernel(
            services=[gpt4o_service],
            plugins=[
                KernelPlugin.from_object(plugin_instance=crm, plugin_name="crm"),
                KernelPlugin.from_object(plugin_instance=product, plugin_name="product"),
            ])
        
        
    def create_agent(self, service_id, definition_file_path):
        
        with open(definition_file_path, 'r') as file:
            definition = yaml.safe_load(file)

        return ChatCompletionAgent(
            service_id=service_id,
            kernel=self.kernel,
            name=definition['name'],
            execution_settings=AzureChatPromptExecutionSettings(
                temperature=definition.get('temperature', 0.5),
                function_choice_behavior=FunctionChoiceBehavior.Auto(
                    filters={"included_plugins": definition.get('included_plugins', [])}
                )
            ),
            description=definition['description'],
            instructions=definition['instructions']
        )
        
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
        
    #
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
   
    # def create_agent_group_chat(self, history):
    def create_agent_group_chat(self):

        self.logger.debug("Creating chat")
        
        query_agent = self.create_agent(service_id="gpt-4o", 
                                        definition_file_path="sk/agents/insurance/query.yaml")
        responder_agent = self.create_agent(service_id="gpt-4o", 
                                            definition_file_path="sk/agents/insurance/responder.yaml")
        
        agents=[query_agent, responder_agent]
        
        agent_group_chat = AgentGroupChat(
                agents=agents,
                selection_strategy=self.create_selection_strategy(agents, responder_agent),
                termination_strategy = self.create_termination_strategy(
                                         agents=[responder_agent,query_agent],
                                         final_agent=responder_agent,
                                         maximum_iterations=8))
        
        return agent_group_chat

    def load_history(self, user_id):
        user_data = self.db.read_user_info(user_id)
        conversation_list = []
        chat_histories = user_data.get('chat_histories')
        if chat_histories:
            for chat_id_key, conversation_data in chat_histories.items():
                messages = conversation_data.get('messages', [])
                conversation_object = {
                    "name": chat_id_key,
                    "messages": messages
                }
                conversation_list.append(conversation_object)
        self.logger.info(f"user history: {json.dumps(conversation_list)}")
        return {"status_code": 200, "data": conversation_list}
    
    async def handle_request(self, user_id, chat_id, user_message, load_history, usecase_type, user_data):
        
        # Additional Use Case - putting it here to avoid an extra endpoint/function
        if load_history is True:
            return self.load_history(user_id=user_id)
        
        # CORE use case
        conversation_messages = []
        
        if chat_id:
            # Continue existing chat
            conversation_data = user_data.get('chat_histories', {}).get(chat_id)
            self.logger.debug(f"Conversation data={conversation_data}")
            if conversation_data:
                conversation_messages = conversation_data.get('messages', [])
            else:
                return {"status_code": 404, "error": "chat_id not found"}
        else:
            # Start a new chat
            chat_id = self.db.generate_chat_id()
            conversation_messages = []
            user_data.setdefault('chat_histories', {})
            user_data['chat_histories'][chat_id] = {'messages': conversation_messages}
            self.db.update_user_info(user_id, user_data)

        conversation_messages.append({'role': 'user', 'name': 'user', 'content': user_message})
        
        agent_group_chat = self.create_agent_group_chat()
        # Load chat history - allowing through only assistant and user messages
        chat_history = [ChatMessageContent(
                            role=AuthorRole(d.get('role')),
                            name=d.get('name'),
                            content=d.get('content'))
                        for d in list(filter(lambda m: m['role'] and m['role'] in ("assistant", "user"), conversation_messages))]
        await agent_group_chat.add_chat_messages(chat_history)
        
        async for item in agent_group_chat.invoke():
            pass  # The response will be processed later

        response = list(reversed([item async for item in agent_group_chat.get_chat_messages()]))

        reply = {'role': response[-1].role.value,
                 'name': response[-1].name, 
                 'content': response[-1].content}
        
        conversation_messages.append(reply)
        
        user_data['chat_histories'][chat_id] = {'messages': conversation_messages}
        self.db.update_user_info(user_id, user_data)

        return {"status_code": 200, "chat_id": chat_id, "reply": [reply]}