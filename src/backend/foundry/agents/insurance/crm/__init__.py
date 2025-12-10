"""
Insurance CRM Agent Package

This package contains the insurance CRM agent implementation using Azure AI Foundry Agent Service libraries.
It provides functionality to process user requests about client insurance policies and data.

Modules:
    crm_insurance_agent: Main insurance CRM agent implementation
    crm_insurance_functions: Insurance CRM data access functions
"""

from .crm_insurance_agent import create_crm_insurance_agent
from .crm_insurance_functions import crm_insurance_functions

__all__ = [
    'create_crm_insurance_agent',
    'crm_insurance_functions'
]
