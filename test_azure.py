from services.llm_service import llm_manager
from config import Config
import os
from dotenv import load_dotenv

load_dotenv()

# Manually refresh config if needed
llm_manager.azure_config = {
    "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "key": os.getenv("AZURE_OPENAI_API_KEY"),
    "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-35-turbo"),
    "version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
}

print(f"Testing Azure Endpoint: {llm_manager.azure_config['endpoint']}")
res = llm_manager.query_azure("Say hello in one word")
print(f"RESULT: {res}")
