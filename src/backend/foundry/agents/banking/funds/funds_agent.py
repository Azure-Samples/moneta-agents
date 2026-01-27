"""
Funds Agent - Microsoft Agent Framework Implementation
Handles funds and ETFs information queries using Agent Framework.
"""

import os
import asyncio
from dotenv import load_dotenv
from pathlib import Path

# Microsoft Agent Framework imports
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity.aio import AzureCliCredential

# Import Funds functions
from funds_functions import funds_functions


async def create_funds_agent(chat_client: AzureOpenAIChatClient) -> ChatAgent:
    """
    Create a Funds agent using Microsoft Agent Framework.
    
    Args:
        chat_client: The Azure OpenAI chat client
        
    Returns:
        ChatAgent configured for Funds operations
    """
    instructions = """You are an assistant that provides information about investment funds and ETFs.

**Your Task:**
- Use the 'search_funds_and_etfs' function to find relevant fund and ETF information
- Provide details about fund performance, characteristics, and suitability
- Help users understand different investment products and their features
- Don't use your general knowledge - rely ONLY on the search results from the provided functions
- Provide CONCISE and clear fund information
- Focus on fund objectives, performance metrics, risk profiles, and investment strategies"""
    
    # Create agent with Funds tools
    agent = chat_client.as_agent(
        instructions=instructions,
        name="funds_agent",
        tools=funds_functions
    )
    
    print(f"✅ Created Funds agent: {agent.name}")
    return agent


async def main(): 
    """
    Main function to initialize and run the Funds agent using Agent Framework.
    """
    os.system('cls' if os.name=='nt' else 'clear')
    load_dotenv()
    
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    
    if not endpoint:
        print("Error: AZURE_OPENAI_ENDPOINT environment variable is not set")
        return

    try:
        async with AzureCliCredential() as credential:
            chat_client = AzureOpenAIChatClient(
                endpoint=endpoint,
                deployment_name=deployment_name,
                credential=credential
            )
            
            agent = await create_funds_agent(chat_client)
            
            print(f"\n💰 You're chatting with: {agent.name}")
            print("This agent provides information about funds and ETFs.")
            print("Type 'quit' to exit.\n")

            while True:
                user_prompt = input("Enter your funds query (or type 'quit' to exit): ")
                
                if user_prompt.lower() in ["quit", "exit", "q"]:
                    print("👋 Thank you for using the Funds service!")
                    break
                    
                if not user_prompt.strip():
                    print("Please enter a valid query.")
                    continue

                try:
                    thread = agent.get_new_thread()
                    response = await agent.run(user_prompt, thread=thread)
                    print(f"\n💰 Funds Agent Response: {response.text}\n")
                        
                except Exception as e:
                    print(f"❌ Error processing request: {str(e)}")

    except Exception as e:
        print(f"❌ Failed to initialize Funds agent: {str(e)}")


if __name__ == '__main__': 
    asyncio.run(main())
