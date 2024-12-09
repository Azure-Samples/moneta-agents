from typing import Callable

from .askable import Askable
from .conversation import Conversation

class User(Askable):
    """
    A human user that interacts with the system. Can provide input to the chat.
    
    Args:
        id (str): The unique identifier of the user.
        mode (str): The mode of the user. Can be "interactive" or "unattended".
        description (str): The description of the user. Can be used by the orchestrator to decide which agent to ask.
        interaction_function (Callable[[str], str]): The function to use to get the user input. By default, it uses the input function.
    """
    def __init__(self, id = "user", mode = "interactive", description = "A human user that interacts with the system. Can provide input to the chat", interaction_function: Callable[[str], str] = None):
        super().__init__(id, description)
        self.id = id
        self.mode = mode
        self.description = description
        self.interaction_function = interaction_function or input
        
    def ask(self, conversation: Conversation, stream = False):
        """
        Ask the user to provide input to the chat.
        
        This method will get the user input from the command line prompt by default when the mode is "interactive".
        Else, it will return "stop" when the mode is "unattended". User input must then be provided by workflow.run().
        """
        if (self.mode == "interactive"):        
            # Get user input from command line prompt
            user_input = self.interaction_function(f"{self.id}: ")
            conversation.messages.append({"role": "user", "content": user_input, "name": self.id})
            return None
        elif (self.mode == "unattended"):
            return "stop"