import logging
import json
import yaml
from abc import ABC, abstractmethod
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole

class SemanticOrchastrator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Semantic Orchestrator Handler init")
        # self.history_db = history_db
        
 
    # --------------------------------------------
    # ABSTRACT method - MUST be implemented by the subclass
    # --------------------------------------------
    @abstractmethod
    def create_agent_group_chat(self): 
        pass
    
    def create_agent(self, kernel, service_id, definition_file_path):
        
        with open(definition_file_path, 'r') as file:
            definition = yaml.safe_load(file)

        return ChatCompletionAgent(
            service_id=service_id,
            kernel=kernel,
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
    
    async def process_conversation(self, conversation_messages):
        agent_group_chat = self.create_agent_group_chat()
        # Load chat history - allow only assistant and user messages
        chat_history = [
            ChatMessageContent(
                role=AuthorRole(d.get('role')),
                name=d.get('name'),
                content=d.get('content')
            ) for d in filter(lambda m: m['role'] in ("assistant", "user"), conversation_messages)
        ]

        await agent_group_chat.add_chat_messages(chat_history)

        async for _ in agent_group_chat.invoke():
            pass

        response = list(reversed([item async for item in agent_group_chat.get_chat_messages()]))

        reply = {
            'role': response[-1].role.value,
            'name': response[-1].name,
            'content': response[-1].content
        }

        return reply