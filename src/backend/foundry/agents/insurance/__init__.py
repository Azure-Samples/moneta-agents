"""
Insurance Agents Package

This package contains the insurance-related agent implementations using Azure AI Foundry Agent Service libraries.
It provides functionality to process user requests about insurance policies and client data.

Sub-packages:
    policies: Insurance policies search and research agent
    crm: Insurance CRM agent for client policy data
"""

from .policies import create_policies_agent, policies_functions
from .crm import create_crm_insurance_agent, crm_insurance_functions

__all__ = [
    'create_policies_agent',
    'policies_functions',
    'create_crm_insurance_agent',
    'crm_insurance_functions'
]
