import logging
import json
import yaml
from abc import ABC, abstractmethod
from dotenv import load_dotenv
import os
from openai import AzureOpenAI
import time
from datetime import datetime, timedelta

from o1_assistants_api.banking.banking_tools import get_TOOLS
from o1_assistants_api.banking.banking_tools import get_FUNCTION_MAPPING

class O1BankingOrchestrator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.debug("o1 Banking Orchestrator Handler init")
        self.client = self.get_openai_client("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT")
        self.o1_client = self.get_openai_client("O1_OPENAI_API_KEY", "O1_OPENAI_ENDPOINT", "O1_OPENAI_DEPLOYMENT_NAME")
        self.o1_mini_client = self.get_openai_client("O1_OPENAI_API_KEY", "O1_OPENAI_ENDPOINT", "O1_MINI_OPENAI_DEPLOYMENT_NAME")


    # Initialize OpenAI clients
    def get_openai_client(self, key, endpoint, deployment):
        return AzureOpenAI(
            api_key=os.getenv(key),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv(endpoint),
            azure_deployment=os.getenv(deployment)
        )
    

    def call_o1(self, scenario):
    
        # Prompt templates
        O1_PROMPT = """
You are a private wealth management assistant focusing on investment solutions, portfolio analysis, and CRM-based client data retrieval. You are a planner. The first input you will receive will be a complex task/scenario that needs to be carefully reasoned through to solve. 
Your task is to review the challenge, and create a plan to handle it.

You will have access to an LLM agent that is responsible for executing the plan that you create and will return results.

The LLM agent has access to the following functions:
{tools}

When creating a plan for the LLM to execute, break your instructions into a logical, step-by-step order, using the specified format:
    - **Main actions are numbered** (e.g., 1, 2, 3).
    - **Sub-actions are lettered** under their relevant main actions (e.g., 1a, 1b).
        - **Sub-actions should start on new lines**
    - **Specify conditions using clear 'if...then...else' statements** (e.g., 'If the product was purchased within 30 days, then...').
    - **For actions that require using one of the above functions defined**, write a step to call a function using backticks for the function name (e.g., `call the load_from_crm_by_client_fullname function`).
        - Ensure that the proper input arguments are given to the model for instruction. There should not be any ambiguity in the inputs.
    - **The last step** in the instructions should always be calling the `instructions_complete` function. This is necessary so we know the LLM has completed all of the instructions you have given it.
    - **Make the plan simple** Do not add steps on the plan when they are not needed.
    - **Generate summary** Before the `instructions_complete` ask the LLM to make a summary of the actions.
Use markdown format when generating the plan with each step and sub-step.

Please find the scenario below.
{scenario}
"""       
        
        tools_str = json.dumps(get_TOOLS(), indent=2)
        prompt= O1_PROMPT.replace("{tools}",tools_str).replace("{scenario}",str(scenario))
     
        response = self.o1_mini_client.chat.completions.create(
            model=os.getenv("O1_MINI_OPENAI_DEPLOYMENT_NAME"),
            messages=[{'role': 'user', 'content': prompt}]
        )
        
        plan = response.choices[0].message.content
        self.logger.debug(f"📟 Response from o1 plan: {plan}")
        return plan
    


    def call_gpt4o(self, plan):
        GPT4O_SYSTEM_PROMPT = """
You are a helpful assistant responsible for executing a plan on handling incoming orders.
Your task is to:
1. Follow the plan exactly as written
2. Use the available tools to execute each step
3. Provide clear explanations of what you're doing
4. Always respond with some content explaining your actions
5. Call the instructions_complete function only when all steps are done
6. Never write or execute code
7. In your response, do not add things like "I have succesfully do this and that..." or "This should provide you with the content you asked for..."

PLAN TO EXECUTE:
{plan}

Remember to explain each action you take and provide status updates.
"""
        
        gpt4o_policy_prompt = GPT4O_SYSTEM_PROMPT.replace("{plan}", plan)
        messages = [{'role': 'system', 'content': gpt4o_policy_prompt}]

        while True:
            response = self.client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                messages=messages,
                tools=get_TOOLS(),
                parallel_tool_calls=False
            )
            #self.logger.info(f" Response from 4o agent:\n {response}")
            
            assistant_message = response.choices[0].message.model_dump()
            messages.append(assistant_message)
   
            if not response.choices[0].message.tool_calls:
                continue

            for tool in response.choices[0].message.tool_calls:
                if tool.function.name == 'instructions_complete':
                    return messages

                function_name = tool.function.name 
              
                self.logger.debug(f"📟 Executing function: {function_name}")
                try:
                    arguments = json.loads(tool.function.arguments)
                    
                    function_response = get_FUNCTION_MAPPING()[function_name](**arguments)
                  
                    self.logger.debug( f"{function_name}: {json.dumps(function_response)}")
                    
                    self.logger.debug("Function executed successfully!")
                    self.logger.debug(function_response)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool.id,
                        "content": json.dumps(function_response)
                    })
                    
                except Exception as e:
                    self.logger.error('error', f"Error in {function_name}: {str(e)}")
            

    def summarize(self, input):
        gpt4o_summary_prompt = """Collect all the information of the latest Action performed paragraph (which is not the 'instructions_complete')
         but instead, the last action that represent a final answer to the user, marked by **Generate summary** and following content.
         Do not include text that mention things like 'The latest action that represents a final answer to the user is etc', instead provide the content you found as is.
         INPUT:{input} """.replace("{input}", input)
        messages = [{'role': 'system', 'content': gpt4o_summary_prompt}]
 
        response = self.client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=messages
        )
        return response.choices[0].message.content


    async def process_conversation(self, conversation_messages):
        
        #o1 planner agent part
        o1_response = self.call_o1(conversation_messages)
        o1_reply = {
            'role': 'assistant',
            'name': 'o1-mini Planner',
            'content': o1_response
        }
        self.logger.info( f"o1 plan: {o1_reply}" )

        #4o executor part
        ex_response = self.call_gpt4o(o1_response)
        # Filter assistant messages that have actual content
        assistants_4o_contents = [
           msg['content'] for msg in ex_response 
           if msg.get('role') == 'assistant' and msg.get('content') is not None
        ]
        ex_reply = {
            'role': 'assistant',
            'name': '4o-mini Agent',
            'content': assistants_4o_contents[-1]
        }
        self.logger.info( f"4o response: {ex_reply}" )

        summary_4o_response = self.summarize(assistants_4o_contents[-1])
        summary_reply = {
            'role': 'assistant',
            'name': '4o-mini Agent',
            'content': summary_4o_response
        }

        completion_tokens = 0
        prompt_tokens = 0
                
        # TODO: Calculate total tokens
        total_tokens = prompt_tokens + completion_tokens

        # Prepare the metrics dictionary
        metrics = {
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens
            }

        #returning only the 4o message (final response) at the moment the plan and the reasons are not kept
        return summary_reply, metrics


