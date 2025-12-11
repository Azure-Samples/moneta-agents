"""
Moneta Insurance Orchestrator - Azure OpenAI In-Memory Implementation
Multi-agent orchestration using HandoffBuilder pattern for insurance services.

This orchestrator coordinates two specialized agents:
1. CRM Insurance Agent - Client insurance data and policy information
2. Policies Agent - Insurance policy research and product information

The orchestration uses the Handoff pattern where a coordinator agent routes
user requests to appropriate specialist agents.

This implementation uses Azure OpenAI with in-memory agents (AzureOpenAIChatClient).
For Foundry-hosted agents, use FoundryInsuranceOrchestrator instead.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional

# Microsoft Agent Framework imports
from agent_framework import (
    ChatAgent,
    ChatMessage,
    HandoffBuilder,
    RequestInfoEvent,
    WorkflowOutputEvent,
    WorkflowEvent
)
from agent_framework._workflows._events import AgentRunEvent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential

# Import specialist agent functions from insurance agents subfolder
from foundry.agents.insurance.crm.crm_insurance_functions import crm_insurance_functions
from foundry.agents.insurance.policies.policies_functions import policies_functions

# Load environment
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)

# Setup tracing for App Insights
from tracing import setup_tracing, get_tracer, set_conversation_context, clear_conversation_context
setup_tracing()
_tracer = get_tracer("moneta-openai-insurance-orchestrator")


# Agent definitions
AGENT_DEFINITIONS = {
    "ins-coordinator": {
        "name": "ins-coordinator",
        "instructions": (
            "You are the Moneta Insurance Coordinator. Analyze customer requests and route them to the appropriate specialist:\n"
            "- ins-crm-agent: For client insurance data, policy information, client details, coverage summaries. "
            "Use when the request mentions a specific client name or ID and is about their policies.\n"
            "- ins-policies-agent: For general insurance policy research, product information, coverage details, and policy recommendations.\n"
            "\n"
            "When you receive a request, immediately call the matching handoff tool "
            "(handoff_to_ins-crm-agent or handoff_to_ins-policies-agent) without explaining."
        ),
        "description": "Moneta Insurance Coordinator - routes requests to specialist agents"
    },
    "ins-crm-agent": {
        "name": "ins-crm-agent",
        "instructions": (
            "You are an Insurance CRM specialist. Help with client insurance data and policy information. "
            "Use your CRM functions to retrieve accurate customer policy data. "
            "ONLY use the provided functions - don't guess or use general knowledge. "
            "If client ID or name is not provided, politely inform the user that you need this information. "
            "Focus on policy details, coverage information, effective dates, and benefits."
        ),
        "description": "CRM Insurance Agent - handles client insurance data and policy information"
    },
    "ins-policies-agent": {
        "name": "ins-policies-agent",
        "instructions": (
            "You are an Insurance Policies specialist. Provide insurance policy information and product research insights. "
            "Use the search function to find relevant insurance policy information and product details. "
            "Provide CONCISE and actionable insurance insights focusing on coverage details, benefits, and recommendations."
        ),
        "description": "Policies Agent - provides insurance policy research and product information"
    }
}


class OpenAIInsuranceOrchestrator:
    """
    Azure OpenAI Insurance Orchestrator with in-memory agents.
    
    This orchestrator uses Microsoft Agent Framework with HandoffBuilder pattern
    for multi-agent coordination in insurance services using Azure OpenAI.
    """
    
    def __init__(self):
        """
        Initialize the Azure OpenAI Insurance Orchestrator.
        Uses Azure OpenAI mode with in-memory agents.
        """
        import logging
        self.logger = logging.getLogger(__name__)
        self.logger.debug("OpenAI Insurance Orchestrator init")
        
        self._workflow = None
        self._initialized = False
        
        # Configuration from environment
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.openai_key = os.getenv("AZURE_OPENAI_KEY")

    async def _ensure_initialized(self):
        """Lazily initialize the workflow and agents."""
        if self._initialized:
            return
        
        # Azure OpenAI mode - use in-memory agents
        if not self.openai_endpoint:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT is required for Azure OpenAI mode."
            )
        
        # Use API key if provided, otherwise fall back to Managed Identity
        if self.openai_key:
            self.logger.info(f"Using Azure OpenAI endpoint with API key: {self.openai_endpoint}")
            chat_client = AzureOpenAIChatClient(
                endpoint=self.openai_endpoint,
                deployment_name=self.openai_deployment_name,
                api_key=self.openai_key
            )
        else:
            self.logger.info(f"Using Azure OpenAI endpoint with Managed Identity: {self.openai_endpoint}")
            credential = DefaultAzureCredential()
            chat_client = AzureOpenAIChatClient(
                endpoint=self.openai_endpoint,
                deployment_name=self.openai_deployment_name,
                credential=credential
            )
        coordinator, crm_agent, policies_agent = create_specialist_agents(chat_client)
        
        # Build the handoff workflow with auto-registered handoff tools
        self._workflow = (
            HandoffBuilder(
                name="moneta_insurance_handoff",
                participants=[coordinator, crm_agent, policies_agent],
            )
            .set_coordinator(coordinator)
            .auto_register_handoff_tools(True)
            .with_termination_condition(
                lambda conv: sum(1 for msg in conv if msg.role.value == "user") >= 10
            )
            .build()
        )
        
        self._initialized = True
        self.logger.info("✅ OpenAI Insurance Orchestrator initialized (Azure OpenAI in-memory agents)")
    
    async def process_conversation(self, user_id: str, conversation_messages: list, session_id: str = None) -> dict:
        """
        Process a conversation and return the agent's reply.
        
        Args:
            user_id: The user identifier
            conversation_messages: List of message dicts with 'role', 'name', 'content' keys
            session_id: Session/chat ID for tracing (typically the chat_id)
            
        Returns:
            Dict with 'role', 'name', 'content' keys representing the agent's reply
        """
        await self._ensure_initialized()
        
        # Use session_id for tracing, generate one if not provided
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())[:8]
        
        self.logger.info(f"Processing conversation with session_id: {session_id}")
        
        # Convert conversation history to ChatMessage objects for the workflow
        chat_messages = []
        for msg in conversation_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            author_name = msg.get('name')
            
            if content:
                chat_msg = ChatMessage(
                    role=role,
                    text=content,
                    author_name=author_name
                )
                chat_messages.append(chat_msg)
        
        if not chat_messages:
            return {
                'role': 'assistant',
                'name': 'coordinator',
                'content': 'I didn\'t receive a message. How can I help you with insurance?'
            }
        
        self.logger.info(f"Injecting {len(chat_messages)} messages as conversation history")
        
        try:
            from opentelemetry.trace import SpanKind
            
            set_conversation_context(
                conversation_id=session_id,
                user_id=user_id,
                mode="azure_openai"
            )
            
            with _tracer.start_as_current_span(
                "insurance_conversation",
                kind=SpanKind.SERVER,
                attributes={
                    "gen_ai.conversation.id": session_id,
                    "gen_ai.operation.name": "invoke_agent",
                    "gen_ai.provider.name": "azure_openai",
                    "gen_ai.agent.name": "insurance_coordinator",
                    "session.id": session_id,
                    "user.id": user_id,
                    "session.mode": "azure_openai",
                    "conversation.message_count": len(chat_messages)
                }
            ) as session_span:
                final_response = ""
                responding_agent = "ins-coordinator"
                
                async for event in self._workflow.run_stream(chat_messages):
                    if isinstance(event, RequestInfoEvent):
                        self.logger.debug(f"RequestInfoEvent: source={event.source_executor_id}, data type={type(event.data).__name__}")
                        if hasattr(event.data, 'conversation') and event.data.conversation:
                            for msg in reversed(event.data.conversation):
                                if hasattr(msg, 'role') and msg.role.value == 'assistant':
                                    if hasattr(msg, 'text') and msg.text:
                                        final_response = msg.text
                                        responding_agent = getattr(msg, 'author_name', None) or getattr(event.data, 'awaiting_agent_id', 'coordinator')
                                        self.logger.info(f"Captured response from '{responding_agent}': {len(final_response)} chars")
                                        break
                    
                    elif isinstance(event, AgentRunEvent):
                        if event.data and event.data.text:
                            final_response = event.data.text
                            responding_agent = event.executor_id or "ins-coordinator"
                            self.logger.info(f"Captured from AgentRunEvent '{responding_agent}': {len(final_response)} chars")
                    
                    elif isinstance(event, WorkflowOutputEvent):
                        if hasattr(event, 'data'):
                            if hasattr(event.data, 'text') and event.data.text:
                                final_response = event.data.text
                                responding_agent = getattr(event, 'source_executor_id', 'coordinator')
                                self.logger.info(f"Captured from WorkflowOutputEvent: {len(final_response)} chars")
                
                self.logger.info(f"Final response: {len(final_response)} chars from '{responding_agent}'")
                
                session_span.set_attribute("response.agent", responding_agent)
                session_span.set_attribute("response.length", len(final_response))
                
                return {
                    'role': 'assistant',
                    'name': responding_agent,
                    'content': final_response or 'I apologize, but I was unable to generate a response.'
                }
            
        except Exception as e:
            self.logger.error(f"Error processing conversation: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'role': 'assistant',
                'name': 'coordinator',
                'content': f'I encountered an error while processing your request. Please try again.'
            }
        finally:
            clear_conversation_context()


def create_specialist_agents(chat_client: AzureOpenAIChatClient) -> tuple[ChatAgent, ChatAgent, ChatAgent]:
    """
    Create the coordinator and specialist agents for the insurance workflow.
    Uses Azure OpenAI mode with in-memory agents.
    
    Args:
        chat_client: The Azure OpenAI chat client
        
    Returns:
        Tuple of (coordinator, crm_agent, policies_agent)
    """
    
    coordinator = chat_client.create_agent(
        instructions=AGENT_DEFINITIONS["ins-coordinator"]["instructions"],
        name="ins-coordinator"
    )
    
    crm_agent = chat_client.create_agent(
        instructions=AGENT_DEFINITIONS["ins-crm-agent"]["instructions"],
        name="ins-crm-agent",
        tools=crm_insurance_functions
    )
    
    policies_agent = chat_client.create_agent(
        instructions=AGENT_DEFINITIONS["ins-policies-agent"]["instructions"],
        name="ins-policies-agent",
        tools=policies_functions
    )
    
    print(f"✅ Created coordinator agent: {coordinator.name}")
    print(f"✅ Created CRM Insurance agent: {crm_agent.name}")
    print(f"✅ Created Policies agent: {policies_agent.name}")
    
    return coordinator, crm_agent, policies_agent


async def handle_workflow_events(events: list[WorkflowEvent]) -> list[RequestInfoEvent]:
    """
    Process workflow events and return any pending input requests.
    
    Args:
        events: List of workflow events to process
        
    Returns:
        List of pending input requests
    """
    pending_requests = []
    
    for event in events:
        if isinstance(event, RequestInfoEvent):
            pending_requests.append(event)
            request_data = event.data
            awaiting_agent = request_data.awaiting_agent_id.upper()
            
            print(f"\n{'='*60}")
            print(f"AWAITING INPUT FROM: {awaiting_agent}")
            print(f"{'='*60}")
            
            for msg in request_data.conversation[-3:]:
                author = msg.author_name or msg.role.value
                print(f"    [{author}]: {msg.text}")
                
        elif isinstance(event, WorkflowOutputEvent):
            print("\n✅ Workflow completed!")
            
    return pending_requests


async def main():
    """
    Main function to initialize and run the OpenAI Insurance orchestrator.
    Uses Azure OpenAI mode with in-memory agents.
    """
    os.system('cls' if os.name=='nt' else 'clear')
    
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
    
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    print("🔌 Using Azure OpenAI mode (in-memory agents)")
    
    if not endpoint:
        print("❌ Error: AZURE_OPENAI_ENDPOINT is required")
        return
    
    try:
        credential = DefaultAzureCredential()
        chat_client = AzureOpenAIChatClient(
            endpoint=endpoint,
            deployment_name=deployment_name,
            credential=credential
        )
        
        coordinator, crm_agent, policies_agent = create_specialist_agents(chat_client)
        
        await run_workflow(coordinator, crm_agent, policies_agent)
    
    except Exception as e:
        print(f"❌ Failed to initialize orchestrator: {str(e)}")
        import traceback
        traceback.print_exc()


async def run_workflow(
    coordinator: ChatAgent,
    crm_agent: ChatAgent,
    policies_agent: ChatAgent
):
    """
    Run the multi-agent workflow with the given agents.
    """
    import uuid
    from opentelemetry.trace import SpanKind
    
    session_id = str(uuid.uuid4())[:8]
    
    workflow = (
        HandoffBuilder(
            name="moneta_insurance_handoff",
            participants=[coordinator, crm_agent, policies_agent],
        )
        .set_coordinator(coordinator)
        .auto_register_handoff_tools(True)
        .with_termination_condition(
            lambda conv: sum(1 for msg in conv if msg.role.value == "user") >= 10
        )
        .build()
    )
    
    print("\n" + "="*60)
    print("🛡️ MONETA INSURANCE MULTI-AGENT ORCHESTRATOR")
    print("   Mode: Azure OpenAI (in-memory agents)")
    print(f"   Session ID: {session_id}")
    print("="*60)
    print("\n🎭 Orchestrator with Specialist Agents:")
    print("   • Coordinator - Routes your requests")
    print("   • CRM Insurance Agent - Client insurance data & policies")
    print("   • Policies Agent - Insurance policy research & products")
    print("\nType 'exit' or 'quit' to end the conversation.")
    print("="*60 + "\n")
    
    turn_counter = 0
    
    with _tracer.start_as_current_span(
        "insurance_session",
        kind=SpanKind.SERVER,
        attributes={
            "gen_ai.conversation.id": session_id,
            "session.id": session_id,
            "session.mode": "azure_openai"
        }
    ) as session_span:
        
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ["exit", "quit", "q"]:
                session_span.set_attribute("session.total_turns", turn_counter)
                session_span.set_attribute("session.status", "completed")
                print("\n👋 Thank you for using Moneta Insurance Services!")
                break
            
            if not user_input:
                print("Please enter a valid query.")
                continue
            
            turn_counter += 1
            
            try:
                with _tracer.start_as_current_span(
                    f"conversation_turn_{turn_counter}",
                    kind=SpanKind.INTERNAL,
                    attributes={
                        "gen_ai.conversation.id": session_id,
                        "turn.number": turn_counter,
                        "turn.user_input": user_input[:500],
                        "session.id": session_id
                    }
                ) as turn_span:
                    handoffs = []
                    
                    events = [event async for event in workflow.run_stream(user_input)]
                    
                    for event in events:
                        if isinstance(event, RequestInfoEvent):
                            if hasattr(event, 'data') and hasattr(event.data, 'awaiting_agent_id'):
                                handoffs.append(event.data.awaiting_agent_id)
                    
                    pending_requests = await handle_workflow_events(events)
                    
                    if handoffs:
                        turn_span.set_attribute("turn.handoffs", ",".join(handoffs))
                        turn_span.set_attribute("turn.handoff_count", len(handoffs))
                
                while pending_requests:
                    user_response = input("\nYou: ").strip()
                    if not user_response:
                        break
                    
                    with _tracer.start_as_current_span(
                        f"followup_turn_{turn_counter}",
                        kind=SpanKind.INTERNAL,
                        attributes={
                            "gen_ai.conversation.id": session_id,
                            "turn.number": turn_counter,
                            "turn.is_followup": True,
                            "turn.user_input": user_response[:500],
                            "session.id": session_id
                        }
                    ):
                        responses = {req.request_id: user_response for req in pending_requests}
                        events = [event async for event in workflow.send_responses_streaming(responses)]
                        pending_requests = await handle_workflow_events(events)
                
                print()
                
            except Exception as e:
                print(f"❌ Error processing request: {str(e)}")
                session_span.set_attribute("session.has_errors", True)
                session_span.record_exception(e)
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
