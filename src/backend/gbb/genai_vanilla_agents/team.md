# Team

The `Team` class represents a group of Askables working together to handle user inputs and tasks. It is capable of deciding which agent to invoke after each step by using their descriptions and their available tools (when `include_tools_descriptions` is set to `True`).

## Usage

```python

from genai_vanilla_agents.team import Team

team = Team(id="team1", description="Support team", members=[agent1, agent2], llm=llm)
```
