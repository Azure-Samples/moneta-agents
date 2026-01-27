"""
CIO Agent - Microsoft Agent Framework Implementation
Handles investment research and market analysis queries using Agent Framework.
"""

import os
import asyncio
from dotenv import load_dotenv
from pathlib import Path

# Microsoft Agent Framework imports
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity.aio import AzureCliCredential

# Import CIO functions
from cio_functions import cio_functions


async def create_cio_agent(chat_client: AzureOpenAIChatClient) -> ChatAgent:
    """
    Create a CIO agent using Microsoft Agent Framework.
    
    Args:
        chat_client: The Azure OpenAI chat client
        
    Returns:
        ChatAgent configured for CIO operations
    """
    instructions = """You are an assistant that provides Chief Investment Office (CIO) views and investment research insights.

**Your Task:**
- Use the 'search_investment_research' function to find relevant CIO views and market analysis
- Provide strategic investment recommendations based on CIO research
- Summarize key investment themes and market outlooks
- Don't use your general knowledge - rely ONLY on the search results from the provided functions
- Provide CONCISE and actionable investment insights
- Focus on strategic asset allocation, market trends, and investment opportunities"""
    
    # Create agent with CIO tools
    agent = chat_client.as_agent(
        instructions=instructions,
        name="cio_agent",
        tools=cio_functions
    )
    
    print(f"✅ Created CIO agent: {agent.name}")
    return agent


async def main(): 
    """
    Main function to initialize and run the CIO agent using Agent Framework.
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
            
            agent = await create_cio_agent(chat_client)
            
            print(f"\n📈 You're chatting with: {agent.name}")
            print("This agent provides CIO views and investment research insights.")
            print("Type 'quit' to exit.\n")

            while True:
                user_prompt = input("Enter your investment query (or type 'quit' to exit): ")
                
                if user_prompt.lower() in ["quit", "exit", "q"]:
                    print("👋 Thank you for using the CIO service!")
                    break
                    
                if not user_prompt.strip():
                    print("Please enter a valid query.")
                    continue

                try:
                    thread = agent.get_new_thread()
                    response = await agent.run(user_prompt, thread=thread)
                    print(f"\n📈 CIO Agent Response: {response.text}\n")
                        
                except Exception as e:
                    print(f"❌ Error processing request: {str(e)}")

    except Exception as e:
        print(f"❌ Failed to initialize CIO agent: {str(e)}")


if __name__ == '__main__': 
    asyncio.run(main())
