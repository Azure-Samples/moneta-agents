import os
from dotenv import load_dotenv
from gbb.genai_vanilla_agents.llm import AzureOpenAILLM
load_dotenv()

llm = AzureOpenAILLM({
    "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
})