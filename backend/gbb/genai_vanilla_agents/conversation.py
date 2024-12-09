from abc import ABC, abstractmethod
from queue import SimpleQueue
from typing import Any, Protocol

from pydantic import BaseModel

from .llm import LLM
import logging
logger = logging.getLogger(__name__)

# a ConversationMetrics class with totalTokens, promptTokens and completionTokens
class ConversationMetrics(BaseModel):
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int

class Conversation():
    def __init__(self, messages: list[dict] = [], variables: dict[str, str] = {}, metrics = ConversationMetrics(total_tokens=0, prompt_tokens=0, completion_tokens=0), log = []):
        self.messages = messages
        self.variables = variables
        self.log = log
        self.metrics = metrics
        self.stream_queue = SimpleQueue()
        
    def stream(self):
        """
        Stream conversation updates, like LLM delta updates, to the consumer
        
        NOTE this is an INFINITE generator function, and must be kept so. 
        Consumers should break the loop themselves, typically using a stack count logic
    """
        while True:
            mark, content = self.stream_queue.get()
            yield [mark, content]
        
    def update(self, delta):
        self.stream_queue.put_nowait(delta)
        
    def to_dict(self):
        return {
            "messages": self.messages,
            "variables": self.variables,
            "metrics": self.metrics.model_dump()
        }
        
    def fork(self):
        return Conversation(messages=self.messages.copy(), variables=self.variables.copy())
        
    @classmethod
    def from_dict(cls, data):
        return cls(
            messages = data.get('messages', []),
            variables = data.get('variables', {}),
            log = data.get('log', []),
            metrics = ConversationMetrics(**data.get('metrics', {}))
        )
        
class ConversationReadingStrategy(ABC):
    @abstractmethod
    def get_messages(self, conversation: Conversation) -> list[dict]:
        pass
    
    def exclude_system_messages(self, messages: list[dict]) -> list[dict]:
        return [message for message in messages if message["role"] != "system"]
    
class LastNMessagesStrategy(ConversationReadingStrategy):
    def __init__(self, n: int):
        self.n = n
        
    def get_messages(self, conversation: Conversation) -> list[dict]:
        return self.exclude_system_messages(conversation.messages)[-self.n:]
    
class AllMessagesStrategy(ConversationReadingStrategy):
    def get_messages(self, conversation: Conversation) -> list[dict]:
        return self.exclude_system_messages(conversation.messages)
    
class TopKLastNMessagesStrategy(ConversationReadingStrategy):
    def __init__(self, k: int, n: int):
        self.k = k
        self.n = n
        
    def get_messages(self, conversation: Conversation) -> list[dict]:
        list = self.exclude_system_messages(conversation.messages)
        return list[:self.k] + list[-self.n:]
    
class SummarizeMessagesStrategy(ConversationReadingStrategy):
    def __init__(self, llm: LLM, system_prompt: str):
        super().__init__()
        self.llm = llm
        self.system_prompt = system_prompt
        
    def get_messages(self, conversation: Conversation) -> list[dict]:
        # Extract the conversation text from the messages        
        local_messages = []
        local_messages += self.exclude_system_messages(conversation.messages)
        local_messages.append({"role": "user", "content": self.system_prompt})
        
        # Summarize the conversation text
        response, usage = self.llm.ask(messages=local_messages)
        response_message = response.model_dump()
        summarized_text = response_message["content"]
        
        return [{"role": "assistant", "name": "summarizer", "content": summarized_text}]

class PipelineConversationReadingStrategy(ConversationReadingStrategy):
    def __init__(self, strategies: list[ConversationReadingStrategy]):
        self.strategies = strategies
        
    def get_messages(self, conversation: Conversation) -> list[dict]:
        messages = conversation.messages
        for strategy in self.strategies:
            messages = strategy.get_messages(Conversation(messages=messages))
        return messages
    
class ConversationUpdateStrategy(ABC):
    @abstractmethod
    def update(self, conversation: Conversation, delta: any):
        pass
    
class AppendMessagesUpdateStrategy(ConversationUpdateStrategy):
    def update(self, conversation: Conversation, delta: any):
        if isinstance(delta, list):
            conversation.messages += delta
        else:
            conversation.messages += [delta]
        
class ReplaceLastMessageUpdateStrategy(ConversationUpdateStrategy):
    def update(self, conversation: Conversation, delta: any):
        conversation.messages[-1] = delta

class NoopUpdateStrategy(ConversationUpdateStrategy):
    """
    No operation update strategy, does not update the conversation.
    
    Useful for agents that do not need to update messages, but only invoke functions or set variables.
    """
    def update(self, conversation: Conversation, delta: any):
        pass