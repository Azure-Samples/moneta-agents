import os
import logging
import json
import yaml
import datetime
from abc import ABC, abstractmethod
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from opentelemetry.trace import get_tracer

from semantic_kernel.connectors.ai.azure_ai_inference import AzureAIInferenceChatCompletion
import azure.ai.inference.aio as aio_inference
import azure.identity.aio as aio_identity

from sk.aifoundry.agent_initialiazer import AgentInitializer

from sk.orchestrators.temp_agent import CustomAgentBase
import util

util.load_dotenv_from_azd()
util.set_up_tracing()
util.set_up_metrics()
util.set_up_logging()

class SemanticOrchastrator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Semantic Orchestrator Handler init")
        
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        
        self.gpt4o_service = AzureAIInferenceChatCompletion(
            ai_model_id="gpt-4o",
            client=aio_inference.ChatCompletionsClient(
                endpoint=f"{str(endpoint).strip('/')}/openai/deployments/{deployment_name}",
                credential=aio_identity.DefaultAzureCredential(),
                credential_scopes=["https://cognitiveservices.azure.com/.default"],
            ))
 
 
    # --------------------------------------------
    # ABSTRACT method - MUST be implemented by the subclass
    # --------------------------------------------
    @abstractmethod
    def create_agent_group_chat(self): 
        pass
    
    async def process_conversation(self, user_id, conversation_messages):
        agent_group_chat = self.create_agent_group_chat()
        chat_history = [
            ChatMessageContent(
                role=AuthorRole(d.get('role')),
                name=d.get('name'),
                content=d.get('content')
            ) for d in filter(lambda m: m['role'] in ("system", "developer", "assistant", "user"), conversation_messages)
        ]

        await agent_group_chat.add_chat_messages(chat_history)
        
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("AgenticChat"):
            async for _ in agent_group_chat.invoke():
                pass

        response = list(reversed([item async for item in agent_group_chat.get_chat_messages()]))

        reply = {
            'role': response[-1].role.value,
            'name': response[-1].name,
            'content': response[-1].content
        }

        return reply
    
    
    # def create_agent(self, kernel, service_id, definition_file_path):
        
    #     with open(definition_file_path, 'r') as file:
    #         definition = yaml.safe_load(file)

    #     return ChatCompletionAgent(
    #         service_id=service_id,
    #         kernel=kernel,
    #         name=definition['name'],
    #         execution_settings=AzureChatPromptExecutionSettings(
    #             temperature=definition.get('temperature', 0.5),
    #             function_choice_behavior=FunctionChoiceBehavior.Auto(
    #                 filters={"included_plugins": definition.get('included_plugins', [])}
    #             )
    #         ),
    #         description=definition['description'],
    #         instructions=definition['instructions']
    #     )

     # --------------------------------------------
    # Create Agent Group Chat from Agent Service Foundry SDK defined Agetns
    # --------------------------------------------
    def create_agent_from_foundry(
        self, 
        kernel: Kernel, 
        service_id: str, 
        agent_initializer: AgentInitializer, 
        agent_type: str
    ) -> ChatCompletionAgent:
        """
        Fetches (or creates) the agent in Foundry via agent_initializer, then
        maps it to an SK ChatCompletionAgent instance.
        """
        # 1) Create / fetch the agent from Foundry
        foundry_agent = agent_initializer.create_agent(agent_type)  
        #   This reads the same local .yaml you have in Foundry, but returns 
        #   the Foundry agent object (including instructions, description, tools, etc.)

        # 2) Extract metadata from the Foundry agent
        #    Depending on the shape of the object returned by foundry_agent, 
        #    you might have:
        agent_name = foundry_agent.name  # e.g. "crm-agent"
        agent_description = foundry_agent.description
        agent_instructions = foundry_agent.instructions
        agent_temperature = foundry_agent.temperature or 0.5

        # 3) Convert Foundry tools -> SK function filters or kernel plugins 
        #    If you want to filter on included plugins:
        included_plugins = []
        if foundry_agent.tools:
            # If the Foundry agent has tool definitions, you might parse them:
            for t in foundry_agent.tools:
                # If 't.name' is something you also have in your SK plugin registry:
                included_plugins.append(t.name)

        # 4) Create the SK ChatCompletionAgent
        sk_agent = ChatCompletionAgent(
            service_id=service_id,
            kernel=kernel,
            name=agent_name,
            execution_settings=AzureChatPromptExecutionSettings(
                temperature=agent_temperature,
                function_choice_behavior=FunctionChoiceBehavior.Auto(
                    filters={
                        "included_plugins": included_plugins
                    }
                ),
            ),
            description=agent_description,
            instructions=agent_instructions
        )

        return sk_agent

 