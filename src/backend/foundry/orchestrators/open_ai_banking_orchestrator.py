"""
Moneta Banking Orchestrator - Azure OpenAI In-Memory Implementation
Multi-agent orchestration using HandoffBuilder pattern for banking services.

This orchestrator coordinates three specialized agents:
1. CRM Agent - Client data and portfolio information
2. CIO Agent - Investment research and market analysis
3. Funds Agent - Funds and ETFs information
4. News Agent - Investment news for stock positions

The orchestration uses the Handoff pattern where a coordinator agent routes
user requests to appropriate specialist agents.

This implementation uses Azure OpenAI with in-memory agents (AzureOpenAIChatClient).
For Foundry-hosted agents, use FoundryBankingOrchestrator instead.
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
    WorkflowEvent,
    ExecutorCompletedEvent
)
from agent_framework._workflows._events import AgentRunEvent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity.aio import AzureCliCredential

# Import specialist agent functions from banking agents subfolder
from foundry.agents.banking.crm.crm_functions import crm_functions
from foundry.agents.banking.cio.cio_functions import cio_functions
from foundry.agents.banking.funds.funds_functions import funds_functions
from foundry.agents.banking.news.news_functions import news_functions

# Load environment
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)

# Setup tracing for App Insights
from tracing import setup_tracing, get_tracer, set_conversation_context, clear_conversation_context
setup_tracing()
_tracer = get_tracer("moneta-openai-banking-orchestrator")


# Agent definitions
AGENT_DEFINITIONS = {
    "bank-coordinator": {
        "name": "bank-coordinator",
        "instructions": (
            "You are the Moneta Banking Coordinator. Analyze customer requests and route them to the appropriate specialist:\n"
            "- bank-crm-agent: For client data, portfolio information, account details, customer inquiries. "
            "Use when the request mentions a specific client name or ID.\n"
            "- bank-cio-agent: For investment research, market analysis, CIO views, strategic investment recommendations.\n"
            "- bank-funds-agent: For information about funds, ETFs, fund performance, and investment products.\n"
            "- bank-news-agent: For fetching latest investment news for specific stock positions/tickers.\n"
            "\n"
            "When you receive a request, immediately call the matching handoff tool "
            "(handoff_to_bank-crm-agent, handoff_to_bank-cio-agent, handoff_to_bank-funds-agent, or handoff_to_bank-news-agent) without explaining."
        ),
        "description": "Moneta Banking Coordinator - routes requests to specialist agents"
    },
    "bank-crm-agent": {
        "name": "bank-crm-agent",
        "instructions": (
            "You are a CRM specialist. Help with client data and portfolio information. "
            "Use your CRM functions to retrieve accurate customer data. "
            "ONLY use the provided functions - don't guess or use general knowledge. "
            "If client ID or name is not provided, politely inform the user that you need this information."
        ),
        "description": "CRM Banking Agent - handles client data and portfolio information"
    },
    "bank-cio-agent": {
        "name": "bank-cio-agent",
        "instructions": (
            "You are a Chief Investment Office specialist. Provide investment research and strategic insights. "
            "Use the search function to find relevant CIO views and market analysis. "
            "Provide CONCISE and actionable investment recommendations."
        ),
        "description": "CIO Agent - provides investment research and market analysis"
    },
    "bank-funds-agent": {
        "name": "bank-funds-agent",
        "instructions": (
            "You are a Funds specialist. Provide information about investment funds and ETFs. "
            "Use the search function to find relevant fund information. "
            "Explain fund characteristics, performance, and suitability clearly and concisely."
        ),
        "description": "Funds Agent - provides funds and ETF information"
    },
    "bank-news-agent": {
        "name": "bank-news-agent",
        "instructions": (
            "You are a News specialist for Moneta Banking. "
            "You fetch and analyze the latest investment news for specific stock positions. "
            "Use the fetch_news function to retrieve news for stock ticker symbols. "
            "When presenting news, summarize the key headlines and their potential impact on the portfolio."
        ),
        "description": "News Agent - fetches investment news for portfolio positions"
    }
}


class OpenAIBankingOrchestrator:
    """
    Azure OpenAI Banking Orchestrator with in-memory agents.
    
    This orchestrator uses Microsoft Agent Framework with HandoffBuilder pattern
    for multi-agent coordination in banking services using Azure OpenAI.
    """
    
    def __init__(self):
        """
        Initialize the Azure OpenAI Banking Orchestrator.
        Uses Azure OpenAI mode with in-memory agents.
        """
        import logging
        self.logger = logging.getLogger(__name__)
        self.logger.debug("OpenAI Banking Orchestrator init")
        
        self._workflow = None
        self._initialized = False
        
        # Configuration from environment
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

    async def _ensure_initialized(self):
        """Lazily initialize the workflow and agents."""
        if self._initialized:
            return
        
        credential = AzureCliCredential()
        
        # Azure OpenAI mode - use in-memory agents
        if not self.openai_endpoint:
            raise ValueError(
                "AZURE_OPENAI_ENDPOINT is required for Azure OpenAI mode."
            )
        
        self.logger.info(f"Using Azure OpenAI endpoint for workflow: {self.openai_endpoint}")
        chat_client = AzureOpenAIChatClient(
            endpoint=self.openai_endpoint,
            deployment_name=self.openai_deployment_name,
            credential=credential
        )
        coordinator, crm_agent, cio_agent, funds_agent, news_agent = create_specialist_agents(chat_client)
        
        # Build the handoff workflow
        self._workflow = (
            HandoffBuilder(
                name="moneta_banking_handoff",
                participants=[coordinator, crm_agent, cio_agent, funds_agent, news_agent],
            )
            .with_start_agent(coordinator)
            .with_termination_condition(
                lambda conv: sum(1 for msg in conv if msg.role.value == "user") >= 10
            )
            .build()
        )
        
        self._initialized = True
        self.logger.info("✅ OpenAI Banking Orchestrator initialized (Azure OpenAI in-memory agents)")
    
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
                'content': 'I didn\'t receive a message. How can I help you?'
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
                "banking_conversation",
                kind=SpanKind.SERVER,
                attributes={
                    "gen_ai.conversation.id": session_id,
                    "gen_ai.operation.name": "invoke_agent",
                    "gen_ai.provider.name": "azure_openai",
                    "gen_ai.agent.name": "banking_coordinator",
                    "session.id": session_id,
                    "user.id": user_id,
                    "session.mode": "azure_openai",
                    "conversation.message_count": len(chat_messages)
                }
            ) as session_span:
                final_response = ""
                responding_agent = "bank-coordinator"
                
                async for event in self._workflow.run_stream(chat_messages):
                    if isinstance(event, RequestInfoEvent):
                        # Handle HandoffAgentUserRequest with agent_response
                        if hasattr(event.data, 'agent_response') and event.data.agent_response:
                            agent_response = event.data.agent_response
                            if hasattr(agent_response, 'text') and agent_response.text:
                                final_response = agent_response.text
                                responding_agent = event.source_executor_id or "bank-coordinator"
                    
                    elif isinstance(event, ExecutorCompletedEvent):
                        if event.data is not None:
                            if hasattr(event.data, 'text') and event.data.text:
                                final_response = event.data.text
                                responding_agent = event.executor_id or "bank-coordinator"
                
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


def create_specialist_agents(chat_client: AzureOpenAIChatClient) -> tuple[ChatAgent, ChatAgent, ChatAgent, ChatAgent, ChatAgent]:
    """
    Create the coordinator and specialist agents for the banking workflow.
    Uses Azure OpenAI mode with in-memory agents.
    
    Args:
        chat_client: The Azure OpenAI chat client
        
    Returns:
        Tuple of (coordinator, crm_agent, cio_agent, funds_agent, news_agent)
    """
    
    coordinator = chat_client.as_agent(
        instructions=AGENT_DEFINITIONS["bank-coordinator"]["instructions"],
        name="bank-coordinator"
    )
    
    crm_agent = chat_client.as_agent(
        instructions=AGENT_DEFINITIONS["bank-crm-agent"]["instructions"],
        name="bank-crm-agent",
        tools=crm_functions
    )
    
    cio_agent = chat_client.as_agent(
        instructions=AGENT_DEFINITIONS["bank-cio-agent"]["instructions"],
        name="bank-cio-agent",
        tools=cio_functions
    )
    
    funds_agent = chat_client.as_agent(
        instructions=AGENT_DEFINITIONS["bank-funds-agent"]["instructions"],
        name="bank-funds-agent",
        tools=funds_functions
    )
    
    news_agent = chat_client.as_agent(
        instructions=AGENT_DEFINITIONS["bank-news-agent"]["instructions"],
        name="bank-news-agent",
        tools=news_functions
    )
    
    print(f"✅ Created coordinator agent: {coordinator.name}")
    print(f"✅ Created CRM Banking agent: {crm_agent.name}")
    print(f"✅ Created CIO agent: {cio_agent.name}")
    print(f"✅ Created Funds agent: {funds_agent.name}")
    print(f"✅ Created News agent: {news_agent.name}")
    
    return coordinator, crm_agent, cio_agent, funds_agent, news_agent


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
    Main function to initialize and run the OpenAI Banking orchestrator.
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
        async with AzureCliCredential() as credential:
            chat_client = AzureOpenAIChatClient(
                endpoint=endpoint,
                deployment_name=deployment_name,
                credential=credential
            )
            
            coordinator, crm_agent, cio_agent, funds_agent, news_agent = create_specialist_agents(chat_client)
            
            await run_workflow(coordinator, crm_agent, cio_agent, funds_agent, news_agent)
    
    except Exception as e:
        print(f"❌ Failed to initialize orchestrator: {str(e)}")
        import traceback
        traceback.print_exc()


async def run_workflow(
    coordinator: ChatAgent,
    crm_agent: ChatAgent,
    cio_agent: ChatAgent,
    funds_agent: ChatAgent,
    news_agent: ChatAgent
):
    """
    Run the multi-agent workflow with the given agents.
    """
    import uuid
    from opentelemetry.trace import SpanKind
    
    session_id = str(uuid.uuid4())[:8]
    
    workflow = (
        HandoffBuilder(
            name="moneta_banking_handoff",
            participants=[coordinator, crm_agent, cio_agent, funds_agent, news_agent],
        )
        .with_start_agent(coordinator)
        .with_termination_condition(
            lambda conv: sum(1 for msg in conv if msg.role.value == "user") >= 10
        )
        .build()
    )
    
    print("\n" + "="*60)
    print("🏦 MONETA BANKING MULTI-AGENT ORCHESTRATOR")
    print("   Mode: Azure OpenAI (in-memory agents)")
    print(f"   Session ID: {session_id}")
    print("="*60)
    print("\n🎭 Orchestrator with Specialist Agents:")
    print("   • Coordinator - Routes your requests")
    print("   • CRM Banking Agent - Client data & portfolios")
    print("   • CIO Agent - Investment research & analysis")
    print("   • Funds Agent - Funds & ETFs information")
    print("   • News Agent - Investment news for positions")
    print("\nType 'exit' or 'quit' to end the conversation.")
    print("="*60 + "\n")
    
    turn_counter = 0
    
    with _tracer.start_as_current_span(
        "banking_session",
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
                print("\n👋 Thank you for using Moneta Banking Services!")
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
