"""
CRM Agent - Microsoft Agent Framework Implementation
Handles client data and portfolio information queries using Agent Framework.
"""

import os
import asyncio
from dotenv import load_dotenv
from pathlib import Path

# Microsoft Agent Framework imports
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity.aio import AzureCliCredential

# Import CRM functions
from crm_functions import crm_functions


async def create_crm_agent(chat_client: AzureOpenAIChatClient) -> ChatAgent:
    """
    Create a CRM agent using Microsoft Agent Framework.
    
    Args:
        chat_client: The Azure OpenAI chat client
        
    Returns:
        ChatAgent configured for CRM operations
    """
    instructions = """You are a CRM assistant that responds to user queries about client data and client portfolios.

**Your Task:**
- FIRST carefully check if the customer name or client ID is mentioned in the user request.
- If the request contains client ID or customer name then use CRM functions to retrieve customer data:
  * Use 'load_from_crm_by_client_fullname' if a full name is provided
  * Use 'load_from_crm_by_client_id' if a client ID is provided
- DO NOT ask for the client's name or ID. If you receive a request that references a customer without providing ID or Name, don't provide an answer and terminate.
- Don't use your general knowledge to respond. Use ONLY the provided functions.
- Provide CONCISE and specific answers to the user's questions. Do not provide general information.
- Make sure to provide accurate and relevant information based on the user's inquiry.
- Focus on the specific data requested (e.g., portfolio performance, contact details, investment profile, etc.)"""
    
    # Create agent with CRM tools
    agent = chat_client.create_agent(
        instructions=instructions,
        name="crm_agent",
        tools=crm_functions
    )
    
    print(f"✅ Created CRM agent: {agent.name}")
    return agent


async def chat_with_crm_agent(agent: ChatAgent, user_query: str) -> str:
    """
    Chat with the CRM agent and return the response.
    
    Args:
        agent: The CRM agent
        user_query: User's query about client data
        
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
    Main function to initialize and run the CRM agent using Agent Framework.
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
            
            # Create the CRM agent
            agent = await create_crm_agent(chat_client)
            
            print(f"\n🏦 You're chatting with: {agent.name}")
            print("This agent can help you with client data and portfolio information.")
            print("Make sure to provide either a client ID or full client name in your query.")
            print("Type 'quit' to exit.\n")

            # Main conversation loop
            while True:
                user_prompt = input("Enter your query (or type 'quit' to exit): ")
                
                if user_prompt.lower() in ["quit", "exit", "q"]:
                    print("👋 Thank you for using the CRM service!")
                    break
                    
                if not user_prompt.strip():
                    print("Please enter a valid query.")
                    continue

                try:
                    response = await chat_with_crm_agent(agent, user_prompt)
                    print(f"\n👤 CRM Agent Response: {response}\n")
                        
                except Exception as e:
                    print(f"❌ Error processing request: {str(e)}")

    except Exception as e:
        print(f"❌ Failed to initialize CRM agent: {str(e)}")
        print("Please check your environment variables and Azure credentials.")


if __name__ == '__main__': 
    asyncio.run(main())
