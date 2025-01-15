# At the moment the Agent name is not captured in the traces by default
# It is on the roadmap, so this is the temporary workaround
# Once this released, - remove it: https://github.com/microsoft/semantic-kernel/issues/10174
import sys
from abc import ABC
from collections.abc import AsyncIterable
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.streaming_chat_message_content import ChatMessageContent

from opentelemetry.trace import get_tracer

if sys.version_info >= (3, 12):
    from typing import override  # pragma: no cover
else:
    from typing_extensions import override  # pragma: no cover

class CustomAgentBase(ChatCompletionAgent, ABC):
    @override
    async def invoke(self, history: ChatHistory) -> AsyncIterable[ChatMessageContent]:
        tracer = get_tracer(__name__)
        response_messages: list[ChatMessageContent] = []
        with tracer.start_as_current_span(self.name):
            # Cache the messages within the span such that subsequent spans
            # that process the message stream don't become children of this span
            async for response_message in super().invoke(history):
                response_messages.append(response_message)

        for response_message in response_messages:
            yield response_message