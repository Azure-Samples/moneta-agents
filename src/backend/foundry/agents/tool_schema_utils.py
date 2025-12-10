"""
Tool Schema Utilities for Microsoft Foundry Agent Registration.

This module provides utilities to convert Python functions to FunctionTool schemas
that can be registered with Microsoft Foundry agents.

The generated schemas allow Foundry to display tools in the UI and understand
the tool signatures, even though the actual execution happens locally via the
Agent Framework.
"""

import inspect
import json
from typing import Any, Callable, get_type_hints, Annotated
from azure.ai.projects.models import FunctionTool


def python_type_to_json_schema(python_type: type) -> dict:
    """
    Convert a Python type to a JSON Schema type definition.
    
    Args:
        python_type: The Python type to convert
        
    Returns:
        JSON Schema type definition
    """
    type_mapping = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
        type(None): {"type": "null"},
    }
    
    # Handle basic types
    if python_type in type_mapping:
        return type_mapping[python_type]
    
    # Handle Optional types
    origin = getattr(python_type, "__origin__", None)
    if origin is not None:
        args = getattr(python_type, "__args__", ())
        
        # Handle list[T]
        if origin is list and args:
            return {
                "type": "array",
                "items": python_type_to_json_schema(args[0])
            }
        
        # Handle dict[K, V]
        if origin is dict:
            return {"type": "object"}
        
        # Handle Optional[T] (Union[T, None])
        if origin is type(None) or (hasattr(origin, "__name__") and origin.__name__ == "Union"):
            non_none_types = [t for t in args if t is not type(None)]
            if len(non_none_types) == 1:
                return python_type_to_json_schema(non_none_types[0])
    
    # Default to string for unknown types
    return {"type": "string"}


def extract_annotated_description(annotation) -> tuple[type, str | None]:
    """
    Extract the type and description from an Annotated type hint.
    
    Args:
        annotation: The type annotation (may be Annotated[T, "description"])
        
    Returns:
        Tuple of (actual_type, description or None)
    """
    origin = getattr(annotation, "__origin__", None)
    
    if origin is Annotated:
        args = getattr(annotation, "__args__", ())
        if len(args) >= 2:
            actual_type = args[0]
            # Look for a string description in the remaining args
            description = None
            for arg in args[1:]:
                if isinstance(arg, str):
                    description = arg
                    break
            return actual_type, description
    
    return annotation, None


def function_to_tool_schema(func: Callable) -> FunctionTool:
    """
    Convert a Python function to a FunctionTool schema for Foundry registration.
    
    Args:
        func: The Python function to convert
        
    Returns:
        FunctionTool instance that can be registered with Foundry agents
    """
    # Get function name and docstring
    func_name = func.__name__
    docstring = inspect.getdoc(func) or f"Function {func_name}"
    
    # Parse docstring for description (first line)
    description_lines = docstring.split("\n")
    description = description_lines[0].strip() if description_lines else func_name
    
    # Get function signature and type hints
    sig = inspect.signature(func)
    try:
        type_hints = get_type_hints(func, include_extras=True)
    except Exception:
        type_hints = {}
    
    # Build parameters schema
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        # Skip self parameter
        if param_name == "self":
            continue
        
        # Get type annotation
        annotation = type_hints.get(param_name, str)
        
        # Extract type and description from Annotated if present
        actual_type, param_description = extract_annotated_description(annotation)
        
        # Convert to JSON schema type
        param_schema = python_type_to_json_schema(actual_type)
        
        # Try to extract description from docstring Args section
        if not param_description:
            param_description = extract_param_description_from_docstring(docstring, param_name)
        
        if param_description:
            param_schema["description"] = param_description
        
        properties[param_name] = param_schema
        
        # Check if parameter is required (no default value)
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
    
    # Build the parameters JSON schema
    parameters = {
        "type": "object",
        "properties": properties,
    }
    
    if required:
        parameters["required"] = required
    
    # Create FunctionTool
    return FunctionTool(
        name=func_name,
        description=description,
        parameters=parameters
    )


def extract_param_description_from_docstring(docstring: str, param_name: str) -> str | None:
    """
    Extract parameter description from a Google-style docstring.
    
    Args:
        docstring: The function's docstring
        param_name: The parameter name to find
        
    Returns:
        Parameter description or None if not found
    """
    if not docstring:
        return None
    
    lines = docstring.split("\n")
    in_args_section = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check for Args: section
        if stripped.lower() in ("args:", "arguments:", "parameters:"):
            in_args_section = True
            continue
        
        # Check for end of Args section
        if in_args_section and stripped and not stripped.startswith(" ") and not line.startswith("\t"):
            if stripped.lower() in ("returns:", "raises:", "yields:", "examples:", "example:", "note:", "notes:"):
                in_args_section = False
                continue
        
        # Look for parameter in Args section
        if in_args_section:
            # Match pattern: param_name: description or param_name (type): description
            if stripped.startswith(f"{param_name}:") or stripped.startswith(f"{param_name} ("):
                # Extract description after the colon
                if ":" in stripped:
                    parts = stripped.split(":", 1)
                    if len(parts) > 1:
                        description = parts[1].strip()
                        # Check for continuation on next lines
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j]
                            if next_line.strip() and (next_line.startswith("        ") or next_line.startswith("\t\t")):
                                description += " " + next_line.strip()
                                j += 1
                            else:
                                break
                        return description
    
    return None


def functions_to_tool_schemas(functions: list[Callable]) -> list[FunctionTool]:
    """
    Convert a list of Python functions to FunctionTool schemas.
    
    Args:
        functions: List of Python functions to convert
        
    Returns:
        List of FunctionTool instances
    """
    return [function_to_tool_schema(func) for func in functions]


def create_handoff_tool_schemas(agent_names: list[str]) -> list[FunctionTool]:
    """
    Create FunctionTool schemas for handoff tools.
    
    The HandoffBuilder pattern uses tools named 'handoff_to_<agent_name>' to route
    requests to specialist agents. This function creates the tool schemas so they
    can be registered with the coordinator agent in Foundry.
    
    Args:
        agent_names: List of agent names to create handoff tools for
                    (e.g., ["ins-crm-agent", "ins-policies-agent"])
        
    Returns:
        List of FunctionTool instances for handoff tools
    """
    handoff_tools = []
    
    for agent_name in agent_names:
        tool_name = f"handoff_to_{agent_name}"
        
        tool = FunctionTool(
            name=tool_name,
            description=f"Hand off the conversation to the {agent_name} specialist. Use this tool to transfer the user's request to {agent_name} for handling.",
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Optional message to include with the handoff"
                    }
                },
                "required": []
            }
        )
        handoff_tools.append(tool)
    
    return handoff_tools


def tool_schemas_to_dicts(tools: list[FunctionTool]) -> list[dict]:
    """
    Convert FunctionTool instances to dictionaries for JSON serialization.
    
    Args:
        tools: List of FunctionTool instances
        
    Returns:
        List of tool dictionaries
    """
    return [tool.as_dict() for tool in tools]


def create_handoff_tools(agent_names: list[str]) -> list:
    """
    Create actual callable handoff tool functions for the coordinator.
    
    When using Foundry-hosted agents, the HandoffBuilder's auto_register_handoff_tools
    cannot dynamically inject tools into the remote agent. Instead, we need to:
    1. Register tool schemas with Foundry (via create_handoff_tool_schemas)
    2. Bind actual callable functions locally (via this function)
    
    This function creates Python functions decorated with @ai_function that match
    the handoff tool schemas registered with Foundry. When the Foundry model calls
    handoff_to_<agent_name>, the local framework can execute the matching function.
    
    Args:
        agent_names: List of agent names to create handoff tools for
                    (e.g., ["ins-crm-agent", "ins-policies-agent"])
        
    Returns:
        List of callable AIFunction instances for handoff tools
    """
    from agent_framework import ai_function
    
    handoff_tools = []
    
    for agent_name in agent_names:
        tool_name = f"handoff_to_{agent_name}"
        description = f"Hand off the conversation to the {agent_name} specialist. Use this tool to transfer the user's request to {agent_name} for handling."
        
        # Create the handoff function with proper name binding
        # The function body returns a deterministic acknowledgement like HandoffBuilder does
        def make_handoff_fn(name: str, target: str):
            @ai_function(name=name, description=f"Handoff to the {target} agent.")
            def handoff_fn(message: str = "") -> str:
                """Hand off the conversation to a specialist agent."""
                return f"Handoff to {target}"
            return handoff_fn
        
        handoff_fn = make_handoff_fn(tool_name, agent_name)
        handoff_tools.append(handoff_fn)
    
    return handoff_tools


# Test the conversion if run directly
if __name__ == "__main__":
    # Example function to test
    def example_function(
        query: Annotated[str, "The search query"],
        limit: int = 10
    ) -> str:
        """
        Search for items matching the query.
        
        Args:
            query: The search query string
            limit: Maximum number of results to return
            
        Returns:
            JSON string containing search results
        """
        return "{}"
    
    tool = function_to_tool_schema(example_function)
    print("Generated FunctionTool:")
    print(json.dumps(tool.as_dict(), indent=2))
