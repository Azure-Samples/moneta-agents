from typing import Annotated, Callable
import json

from pydantic import BaseModel

from .conversation import Conversation, ConversationReadingStrategy
from .askable import Askable
from .llm import LLM

import logging
logger = logging.getLogger(__name__)

class PlannedTeam(Askable):
    """
    A team of Askable that executes a plan to solve the user inquiry by using the available agents.
    
    Unlike the Team class, the PlannedTeam class does not decide which agent to ask next based on the conversation context but instead follows a pre-defined plan, evaluated upfront.

    Args:
        llm (LLM): The language model to use for the decision-making process.
        description (str): The description of the team.
        id (str): The unique identifier of the team.
        members (list[Askable]): The agents that are part of the team.
        stop_callback (Callable[[list[dict]], bool]): The callback function to determine when to stop the conversation
        fork_conversation (bool): Whether to fork the conversation and avoid writing the messages to the main conversation.
        fork_strategy (ConversationReadingStrategy): The reading strategy to use to select the messages to report output back to the main conversation.
        include_tools_descriptions (bool): Whether to include the tools descriptions in the system prompt to help the orchestrator decide.
    """
    
    def __init__(self, llm: LLM, description: str, id: str, members: list[Askable], stop_callback: Callable[[list[dict]], bool] = None, 
                 fork_conversation: bool = False,
                 fork_strategy: ConversationReadingStrategy = None,
                 include_tools_descriptions: bool = False):
        super().__init__(id, description)
        self.agents = members
        self.plan = None
        self.stop_callback = stop_callback
        self.fork_conversation = fork_conversation
        self.fork_strategy = fork_strategy
        self.include_tools_descriptions = include_tools_descriptions
        
        self.current_agent = None
        self.agents_dict = {agent.id: agent for agent in members}
        
        self.llm = llm
        
        logger.debug("[PlannedTeam %s] initialized with agents: %s", self.id, self.agents_dict)

    def ask(self, conversation: Conversation, stream = False):
        """
        Ask the team to solve the user inquiry by executing the pre-defined plan.
        
        This method will execute the plan by asking each agent in the plan in order. If the stop_callback is triggered, the execution will stop.
        
        Args:
            conversation (Conversation): The conversation to use for the execution. If fork_conversation is set to True, a forked conversation will be used and the messages will be written to the main conversation only at the end (depending on the fork_strategy).
            stream (bool): Whether to stream the conversation updates.
        """
        
        if self.plan is None:
            self.plan = self._create_plan(conversation)
            logger.debug("[PlannedTeam %s] created plan: %s", self.id, self.plan)
        
        execution_result = None
        local_conversation = conversation.fork() if self.fork_conversation else conversation
        
        if stream:
            conversation.update(["start", self.id])
        for step in self.plan:
            self.current_agent = self.agents_dict[step.agent_id]
            logger.debug("[PlannedTeam %s] current agent: %s", self.id, self.current_agent.id)
            
            # TODO check behavior
            local_conversation.messages.append({"role": "assistant", "name": self.id, "content": step.instructions})
            
            agent_result = self.current_agent.ask(local_conversation, stream=stream)
            logger.debug("[PlannedTeam %s] asked current agent with messages: %s", self.id, agent_result)
            
            if agent_result == "stop":
                logger.debug("[PlannedTeam %s] stop signal received, ending workflow.", self.id)
                conversation.log.append(("info", "plannedteam/stop", self.id))
                execution_result = "agent-stop"
                break
            elif agent_result == "error":
                logger.error("[PlannedTeam %s] error signal received, ending workflow.", self.id)
                conversation.log.append(("error", "plannedteam/error", self.id))
                execution_result = "agent-error"
                break
            
            if self.stop_callback is not None and self.stop_callback(local_conversation.messages):
                logger.debug("[PlannedTeam %s] stop callback triggered, ending workflow.", self.id)
                conversation.log.append(("info", "plannedteam/callback-stop", self.id))
                execution_result = "callback-stop"
                break
                
        if stream:
            local_conversation.update(["end", self.id])
            
        if self.fork_conversation:
            conversation.messages.extend(self.fork_strategy.get_messages(local_conversation))
            
        return execution_result

    def _create_plan(self, conversation: Conversation):
        system_prompt = """
You are a team orchestrator that must create a plan to solve the user inquiry by using the available agents.
Your task is to create a plan that includes only the agents suitable to help, based on their descriptions.
The plan must be a list of agent_id values, in the order they should be executed, along with the proper instructions for each agent.
The plan must be returned as JSON, with the following structure:

{{
    "plan": [
        {{
            "agent_id": "agent_id",
            "instructions": "instructions"
        }},
        ...
    ]
}}

You MUST return the plan in the format specified above. DO NOT return anything else.

# AVAILABLE AGENTS

{agents}

# INQUIRY

{inquiry}

BE SURE TO READ AGAIN THE INSTUCTIONS ABOVE BEFORE PROCEEDING.
"""
        local_messages = []
        agents_info = self._generate_agents_info()
        inquiry = conversation.messages[-1]["content"] # TODO pick the first user message
        
        local_messages.append({"role": "system", "content": system_prompt.format(agents=agents_info, inquiry=inquiry)})
        local_messages.append({"role": "user", "content": "Define the plan based on the provided agents and the inquiry."})
        
        # logger.debug("[Team %s] messages for selecting next agent: %s", self.id, local_messages)
        
        result, usage = self.llm.ask(messages=local_messages, response_format=TeamPlan)
        logger.debug("[PlannedTeam %s] result from Azure OpenAI: %s", self.id, result)
        
        if usage is not None:
            # Update conversation metrics with response usage
            conversation.metrics.total_tokens += usage["total_tokens"]
            conversation.metrics.prompt_tokens += usage["prompt_tokens"]
            conversation.metrics.completion_tokens += usage["completion_tokens"]
        
        output = TeamPlan.model_validate(result.parsed)
        return output.plan
    
    def _generate_agents_info(self):
        agents_info = []
        for agent in self.agents:
            tools = []
            if self.include_tools_descriptions and hasattr(agent, 'tools'):
                for tool in agent.tools:
                    tool_name = tool['function']['name']
                    tool_description = tool['function']['description']
                    tools.append(f"    - tool '{tool_name}': {tool_description}")
            tools_str = "\n".join(tools)
            
            agent_info = f"- agent_id: {agent.id}\n    - description: {agent.description}\n{tools_str}\n\n"
            agents_info.append(agent_info)
        
        return "\n".join(agents_info)
    
class TeamPlanStep(BaseModel):
    agent_id: Annotated[str, "The agent_id of the agent to execute"]
    instructions: Annotated[str, "The instructions for the agent"]
class TeamPlan(BaseModel):
    plan: Annotated[list[TeamPlanStep], "The plan to be executed by the team"]