"""
Insurance Policies Agent - Microsoft Agent Framework Implementation
Handles insurance policy research and product information queries using Agent Framework.
"""

import os
import asyncio
from dotenv import load_dotenv
from pathlib import Path

# Microsoft Agent Framework imports
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity.aio import AzureCliCredential

# Import policies functions
try:
    from .policies_functions import policies_functions
except ImportError:
    from policies_functions import policies_functions


async def create_policies_agent(chat_client: AzureOpenAIChatClient) -> ChatAgent:
    """
    Create an Insurance Policies agent using Microsoft Agent Framework.
    
    Args:
        chat_client: The Azure OpenAI chat client
        
    Returns:
        ChatAgent configured for insurance policies operations
    """
    instructions = """You are an assistant that provides insurance policy information and product research insights.

**Your Task:**
- Use the 'search_insurance_policies' function to find relevant insurance policy information and product details
- Provide detailed information about insurance coverage, benefits, and policy terms
- Summarize key policy features and coverage options
- Don't use your general knowledge - rely ONLY on the search results from the provided functions
- Provide CONCISE and actionable insurance insights
- Focus on policy coverage details, benefits, exclusions, and recommendations based on the search results"""
    
    # Create agent with insurance policies tools
    agent = chat_client.as_agent(
        instructions=instructions,
        name="policies_agent",
        tools=policies_functions
    )
    
    print(f"✅ Created Insurance Policies agent: {agent.name}")
    return agent


async def main(): 
    """
    Main function to initialize and run the Insurance Policies agent using Agent Framework.
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
            
            agent = await create_policies_agent(chat_client)
            
            print(f"\n🛡️ You're chatting with: {agent.name}")
            print("This agent provides insurance policy information and product insights.")
            print("Type 'quit' to exit.\n")

            while True:
                user_prompt = input("Enter your insurance query (or type 'quit' to exit): ")
                
                if user_prompt.lower() in ["quit", "exit", "q"]:
                    print("👋 Thank you for using the Insurance Policies service!")
                    break
                    
                if not user_prompt.strip():
                    print("Please enter a valid query.")
                    continue

                try:
                    thread = agent.get_new_thread()
                    response = await agent.run(user_prompt, thread=thread)
                    print(f"\n🛡️ Insurance Policies Agent Response: {response.text}\n")
                        
                except Exception as e:
                    print(f"❌ Error processing request: {str(e)}")

    except Exception as e:
        print(f"❌ Failed to initialize Insurance Policies agent: {str(e)}")


if __name__ == '__main__': 
    asyncio.run(main())
