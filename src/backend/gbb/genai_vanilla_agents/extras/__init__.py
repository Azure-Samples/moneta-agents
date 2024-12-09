from ..llm import LLM
from ..conversation import ConversationReadingStrategy, Conversation
from llmlingua import PromptCompressor

import logging
logger = logging.getLogger(__name__)

class PromptCompressorLLM(LLM):
    def __init__(self, model_name: str):
        super().__init__(model_name)
        self.prompt_compressor = PromptCompressor()

        logger.debug("[PromptCompressorLLM] initialized with model: %s", self.model_name)

    def ask(self, messages: list[dict]):
        # Extract the conversation text from the messages
        conversation_text = " ".join([message["content"] for message in messages])

        # Compress the conversation text
        compressed_text = self.prompt_compressor.compress(conversation_text)

        return compressed_text
    
class CompressSystemPromptStrategy(ConversationReadingStrategy):
    def __init__(self):
        super().__init()
        self.compressor = PromptCompressor()
        
    def get_messages(self, conversation: Conversation) -> list[dict]:
        # Get system message
        system_message = conversation.messages[0]
        if system_message["role"] != "system":
            raise ValueError("First message in conversation should be system message")
        
        # Compress the system message
        compressed_text = self.compressor.compress(system_message["content"])
        
        # Return the original conversation with the compressed system message
        return [{"role": "system", "content": compressed_text}] + conversation.messages[1:]