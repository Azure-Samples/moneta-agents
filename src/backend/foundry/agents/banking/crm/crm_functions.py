import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# Import tracing utilities from backend root
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from tracing import get_tracing_manager

def load_from_crm_by_client_fullname(client_fullname: str) -> str:
    """
    Load client data from CRM by full name.
    
    Args:
        client_fullname (str): The full name of the client to search for
        
    Returns:
        str: JSON string containing client information or error message
    """
    tracing_manager = get_tracing_manager()
    
    try:
        with tracing_manager.trace_function_call(
            "load_from_crm_by_client_fullname",
            parameters={"client_fullname": client_fullname}
        ):
            # Get the directory of the current script
            script_dir = Path(__file__).parent
            json_file_path = script_dir / "client_sample.json"
        
        # Check if the file exists
        if not json_file_path.exists():
            return json.dumps({"error": "CRM data file not found"})
        
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
                    "financialInformation": client_data.get('financialInformation'),
                    "investmentProfile": client_data.get('investmentProfile'),
                    "declared_source_of_wealth": client_data.get('declared_source_of_wealth'),
                    "portfolio": client_data.get('portfolio')
                }
            }
            return json.dumps(result, indent=2)
        else:
            return json.dumps({"error": f"Client with full name '{client_fullname}' not found in CRM"})
            
    except FileNotFoundError:
        return json.dumps({"error": "CRM data file not found"})
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON format in CRM data file"})
    except Exception as e:
        # Log error in trace if available
        if tracing_manager and tracing_manager.is_configured:
            with tracing_manager.trace_function_call(
                "load_from_crm_by_client_fullname_error",
                parameters={"error": str(e), "client_fullname": client_fullname}
            ):
                pass
        return json.dumps({"error": f"Error accessing CRM data: {str(e)}"})


def load_from_crm_by_client_id(client_id: str) -> str:
    """
    Load client data from CRM by client ID.
    
    Args:
        client_id (str): The client ID to search for
        
    Returns:
        str: JSON string containing client information or error message
    """
    tracing_manager = get_tracing_manager()
    
    try:
        with tracing_manager.trace_function_call(
            "load_from_crm_by_client_id",
            parameters={"client_id": client_id}
        ):
            # Get the directory of the current script
            script_dir = Path(__file__).parent
            json_file_path = script_dir / "client_sample.json"
            
            # Check if the file exists
            if not json_file_path.exists():
                return json.dumps({"error": "CRM data file not found"})
        
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
                    "financialInformation": client_data.get('financialInformation'),
                    "investmentProfile": client_data.get('investmentProfile'),
                    "declared_source_of_wealth": client_data.get('declared_source_of_wealth'),
                    "portfolio": client_data.get('portfolio')
                }
            }
            return json.dumps(result, indent=2)
        else:
            return json.dumps({"error": f"Client with ID '{client_id}' not found in CRM"})
            
    except FileNotFoundError:
        return json.dumps({"error": "CRM data file not found"})
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON format in CRM data file"})
    except Exception as e:
        # Log error in trace if available
        if tracing_manager and tracing_manager.is_configured:
            with tracing_manager.trace_function_call(
                "load_from_crm_by_client_id_error",
                parameters={"error": str(e), "client_id": client_id}
            ):
                pass
        return json.dumps({"error": f"Error accessing CRM data: {str(e)}"})


# Define a list of callable functions for CRM operations
crm_functions: list[Callable[..., Any]] = [
    load_from_crm_by_client_fullname,
    load_from_crm_by_client_id
]
