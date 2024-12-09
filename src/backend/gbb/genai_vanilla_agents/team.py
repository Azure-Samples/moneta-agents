from typing import Annotated, Callable

from pydantic import BaseModel

from .conversation import AllMessagesStrategy, Conversation, ConversationReadingStrategy

from .agent import Agent
from .askable import Askable
from .llm import LLM

import logging
logger = logging.getLogger(__name__)

class Team(Askable):
    """
    A team of Askable that decides which agent to ask next based on the conversation context and available agents information.
    
    Args:
        llm (LLM): The language model to use for the decision-making process.
        description (str): The description of the team.
        id (str): The unique identifier of the team.
        members (list[Askable]): The agents that are part of the team.
        system_prompt (str): The system prompt to show to the orchestrator.
        stop_callback (Callable[[list[dict]], bool]): The callback function to determine when to stop the conversation
        allowed_transitions (dict[Agent, list[Agent]]): The allowed transitions between agents.
        include_tools_descriptions (bool): Whether to include the tools descriptions in the system prompt to help the orchestrator decide.
        reading_strategy (ConversationReadingStrategy): The reading strategy to use to select the messages to use for the decision-making process.
        use_structured_output (bool): Whether to use JSON structured output for the decision-making process. Set to False to use an older LLM API version.
    """
    
    def __init__(self, llm: LLM, description: str, id: str, 
                 members: list[Askable], 
                 system_prompt: str = "", 
                 stop_callback: Callable[[list[dict]], bool] = None, 
                 allowed_transitions: dict[Agent, list[Agent]] = None,
                 include_tools_descriptions: bool = False,
                 reading_strategy: ConversationReadingStrategy = AllMessagesStrategy(),
                 use_structured_output: bool = True):
        super().__init__(id, description)
        self.agents = members
        self.system_prompt = system_prompt
        self.stop_callback = stop_callback
        self.include_tools_descriptions = include_tools_descriptions
        self.allowed_transitions = allowed_transitions
        self.allowed_transitions_str_dict = {tr.id: [agent.id for agent in members] for tr in self.allowed_transitions for agent in self.allowed_transitions[tr]} if self.allowed_transitions else None
        self.use_structured_output = use_structured_output
        
        self.current_agent = None
        self.agents_dict = {agent.id: agent for agent in members}
        
        self.llm = llm
        self.reading_strategy = reading_strategy
        
        logger.debug("[Team %s] initialized with agents: %s", self.id, self.agents_dict)

    def ask(self, conversation: Conversation, stream = False):
        """
        Ask the team to solve the user inquiry by selecting the next agent to ask based on the conversation context and available agents information.
        
        This method will ask each agent in the team in order based on the conversation context and the available agents information. If the stop_callback is triggered, the execution will stop."""
        
        if stream:
            conversation.update(["start", self.id])
            
        execution_result = None
        while True:
            next_agent_id = self._select_next_agent(conversation)
            logger.debug("[Team %s] selected next agent ID: %s", self.id, next_agent_id)
            
            self.current_agent = self.agents_dict[next_agent_id]
            logger.debug("[Team %s] current agent: '%s'", self.id, self.current_agent.id)
            
            agent_result = self.current_agent.ask(conversation, stream=stream)
                
            logger.debug("[Team %s] asked current agent with messages: %s", self.id, agent_result)
            
            if agent_result == "stop":
                logger.debug("[Team %s] stop signal received, ending workflow.", self.id)
                conversation.log.append(("info", "team/stop", self.id))
                execution_result = "agent-stop"
                break
            elif agent_result == "error":
                logger.error("[Team %s] error signal received, ending workflow.", self.id)
                conversation.log.append(("error", "team/error", self.id))
                execution_result = "agent-error"
                break
            
            if self.stop_callback(conversation.messages):
                logger.debug("[Team %s] stop callback triggered, ending workflow.", self.id)
                conversation.log.append(("info", "team/callback-stop", self.id))
                execution_result = "callback-stop"
                break
                
        if stream:
            conversation.update(["end", self.id])
            
        return execution_result

    def _select_next_agent(self, conversation: Conversation):
        system_prompt = """
You are a team orchestrator that uses a chat history to determine the next best speaker in the conversation. 
Your task is to return the agent_id of the speaker that is best suited to proceed based on the context provided in the chat history and the description of the agents.
You MUST return agent_id value from the list of available agents.
The names are case-sensitive and should not be abbreviated or changed.
When a user input is expected, you MUST select an agent capable of handling the user input.
When provided, you can also take a decision based on tools available to each agent
When provided, you can also take a decision based on the allowed transitions between agents.

# AVAILABLE AGENTS

{agents}

# CHAT HISTORY

{history}

BE SURE TO READ AGAIN THE INSTUCTIONS ABOVE BEFORE PROCEEDING.
"""
        local_messages = []
        agents_info = self.generate_agents_info()
        history = self.construct_message_history(conversation)
        
        local_messages.append({"role": "system", "content": system_prompt.format(agents=agents_info, history=history)})
        local_messages.append({"role": "user", "content": "Read the conversation and provide the agent_id of the next speaker."})
        
        if self.use_structured_output:
            result, usage = self.llm.ask(messages=local_messages, temperature=0, response_format=AgentChoiceResponse)
            logger.debug("[Team %s] selected agent_id: %s, (reason: '%s')", self.id, result.parsed.agent_id, result.parsed.reason)
            conversation.log.append(("info", "team/choice", self.id, result.parsed.agent_id, result.parsed.reason))
            next_agent_id = result.parsed.agent_id
        else:
            result, usage = self.llm.ask(messages=local_messages, temperature=0)
            next_agent_id = result.content.split(" ")[-1].strip()
            logger.debug("[Team %s] selected agent_id: %s", self.id, next_agent_id)
            conversation.log.append(("info", "team/choice", self.id, next_agent_id))
        
        if usage is not None:
            # Update conversation metrics with response usage
            conversation.metrics.total_tokens += usage["total_tokens"]
            conversation.metrics.prompt_tokens += usage["prompt_tokens"]
            conversation.metrics.completion_tokens += usage["completion_tokens"]
        
        
        if next_agent_id not in self.agents_dict:
            logger.error("[Team %s] invalid agent_id selected: %s", self.id, next_agent_id)
            conversation.log.append(("error", "team/choice", self.id, next_agent_id))
            return self._select_next_agent(conversation)
        
        if self.allowed_transitions_str_dict is not None and self.current_agent is not None:
            if next_agent_id not in self.allowed_transitions_str_dict[self.current_agent.id]:
                logger.error("[Team %s] invalid agent_id selected: %s", self.id, next_agent_id)
                conversation.log.append(("error", "team/choice", self.id, next_agent_id))
                return self._select_next_agent(conversation)
        
        return next_agent_id

    def construct_message_history(self, conversation):
        selected_messages = self.reading_strategy.get_messages(conversation)
        history = "\n".join([f"{message['role']}: {message['content']}" for message in selected_messages])
        return history

    def generate_agents_info(self):
        agents_info = []
        for agent in self.agents:
            tools = []
            if self.include_tools_descriptions and hasattr(agent, 'tools'):
                for tool in agent.tools:
                    tool_name = tool['function']['name']
                    tool_description = tool['function']['description']
                    tools.append(f"    - tool '{tool_name}': {tool_description}")
            tools_str = "\n".join(tools)
            
            transitions = []
            if self.allowed_transitions and agent in self.allowed_transitions:
                transitions = [f"    - can transition to: {next_agent.id}" for next_agent in self.allowed_transitions[agent]]
            transitions_str = "\n".join(transitions)
            
            agent_info = f"- agent_id: {agent.id}\n    - description: {agent.description}\n{tools_str}\n{transitions_str}\n\n"
            agents_info.append(agent_info)
        
        return "\n".join(agents_info)

class AgentChoiceResponse(BaseModel):
    agent_id: Annotated[str, "Agent ID selected by the orchestrator. Must be a valid agent_id from the list of available agents."]
    reason: Annotated[str, "Reasoning behind the agent_id selection."]