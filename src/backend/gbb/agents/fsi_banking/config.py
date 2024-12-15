import os
from gbb.genai_vanilla_agents.llm import AzureOpenAILLM

def create_llm():
    return AzureOpenAILLM({
        "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
        "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
    })