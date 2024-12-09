# A common Python interface for both Agent and Team
from abc import ABC, abstractmethod

from .conversation import Conversation

class Askable(ABC):
    
    @abstractmethod
    def ask(self, conversation: Conversation, stream = False) -> str:
        pass
    
    def __init__(self, id: str, description: str):
        self._id = id
        self._description = description

    # an id property with a default implementation
    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    # a description property with a default implementation
    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value
