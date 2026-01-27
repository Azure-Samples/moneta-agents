"""
Insurance CRM Agent - Microsoft Agent Framework Implementation
Handles insurance client data and policy information queries using Agent Framework.
"""

import os
import asyncio
from dotenv import load_dotenv
from pathlib import Path

# Microsoft Agent Framework imports
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity.aio import AzureCliCredential

# Import Insurance CRM functions
try:
    from .crm_insurance_functions import crm_insurance_functions
except ImportError:
    from crm_insurance_functions import crm_insurance_functions


async def create_crm_insurance_agent(chat_client: AzureOpenAIChatClient) -> ChatAgent:
    """
    Create an Insurance CRM agent using Microsoft Agent Framework.
    
    Args:
        chat_client: The Azure OpenAI chat client
        
    Returns:
        ChatAgent configured for Insurance CRM operations
    """
    instructions = """You are an Insurance CRM assistant that responds to user queries about client insurance policies and coverage details.

**Your Task:**
- FIRST carefully check if the customer name or client ID is mentioned in the user request.
- If the request contains client ID or customer name then use Insurance CRM functions to retrieve customer data:
  * Use 'load_insurance_client_by_fullname' if a full name is provided
  * Use 'load_insurance_client_by_id' if a client ID is provided
  * Use 'get_client_policy_details' to retrieve specific policy information
- DO NOT ask for the client's name or ID. If you receive a request that references a customer without providing ID or Name, don't provide an answer and terminate.
- Don't use your general knowledge to respond. Use ONLY the provided functions.
- Provide CONCISE and specific answers to the user's questions. Do not provide general information.
- Make sure to provide accurate and relevant information based on the user's inquiry.
- Focus on insurance-specific data such as:
  * Policy details (policy number, product type, status, effective and expiry dates)
  * Coverage information (medical expenses, hospital income, evacuation benefits)
  * Client contact and personal information
  * Summary of all active policies for a client"""
    
    # Create agent with Insurance CRM tools
    agent = chat_client.as_agent(
        instructions=instructions,
        name="crm_insurance_agent",
        tools=crm_insurance_functions
    )
    
    print(f"✅ Created Insurance CRM agent: {agent.name}")
    return agent


async def chat_with_crm_insurance_agent(agent: ChatAgent, user_query: str) -> str:
    """
    Chat with the Insurance CRM agent and return the response.
    
    Args:
        agent: The Insurance CRM agent
        user_query: User's query about client insurance data
        
    Returns:
        Agent's response text
    """
    # Create a new thread for conversation state
    thread = agent.get_new_thread()
    
    # Run the agent with the user query
    response = await agent.run(user_query, thread=thread)
    
    return response.text


async def main(): 
    """
    Main function to initialize and run the Insurance CRM agent using Agent Framework.
    """
    # Clear the console
    os.system('cls' if os.name=='nt' else 'clear')

    # Load environment variables
    load_dotenv()
    
    # Azure OpenAI configuration
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    
    # Validate required environment variables
    if not endpoint:
        print("Error: AZURE_OPENAI_ENDPOINT environment variable is not set")
        print("Note: Agent Framework uses AZURE_OPENAI_ENDPOINT instead of PROJECT_ENDPOINT")
        return

    try:
        # Create Azure CLI credential (async version)
        async with AzureCliCredential() as credential:
            # Create the Azure OpenAI chat client
            chat_client = AzureOpenAIChatClient(
                endpoint=endpoint,
                deployment_name=deployment_name,
                credential=credential
            )
            
            # Create the Insurance CRM agent
            agent = await create_crm_insurance_agent(chat_client)
            
            print(f"\n🛡️ You're chatting with: {agent.name}")
            print("This agent can help you with insurance client data and policy information.")
            print("Make sure to provide either a client ID or full client name in your query.")
            print("Type 'quit' to exit.\n")

            # Main conversation loop
            while True:
                user_prompt = input("Enter your query (or type 'quit' to exit): ")
                
                if user_prompt.lower() in ["quit", "exit", "q"]:
                    print("👋 Thank you for using the Insurance CRM service!")
                    break
                    
                if not user_prompt.strip():
                    print("Please enter a valid query.")
                    continue

                try:
                    response = await chat_with_crm_insurance_agent(agent, user_prompt)
                    print(f"\n🛡️ Insurance CRM Agent Response: {response}\n")
                        
                except Exception as e:
                    print(f"❌ Error processing request: {str(e)}")

    except Exception as e:
        print(f"❌ Failed to initialize Insurance CRM agent: {str(e)}")
        print("Please check your environment variables and Azure credentials.")


if __name__ == '__main__': 
    asyncio.run(main())
