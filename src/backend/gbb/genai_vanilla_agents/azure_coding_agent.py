import shutil
from typing import Annotated

import requests
from .llm import LLM
from .conversation import AllMessagesStrategy, ConversationReadingStrategy
from .agent import Agent

# Configure logging
import logging
logger = logging.getLogger(__name__)

from azure.identity import DefaultAzureCredential
credential = DefaultAzureCredential()
token = credential.get_token("https://dynamicsessions.io/.default")
import os

class AzureCodingAgent(Agent):
    def __init__(self, id: str, description: str, llm: LLM, reading_strategy: ConversationReadingStrategy = AllMessagesStrategy()):
        system_message = """
        You are an expert Python developer.
        Your task is to write a Python code snippet to solve a given problem.
        ALWAYS adhere to the guidelines provided.
        
        ## GUIDELINES
        - You can use any Python libraries you need, but in case you must invoke the proper function call to install them first.
        - The code MUST be written in Python.
        - The code MUST be secure and efficient. NEVER use code that can be harmful.
        - The code MUST AVOID any side effects, especially reading or writing to the file system.
        - The code MUST NOT read or write files or directories outside of the code execution environment.
        - If you cannot comply with these guidelines, please return an error message.
        
        ## INSTRUCTIONS
        - Write and run the Python code to solve the problem and return the output of the code execution
        
        ## ADDITIONAL CONTEXT
        __context__
        
        """
        super().__init__(id=id, description=description, system_message=system_message, llm=llm, reading_strategy=reading_strategy)
                
        logger.debug(f"CodingAgent initialized with ID: {self.id}, Description: {self.description}")
        self.register_tool(description="Runs the provided Python code block")(run_code)

def run_code( 
    conversation_id: Annotated[str, "Conversation ID"],
    code: Annotated[str, "Python code to run"]) -> Annotated[str, "Python code output"]:
    logger.info("Starting execution of provided code")
    logger.debug(f"Code: {code}")
    
    management_endpoint = os.getenv("AZURE_DYNAMIC_SESSIONS_ENDPOINT")
    if not management_endpoint:
        logger.error("AZURE_DYNAMIC_SESSIONS_ENDPOINT environment variable is not set")
        return "Error: AZURE_DYNAMIC_SESSIONS_ENDPOINT environment variable is not set"
    
    try:
        response = requests.post(
            f"{management_endpoint}/code/execute?api-version=2024-02-02-preview&identifier={conversation_id}", 
            headers={"Authorization": f"Bearer {token.token}"}, 
            json={
            "properties": {
                "codeInputType": "inline",
                "executionType": "synchronous",
                "code": code
            }
            })
        
        response.raise_for_status()
        
        response_json = response.json()
        logger.info("Code execution completed successfully")
        return response_json["properties"]
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}, Response: {e.response.text if e.response else 'No response'}")
        return f"Error: Request failed with exception {e}, Response: {e.response.text if e.response else 'No response'}"
    
    except ValueError as e:
        logger.error(f"JSON decoding failed: {e}")
        return f"Error: JSON decoding failed with exception {e}"
    
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return f"Error: An unexpected error occurred: {e}"