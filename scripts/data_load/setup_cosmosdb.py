import sys
import os
import json
import subprocess
import logging
from rich.logging import RichHandler
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from crm_store import CRMStore

def load_azd_env():
    """Get path to current azd env file and load file using python-dotenv"""
    result = subprocess.run("azd env list -o json", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception("Error loading azd env")
    env_json = json.loads(result.stdout)
    env_file_path = None
    for entry in env_json:
        if entry["IsDefault"]:
            env_file_path = entry["DotEnvPath"]
    if not env_file_path:
        raise Exception("No default azd env file found")
    load_dotenv(env_file_path, override=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)])
    logger = logging.getLogger("moneta")
    logger.setLevel(logging.INFO)


    load_azd_env()

    db = CRMStore(
            url=os.getenv("COSMOSDB_ENDPOINT"),
            key=DefaultAzureCredential(),
            database_name=os.getenv("COSMOSDB_DATABASE_NAME"),
            container_name=os.getenv("COSMOSDB_CONTAINER_CLIENT_NAME")
        )

    # Loading Insurance Customer
    logger.info("Loading Insurance Customer")
    ins_customer = ''
    try:  
        # Open and read the JSON file
        with open('src/data/customer-profiles/customer-insurance.json', 'r') as file:
            ins_customer =  json.load(file)
    except Exception as e:
        print(f"An unexpected error occurred: {e}") 

    db.create_customer_profile(ins_customer)


    # Loading Banking
    logger.info("Loading Banking Customer")
    banking_customer = ''
    try:  
        # Open and read the JSON file
        with open('src/data/customer-profiles/customer-banking.json', 'r') as file:
            banking_customer =  json.load(file)
    except Exception as e:
        print(f"An unexpected error occurred: {e}") 

    db.create_customer_profile(banking_customer)