import re
import threading
from typing import Optional

from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.context import Context


class FoundryAttributePropagator(SpanProcessor):
    """
    Span processor that propagates Foundry-required attributes from parent to child spans.
    
    This ensures that gen_ai.conversation.id and other critical attributes are present
    on all child spans, which is required for Foundry UI to properly display agent traces
    at the agent level.
    
    OpenTelemetry GenAI Semantic Conventions require these attributes on invoke_agent spans:
    - gen_ai.conversation.id: Session/thread ID for correlation (CRITICAL for Foundry)
    - gen_ai.agent.id: Unique identifier of the agent
    - gen_ai.agent.name: Human-readable agent name
    - gen_ai.operation.name: Should be 'invoke_agent' for agent calls
    - gen_ai.provider.name: e.g., 'microsoft.agent_framework'
    - gen_ai.request.model: Model deployment name
    
    See: https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/
    """
    
    # Attributes that should be propagated from parent to child spans
    PROPAGATE_ATTRIBUTES = [
        "gen_ai.conversation.id",  # Critical for Foundry trace correlation
        "session.id",              # Backup correlation ID
        "user.id",                 # User context
        "session.mode",            # Foundry vs Azure OpenAI mode
    ]
    
    # Attributes to add if missing (with attribute name as key)
    DEFAULT_ATTRIBUTES = {
        "gen_ai.provider.name": "microsoft.agent_framework",
    }
    
    def __init__(self):
        self._lock = threading.Lock()
        # Thread-local storage for parent span attributes
        self._parent_attributes = threading.local()
    
    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        """
        Called when a span starts. Propagate attributes from parent context.
        """
        # Check if this span should receive propagated attributes
        span_name = span.name or ""
        
        # Get attributes from parent context if available
        propagated_attrs = {}
        
        # Try to get parent span from context
        if parent_context:
            from opentelemetry.trace import get_current_span
            parent_span = get_current_span()
            if parent_span and hasattr(parent_span, 'attributes'):
                parent_attrs = getattr(parent_span, 'attributes', {}) or {}
                for attr in self.PROPAGATE_ATTRIBUTES:
                    if attr in parent_attrs:
                        propagated_attrs[attr] = parent_attrs[attr]
        
        # Also check thread-local storage for attributes set by parent spans
        if hasattr(self._parent_attributes, 'attrs'):
            for attr in self.PROPAGATE_ATTRIBUTES:
                if attr in self._parent_attributes.attrs and attr not in propagated_attrs:
                    propagated_attrs[attr] = self._parent_attributes.attrs[attr]
        
        # Apply propagated attributes to the span
        for attr, value in propagated_attrs.items():
            span.set_attribute(attr, value)
        
        # Add default attributes if missing
        for attr, default_value in self.DEFAULT_ATTRIBUTES.items():
            if not span.attributes or attr not in span.attributes:
                span.set_attribute(attr, default_value)
        
        # If this is a root span with gen_ai.conversation.id, store it for children
        if span.attributes:
            for attr in self.PROPAGATE_ATTRIBUTES:
                if attr in span.attributes:
                    if not hasattr(self._parent_attributes, 'attrs'):
                        self._parent_attributes.attrs = {}
                    self._parent_attributes.attrs[attr] = span.attributes[attr]
    
    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span ends."""
        pass  # No action needed on end
    
    def shutdown(self) -> None:
        """Shuts down the processor."""
        pass
    
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Forces flush of any buffered spans."""
        return True


class FilteringBatchSpanProcessor(BatchSpanProcessor):
    """
    BatchSpanProcessor that filters out noisy spans (CosmosDB, HTTP internals)
    while preserving Semantic Kernel and Agent Framework telemetry.
    """

    EXCLUDED_SPAN_NAMES = ['.*CosmosClient.*', '.*DatabaseProxy.*', '.*ContainerProxy.*']

    def on_end(self, span: ReadableSpan) -> None:
        # Filter out noisy spans
        for regex in self.EXCLUDED_SPAN_NAMES:
            if re.match(regex, span.name):
                return
            
        if span.attributes and span.attributes.get('component') == 'http':
            return
    
        super().on_end(span)


# Keep backward compatibility alias
CustomSpanProcessor = FilteringBatchSpanProcessor