"""
CRM Agent Package

This package contains the CRM agent implementation using Azure AI Foundry Agent Service libraries.
It provides functionality to process user requests about client data and client portfolios.

Modules:
    crm_agent: Main CRM agent implementation
    crm_functions: CRM data access functions
"""

from .crm_functions import crm_functions, load_from_crm_by_client_fullname, load_from_crm_by_client_id

__all__ = [
    'crm_functions',
    'load_from_crm_by_client_fullname', 
    'load_from_crm_by_client_id'
]
