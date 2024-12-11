import io
import os
import uuid
import json
import subprocess
import re
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient
from dotenv import load_dotenv

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

load_azd_env()
# Variables
account_url = os.getenv("BLOB_ACCOUNT_URL")
credentials = DefaultAzureCredential()
# Create the BlobServiceClient object

blob_service_client = BlobServiceClient(account_url, credential=credentials)

# Functions for sanitizing and uploading files
def sanitize_folder_file_name(value):
    value = value.lower()
    sanitized_value = re.sub(r"[^a-z0-9-.]", "-", value)
    return sanitized_value

def rename_files_and_folders(directory_path: str):
    for root, dirs, files in os.walk(directory_path, topdown=False):
        for file_name in files:
            sanitized_file_name = sanitize_folder_file_name(file_name)
            original_file_path = os.path.join(root, file_name)
            sanitized_file_path = os.path.join(root, sanitized_file_name)
            if original_file_path != sanitized_file_path:
                os.rename(original_file_path, sanitized_file_path)
        for dir_name in dirs:
            sanitized_dir_name = sanitize_folder_file_name(dir_name)
            original_dir_path = os.path.join(root, dir_name)
            sanitized_dir_path = os.path.join(root, sanitized_dir_name)
            if original_dir_path != sanitized_dir_path:
                os.rename(original_dir_path, sanitized_dir_path)

current_working_directory = os.getcwd()
data_directory_path = os.path.abspath(os.path.join(current_working_directory, 'src/data'))
rename_files_and_folders(data_directory_path)

def upload_files_from_directory(directory_path: str):
    for folder_name in os.listdir(directory_path):
        folder_path = os.path.join(directory_path, folder_name)
        if os.path.isdir(folder_path):
            container_client = blob_service_client.get_container_client(folder_name)
            if not container_client.exists():
                container_client.create_container()
            for file_name in os.listdir(folder_path):
                print(f"Uploading file: {folder_name}/{file_name}...")
                file_path = os.path.join(folder_path, file_name)
                if os.path.isfile(file_path):
                    blob_client = BlobClient(
                        account_url=account_url,
                        container_name=folder_name,
                        blob_name=file_name,
                        credential=credentials
                    )
                    with open(file_path, "rb") as data:
                        blob_client.upload_blob(data, overwrite=True)
    print("Upload complete.")
# Upload files from the data directory
upload_files_from_directory(data_directory_path)