from gbb.genai_vanilla_agents.user import User

user_proxy_agent = User(
    id="Customer",
    mode="unattended", 
    description = "An interface to a human participant. Call this agent to get inputs from the user and proceed with the workflow.")
