"""
Insurance CRM Functions for accessing client policy data and insurance information.
This module provides functions to retrieve client insurance policy data from CRM.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# Import tracing utilities from backend root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent.parent))
from tracing import get_tracing_manager


def load_insurance_client_by_fullname(client_fullname: str) -> str:
    """
    Load insurance client data from CRM by full name.
    
    Args:
        client_fullname (str): The full name of the client to search for
        
    Returns:
        str: JSON string containing client insurance information or error message
    """
    tracing_manager = get_tracing_manager()
    
    try:
        with tracing_manager.trace_function_call(
            "load_insurance_client_by_fullname",
            parameters={"client_fullname": client_fullname}
        ):
            # Get the path to the insurance customer data
            # Path: crm -> insurance -> agents -> foundry -> backend -> src -> data/customer-profiles
            data_dir = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "customer-profiles"
            json_file_path = data_dir / "customer-insurance.json"
        
            # Check if the file exists
            if not json_file_path.exists():
                return json.dumps({"error": "Insurance CRM data file not found"})
            
            # Load the JSON data
            with open(json_file_path, 'r', encoding='utf-8') as file:
                client_data = json.load(file)
            
            # Check if the full name matches (case-insensitive)
            if client_data.get('fullName', '').lower() == client_fullname.lower():
                # Return the relevant client information
                result = {
                    "status": "success",
                    "client": {
                        "id": client_data.get('id'),
                        "clientID": client_data.get('clientID'),
                        "fullName": client_data.get('fullName'),
                        "firstName": client_data.get('firstName'),
                        "lastName": client_data.get('lastName'),
                        "dateOfBirth": client_data.get('dateOfBirth'),
                        "nationality": client_data.get('nationality'),
                        "contactDetails": client_data.get('contactDetails'),
                        "address": client_data.get('address'),
                        "policies": client_data.get('policies', [])
                    }
                }
                return json.dumps(result, indent=2)
            else:
                return json.dumps({"error": f"Insurance client with full name '{client_fullname}' not found in CRM"})
            
    except FileNotFoundError:
        return json.dumps({"error": "Insurance CRM data file not found"})
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON format in Insurance CRM data file"})
    except Exception as e:
        # Log error in trace if available
        if tracing_manager and tracing_manager.is_configured:
            with tracing_manager.trace_function_call(
                "load_insurance_client_by_fullname_error",
                parameters={"error": str(e), "client_fullname": client_fullname}
            ):
                pass
        return json.dumps({"error": f"Error accessing Insurance CRM data: {str(e)}"})


def load_insurance_client_by_id(client_id: str) -> str:
    """
    Load insurance client data from CRM by client ID.
    
    Args:
        client_id (str): The client ID to search for
        
    Returns:
        str: JSON string containing client insurance information or error message
    """
    tracing_manager = get_tracing_manager()
    
    try:
        with tracing_manager.trace_function_call(
            "load_insurance_client_by_id",
            parameters={"client_id": client_id}
        ):
            # Get the path to the insurance customer data
            # Path: crm -> insurance -> agents -> foundry -> backend -> src -> data/customer-profiles
            data_dir = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "customer-profiles"
            json_file_path = data_dir / "customer-insurance.json"
            
            # Check if the file exists
            if not json_file_path.exists():
                return json.dumps({"error": "Insurance CRM data file not found"})
        
            # Load the JSON data
            with open(json_file_path, 'r', encoding='utf-8') as file:
                client_data = json.load(file)
            
            # Check if the client ID matches
            if client_data.get('clientID') == client_id or client_data.get('id') == client_id:
                # Return the relevant client information
                result = {
                    "status": "success",
                    "client": {
                        "id": client_data.get('id'),
                        "clientID": client_data.get('clientID'),
                        "fullName": client_data.get('fullName'),
                        "firstName": client_data.get('firstName'),
                        "lastName": client_data.get('lastName'),
                        "dateOfBirth": client_data.get('dateOfBirth'),
                        "nationality": client_data.get('nationality'),
                        "contactDetails": client_data.get('contactDetails'),
                        "address": client_data.get('address'),
                        "policies": client_data.get('policies', [])
                    }
                }
                return json.dumps(result, indent=2)
            else:
                return json.dumps({"error": f"Insurance client with ID '{client_id}' not found in CRM"})
            
    except FileNotFoundError:
        return json.dumps({"error": "Insurance CRM data file not found"})
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON format in Insurance CRM data file"})
    except Exception as e:
        # Log error in trace if available
        if tracing_manager and tracing_manager.is_configured:
            with tracing_manager.trace_function_call(
                "load_insurance_client_by_id_error",
                parameters={"error": str(e), "client_id": client_id}
            ):
                pass
        return json.dumps({"error": f"Error accessing Insurance CRM data: {str(e)}"})


def get_client_policy_details(client_id: str, policy_no: str) -> str:
    """
    Get details for a specific policy of an insurance client.
    
    Args:
        client_id (str): The client ID to search for
        policy_no (str): The policy number to retrieve details for
        
    Returns:
        str: JSON string containing policy details or error message
    """
    tracing_manager = get_tracing_manager()
    
    try:
        with tracing_manager.trace_function_call(
            "get_client_policy_details",
            parameters={"client_id": client_id, "policy_no": policy_no}
        ):
            # Get the path to the insurance customer data
            # Path: crm -> insurance -> agents -> foundry -> backend -> src -> data/customer-profiles
            data_dir = Path(__file__).parent.parent.parent.parent.parent.parent / "data" / "customer-profiles"
            json_file_path = data_dir / "customer-insurance.json"
            
            # Check if the file exists
            if not json_file_path.exists():
                return json.dumps({"error": "Insurance CRM data file not found"})
        
            # Load the JSON data
            with open(json_file_path, 'r', encoding='utf-8') as file:
                client_data = json.load(file)
            
            # Check if the client ID matches
            if client_data.get('clientID') != client_id and client_data.get('id') != client_id:
                return json.dumps({"error": f"Insurance client with ID '{client_id}' not found in CRM"})
            
            # Find the specific policy
            policies = client_data.get('policies', [])
            for policy in policies:
                if policy.get('PolicyNo') == policy_no:
                    result = {
                        "status": "success",
                        "client": {
                            "id": client_data.get('id'),
                            "fullName": client_data.get('fullName')
                        },
                        "policy": policy
                    }
                    return json.dumps(result, indent=2)
            
            return json.dumps({"error": f"Policy number '{policy_no}' not found for client '{client_id}'"})
            
    except FileNotFoundError:
        return json.dumps({"error": "Insurance CRM data file not found"})
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON format in Insurance CRM data file"})
    except Exception as e:
        # Log error in trace if available
        if tracing_manager and tracing_manager.is_configured:
            with tracing_manager.trace_function_call(
                "get_client_policy_details_error",
                parameters={"error": str(e), "client_id": client_id, "policy_no": policy_no}
            ):
                pass
        return json.dumps({"error": f"Error accessing Insurance CRM data: {str(e)}"})


# Define a list of callable functions for Insurance CRM operations
crm_insurance_functions: list[Callable[..., Any]] = [
    load_insurance_client_by_fullname,
    load_insurance_client_by_id,
    get_client_policy_details
]
