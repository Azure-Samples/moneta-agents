import re

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor

class CustomSpanProcessor(BatchSpanProcessor):
    """Filtering out spans with specific names and URLs to keep only Semantic Kernel telemetry"""

    EXCLUDED_SPAN_NAMES = ['.*CosmosClient.*', '.*DatabaseProxy.*', '.*ContainerProxy.*']

    def on_end(self, span: ReadableSpan) -> None:
       
        for regex in self.EXCLUDED_SPAN_NAMES:
            if re.match(regex, span.name):
                return
            
        if span.attributes.get('component') == 'http':
            return
    
        super().on_end(span)