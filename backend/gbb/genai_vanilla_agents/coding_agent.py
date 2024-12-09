import shutil
from typing import Annotated
from .llm import LLM
from .conversation import AllMessagesStrategy, ConversationReadingStrategy
from .agent import Agent

# Configure logging
import logging
logger = logging.getLogger(__name__)

import subprocess
import os
import tempfile
import venv

class LocalCodingAgent(Agent):
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
        - Initialize a Python virtual environment, and set a conversation variable "venv_dir" to the virtual environment directory. Skip this step if the virtual environment is already initialized.
        - Install the required Python packages, if any
        - Write and run the Python code to solve the problem and return the output of the code execution
        
        ## ADDITIONAL CONTEXT
        __context__
        
        """
        super().__init__(id=id, description=description, system_message=system_message, llm=llm, reading_strategy=reading_strategy)
        
        logger.debug(f"CodingAgent initialized with ID: {self.id}, Description: {self.description}")
        self.register_tool(description="Initializes a Python virtual environment")(init_venv)
        # self.register_tool(description="Cleans up the Python virtual environment")(cleanup_venv)
        self.register_tool(description="Installs the provided Python requirements")(install_dependencies)
        self.register_tool(description="Runs the provided Python code block")(run_code)
        
def init_venv() -> Annotated[str, "Python virtual environment directory"]:
    logger.info("Initializing virtual environment")
    
    # Create a directory for the virtual environment
    venv_dir = os.path.join(os.getcwd(), 'LocalCodingAgent', 'venv')
    logger.debug(f"Creating virtual environment in {venv_dir}")
    
    if not os.path.exists(venv_dir):
        os.makedirs(venv_dir)
        venv.create(venv_dir, with_pip=True)
    
    logger.info("Virtual environment initialized successfully")
    return venv_dir

# def cleanup_venv(venv_dir: Annotated[str, "Python virtual environment directory"]) -> Annotated[str, "Virtual environment cleanup output"]:
#     logger.info("Cleaning up virtual environment")
#     logger.debug(f"Virtual environment directory: {venv_dir}")
    
#     if os.path.exists(venv_dir):
#         logger.debug(f"Removing virtual environment directory: {venv_dir}")
#         shutil.rmtree(venv_dir)
#         logger.info("Virtual environment cleaned up successfully")
#         return "success"
#     else:
#         logger.warning(f"Virtual environment directory not found: {venv_dir}")
#         return "error"
        
def install_dependencies(venv_dir: Annotated[str, "Python virtual environment directory"], requirements: Annotated[str, "Python requirements in requirements.txt format"]) -> Annotated[str, "Python requirements installation output"]:
    logger.info("Starting installation of dependencies")
    logger.debug(f"Requirements: {requirements}")
    
    # Install the required python packages in the virtual environment
    try:
        logger.debug(f"Installing requirements from {requirements}")
        subprocess.check_call([os.path.join(venv_dir, 'scripts', 'pip'), 'install', requirements])
        logger.info("Dependencies installed successfully")
        return "success"
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running code: {e.output.decode('utf-8')}")
        return f"Error installing dependencies:\n{e.output.decode('utf-8')}"
        
        

def run_code(venv_dir: Annotated[str, "Python virtual environment directory"], code: Annotated[str, "Python code to run"]) -> Annotated[str, "Python code output"]:
    logger.info("Starting execution of provided code")
    logger.debug(f"Code: {code}")
            
    # Write the code to a temporary file
    code_file = os.path.join(venv_dir, 'code.py')
    logger.debug(f"Writing code to temporary file {code_file}")
    
    with open(code_file, 'w') as f:
        f.write(code)
    
    # Run the provided python code in the virtual environment
    try:
        result = subprocess.check_output([os.path.join(venv_dir, 'scripts', 'python'), code_file], stderr=subprocess.STDOUT)
        logger.info("Code executed successfully")
        return result.decode('utf-8')
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running code: {e.output.decode('utf-8')}")
        return f"Error executing code:\n{e.output.decode('utf-8')}"