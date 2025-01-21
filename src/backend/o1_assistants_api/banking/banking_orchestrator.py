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
You are a private wealth management assistant focusing on investment solutions, portfolio analysis, and CRM-based client data retrieval. The first input you receive will be a query related to private wealth management—this may include requests about CIO research, client information, fund details, or recent news on specific investments.

Your task is to review the request and create a detailed plan to provide the required information and/or analysis.

You will have access to an LLM agent that is responsible for executing the plan you create and returning the results.

The LLM agent has access to the following functions:
1. **search_cio(query)**
   - Searches details about CIO insights, recommendations, and in-house views.
2. **load_from_crm_by_client_fullname(full_name)**
   - Loads insured client data from the CRM by the client full name.
3. **load_from_crm_by_client_id(client_id)**
   - Loads insured client data from the CRM by the client unique ID.
4. **search_funds_details(query)**
   - Searches for details about mutual funds or ETFs.
5. **search_news(position)**
   - Searches the web for the latest investment news for a specific stock ticker (position).

When creating a plan for the LLM to execute, please follow these formatting guidelines:

1. **Number each main action** (e.g., 1, 2, 3).
2. **For sub-actions, use letters** under their relevant main actions (e.g., 1a, 1b).  
   - Each sub-action should start on a new line.
3. **Use clear conditional logic** when needed (e.g., “If no client data is found, then return an error message...”).
4. **When calling one of the above functions**, enclose the function name in backticks (e.g., `call the search_news function`) and provide any relevant input parameters explicitly (e.g., “pass the ticker = 'AAPL' as an argument”).
5. **Only use the functions that are required to fullfill the original input query.**
6. **Always end your plan** by calling the `instructions_complete` function to signal that all instructions have been fulfilled.
7. **The last step of the plan should always be generating a final answer for the user initial query by calling the `final_answer` function**

Be thorough in your steps and sub-steps, explaining what is being done at each stage and why. Use markdown format when generating the plan to clearly separate numbered actions and sub-actions.

---

Please find the scenario below.
"""       
    
        prompt = f"{O1_PROMPT}\n\nScenario:\n{scenario}\n\nPlease provide the next steps in your plan."
     
        response = self.o1_mini_client.chat.completions.create(
            model=os.getenv("O1_MINI_OPENAI_DEPLOYMENT_NAME"),
            messages=[{'role': 'user', 'content': prompt}]
        )
        
        plan = response.choices[0].message.content
        self.logger.debug(f"📟 Response from o1 plan: {plan}")
        return plan
    


    def call_gpt4o(self, plan):
        GPT4O_SYSTEM_PROMPT = """
You are a helpful assistant responsible for executing the policy on handling financial service requests. Your task is to follow the policy exactly as it is written and perform the necessary actions.

You must explain your decision-making process across various steps.

# Steps

1. **Read and Understand Policy**: Carefully read and fully understand the given policy on handling the request.
2. **Identify the exact step in the policy**: Determine which step in the policy you are at, and execute the instructions according to the policy.
3. **Decision Making**: Briefly explain your actions and why you are performing them.
4. **Action Execution**: Perform the actions required by calling any relevant functions and input parameters.

POLICY:
{policy}
"""
        
        gpt4o_policy_prompt = GPT4O_SYSTEM_PROMPT.replace("{policy}", plan)
        messages = [{'role': 'system', 'content': gpt4o_policy_prompt}]

        while True:
            response = self.client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                messages=messages,
                tools=get_TOOLS(),
                parallel_tool_calls=False
            )
               
            assistant_message = response.choices[0].message.model_dump()
            messages.append(assistant_message)
            self.logger.debug(f"📟 Response from 4o agent: {assistant_message}")

            if not response.choices[0].message.tool_calls:
                continue

            for tool in response.choices[0].message.tool_calls:
                if tool.function.name == 'instructions_complete':
                    return messages

                if tool.function.name == 'final_answer':

                    gpt4o_answer_prompt = """Provide a response identified by the last following paragraph **Action Execution**: you find in the input to the user.
                    INPUT: {input} """.replace("{input}", response.choices[0].message.content)
                    answer_messages = [{'role': 'system', 'content': gpt4o_answer_prompt}]
                    answer_response = self.client.chat.completions.create(
                          model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
                          messages=answer_messages
                
                    )
                    messages.append({
                        "role": "assistant",
                        "content": answer_response.choices[0].message.content
                    })
                    continue

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
            

    async def process_conversation(self, conversation_messages):
        
        #o1 planner agent part
        o1_response = self.call_o1(conversation_messages)
        o1_reply = {
            'role': 'assistant',
            'name': 'o1 Planner',
            'content': o1_response
        }
        self.logger.info( f"o1 plan: {o1_reply}" )
    

        #4o executor part
        ex_response = self.call_gpt4o(o1_response)
        ex_reply = {
            'role': 'assistant',
            'name': '4o Agent',
            'content': ex_response
        }
        self.logger.info('New reposnse \n')
        self.logger.info( f"4o response: {ex_reply}" )

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
        return ex_reply, metrics


