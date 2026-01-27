"""
Consolidated tracing setup for Azure AI Foundry.

Uses Agent Framework's configure_otel_providers for proper span nesting.
Sends traces to Azure Application Insights connected to Foundry project.

Foundry UI requires specific OpenTelemetry GenAI semantic conventions:
- gen_ai.conversation.id: Session/thread ID for trace correlation (CRITICAL)
- gen_ai.agent.id: Unique agent identifier
- gen_ai.agent.name: Human-readable agent name
- gen_ai.operation.name: 'invoke_agent' for agent calls
- gen_ai.provider.name: 'microsoft.agent_framework'

See: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
_backend_dir = Path(__file__).parent
_env_file = _backend_dir / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

# Suppress noisy loggers
logging.getLogger("opentelemetry.sdk.trace").setLevel(logging.ERROR)
logging.getLogger("azure.monitor.opentelemetry.exporter.export").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

_TRACING_CONFIGURED = False
_CONVERSATION_ID_HOLDER = {}  # Thread-safe holder for conversation ID propagation


def _get_foundry_appinsights_connection_string() -> str:
    """
    Get Application Insights connection string from Foundry project.
    This ensures traces appear in Foundry portal's Tracing tab.
    """
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    if not project_endpoint:
        return None
    
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
        
        project_client = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint=project_endpoint
        )
        
        conn_str = project_client.telemetry.get_application_insights_connection_string()
        print(f"📊 Got App Insights connection string from Foundry project")
        return conn_str
    except Exception as e:
        print(f"⚠️  Could not get connection string from Foundry: {e}")
        return None


def setup_tracing(
    connection_string: str = None,
    service_name: str = "moneta-agents"
) -> bool:
    """
    Configure tracing using Agent Framework's configure_otel_providers.
    
    This ensures proper span nesting for:
    - invoke_agent spans
    - chat model spans  
    - execute_tool spans
    
    Call this ONCE at application startup.
    """
    global _TRACING_CONFIGURED
    
    if _TRACING_CONFIGURED:
        return True
    
    # Priority: 1) Provided connection string, 2) Foundry project's App Insights, 3) Env var
    conn_str = connection_string
    if not conn_str:
        conn_str = _get_foundry_appinsights_connection_string()
    if not conn_str:
        conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    if not conn_str:
        print("⚠️  No Application Insights connection string available - tracing disabled")
        return False
    
    try:
        # Use Agent Framework's configure_otel_providers with Azure Monitor exporter
        # This properly instruments agent spans with parent-child relationships
        from agent_framework.observability import configure_otel_providers
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
        
        # Create Azure Monitor exporter
        azure_exporter = AzureMonitorTraceExporter(connection_string=conn_str)
        
        configure_otel_providers(
            enable_sensitive_data=True,  # Include prompts/responses in traces
            exporters=[azure_exporter]
        )
        
        _TRACING_CONFIGURED = True
        print(f"✅ Tracing configured via Agent Framework configure_otel_providers")
        print(f"   - Application Insights: configured (Foundry-connected)")
        print(f"   - Sensitive data recording: enabled")
        return True
        
    except ImportError as e:
        print(f"⚠️  Agent Framework observability not available: {e}")
        print("   Falling back to manual OpenTelemetry setup...")
        return _setup_manual_tracing(conn_str, service_name)
    except Exception as e:
        print(f"❌ Agent Framework observability failed: {e}")
        print("   Falling back to manual OpenTelemetry setup...")
        return _setup_manual_tracing(conn_str, service_name)


def _setup_manual_tracing(conn_str: str, service_name: str) -> bool:
    """Fallback manual OpenTelemetry setup if Agent Framework is unavailable."""
    global _TRACING_CONFIGURED
    
    # Enable content recording for Gen AI traces
    os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "true"
    
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.semconv.resource import ResourceAttributes
        from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
        
        # Create resource with service name
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: service_name
        })
        
        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)
        
        # Add Azure Monitor exporter
        exporter = AzureMonitorTraceExporter(connection_string=conn_str)
        tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        
        # Set as global tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        print(f"📊 Tracing: Azure Monitor exporter configured (manual)")
        
        # Enable Azure AI Inference instrumentor for Foundry Gen AI traces
        try:
            from azure.ai.inference.tracing import AIInferenceInstrumentor
            AIInferenceInstrumentor().instrument()
            print(f"📊 Tracing: AI Inference instrumentor enabled")
        except Exception as e:
            print(f"⚠️  AIInferenceInstrumentor: {e}")
        
        _TRACING_CONFIGURED = True
        print(f"✅ Tracing configured for App Insights (manual fallback)")
        return True
        
    except Exception as e:
        print(f"❌ Manual tracing configuration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_tracer(name: str = __name__):
    """Get an OpenTelemetry tracer for custom spans."""
    try:
        # Prefer Agent Framework's get_tracer if available
        from agent_framework.observability import get_tracer as af_get_tracer
        return af_get_tracer()
    except ImportError:
        from opentelemetry import trace
        return trace.get_tracer(name)


def set_conversation_context(conversation_id: str, user_id: str = None, mode: str = None):
    """
    Set the conversation context for attribute propagation to child spans.
    
    This stores the conversation ID and other attributes that should be
    propagated to all child spans within this conversation context.
    Required for Foundry UI to properly display agent-level traces.
    
    Args:
        conversation_id: The unique conversation/session ID
        user_id: Optional user identifier
        mode: Optional mode indicator (e.g., 'foundry' or 'azure_openai')
    """
    import threading
    thread_id = threading.current_thread().ident
    _CONVERSATION_ID_HOLDER[thread_id] = {
        "gen_ai.conversation.id": conversation_id,
        "session.id": conversation_id,
    }
    if user_id:
        _CONVERSATION_ID_HOLDER[thread_id]["user.id"] = user_id
    if mode:
        _CONVERSATION_ID_HOLDER[thread_id]["session.mode"] = mode


def get_conversation_context() -> dict:
    """
    Get the current conversation context for attribute propagation.
    
    Returns:
        Dictionary of attributes to propagate to child spans
    """
    import threading
    thread_id = threading.current_thread().ident
    return _CONVERSATION_ID_HOLDER.get(thread_id, {})


def clear_conversation_context():
    """Clear the conversation context after processing is complete."""
    import threading
    thread_id = threading.current_thread().ident
    if thread_id in _CONVERSATION_ID_HOLDER:
        del _CONVERSATION_ID_HOLDER[thread_id]


def create_foundry_span(tracer, name: str, conversation_id: str, agent_name: str = None, 
                        agent_id: str = None, model: str = None, **extra_attributes):
    """
    Create a span with all required Foundry attributes for proper trace correlation.
    
    This is a helper function to create spans that will be properly displayed
    in the Foundry UI at the agent level.
    
    Args:
        tracer: The OpenTelemetry tracer
        name: Span name
        conversation_id: The conversation/session ID (CRITICAL for Foundry)
        agent_name: Human-readable agent name
        agent_id: Unique agent identifier
        model: Model deployment name
        **extra_attributes: Additional attributes to add
        
    Returns:
        A context manager for the span
    """
    from opentelemetry.trace import SpanKind
    
    # Build required attributes per OpenTelemetry GenAI semantic conventions
    attributes = {
        "gen_ai.conversation.id": conversation_id,  # Critical for Foundry trace correlation
        "gen_ai.provider.name": "microsoft.agent_framework",
        "session.id": conversation_id,
    }
    
    if agent_name:
        attributes["gen_ai.agent.name"] = agent_name
    if agent_id:
        attributes["gen_ai.agent.id"] = agent_id
    if model:
        attributes["gen_ai.request.model"] = model
    
    # Merge extra attributes
    attributes.update(extra_attributes)
    
    return tracer.start_as_current_span(
        name,
        kind=SpanKind.INTERNAL,
        attributes=attributes
    )


# Backward compatibility - simple tracing manager stub
class _TracingManager:
    """Simple tracing manager for backward compatibility."""
    
    def __init__(self):
        self.is_configured = True
        self._tracer = None
    
    @property
    def tracer(self):
        if self._tracer is None:
            self._tracer = get_tracer("function-tracing")
        return self._tracer
    
    def trace_function_call(self, function_name: str, **kwargs):
        """Create a span for a function call."""
        return self.tracer.start_as_current_span(function_name, attributes=kwargs)


_tracing_manager = None

def get_tracing_manager():
    """Get the global tracing manager instance."""
    global _tracing_manager
    if _tracing_manager is None:
        _tracing_manager = _TracingManager()
    return _tracing_manager
