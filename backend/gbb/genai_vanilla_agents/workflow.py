import asyncio
import queue
import threading
from typing import Union
from .askable import Askable
from .conversation import Conversation

import logging
logger = logging.getLogger(__name__)

import base64

class WorkflowInput:
    def __init__(self, text: str, images: list[str] = []):
        self.text = text
        self.images = images
        
    # Function to encode the image
    def _encode_image(self, image_path: str):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
        
    def add_image_file(self, image_path: str):
        base64_image = self._encode_image(image_path)
        url = f"data:image/jpeg;base64,{base64_image}"
        self.images.append(url)
        
    def add_image_bytes(self, data: bytes):
        base64_image = base64.b64encode(data).decode('utf-8')
        url = f"data:image/jpeg;base64,{base64_image}"
        self.images.append(url)
        
    def to_message(self):
        # See https://platform.openai.com/docs/guides/vision
        content = [{"text": self.text, "type": "text"}]
        content.extend([{"image_url": {"url": image}, "type": "image_url"} for image in self.images])
        return {"role": "user", "name": "user", "content": content}
        

class Workflow():
    def __init__(self, askable: Askable, conversation: Conversation = None, system_prompt: str = ""):
        self.askable = askable
        self.conversation = conversation or Conversation(messages=[], variables={})
        self.system_prompt = system_prompt
        
        logger.debug("Workflow initialized")

    def run(self, workflow_input: Union[str, WorkflowInput]):
        self._handle_workflow_input(workflow_input)
        
        execution_result = self.askable.ask(self.conversation)
            
        return execution_result

    def _handle_workflow_input(self, workflow_input):
        logger.debug("Running workflow with input: %s", workflow_input)
        
        logger.debug("Conversation length: %s", len(self.conversation.messages))
        if len(self.conversation.messages) == 0:
            self.conversation.messages.append({"role": "system", "content": self.system_prompt})
            logger.debug("Added system prompt to messages: %s", self.system_prompt)
            
        if isinstance(workflow_input, WorkflowInput):
            self.conversation.messages.append(workflow_input.to_message())
            logger.debug("Added user input to messages: %s", workflow_input.text)
        elif isinstance(workflow_input, str):
            self.conversation.messages.append({"role": "user", "name": "user", "content": workflow_input})
        logger.debug("Added user input to messages: %s", workflow_input)
    
    def run_stream(self, workflow_input: Union[str, WorkflowInput]):
        self._handle_workflow_input(workflow_input)
        
        result_queue = queue.Queue()
        def ask_in_thread():
            try:
                res = self.askable.ask(self.conversation, stream=True)
            except Exception as e:
                logger.error("Error during askable.ask: %s", e)
                self.conversation.update(["error", e])
                res = "error"
            
            logger.debug("Workflow execution result in thread: %s", res)
            result_queue.put_nowait(res)
        
        thread = threading.Thread(target=ask_in_thread)
        thread.start()
        
        # In order to break the stream, we need to keep track of nesting levels, using a stack count
        stack_count = 0
        for mark, content in self.conversation.stream():
            # Always update the conversation with the stream content
            logger.debug(f"Stream content: {mark}, {content}")
            yield [mark, content]
            
            # Keep track of the stack count to know when to break
            if mark == "start":
                stack_count += 1
            elif mark == "end":
                stack_count -= 1
                
            logger.debug("Stack count: %s", stack_count)            
            if stack_count == 0:
                logger.debug("Received response and stack count is 0, breaking stream.")
                break
            if mark == "error":
                logger.debug("Received error, breaking stream.")
                break
        
        logger.debug("Joining thread")
        thread.join()
        result = result_queue.get()
        logger.debug("Workflow execution result: %s", result)
        
        yield ["result", result]
    
    def restart(self):        
        self.conversation = Conversation(messages=[], variables={})
        logger.debug("Conversation length: %s", len(self.conversation.messages))
        logger.debug("Restarted workflow, cleared conversation.")
