"""
Insurance Policies Agent Package

This package contains the insurance policies agent implementation using Azure AI Foundry Agent Service libraries.
It provides functionality to search and retrieve insurance policy information.

Modules:
    policies_agent: Main insurance policies agent implementation
    policies_functions: Insurance policies search functions using Azure AI Search
"""

from .policies_agent import create_policies_agent
from .policies_functions import policies_functions

__all__ = [
    'create_policies_agent',
    'policies_functions'
]
