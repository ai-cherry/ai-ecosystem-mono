class AgentRegistry:
    def __init__(self):
        self.registry = {}

    def register_agent(self, agent_id: str, agent_info: dict):
        self.registry[agent_id] = agent_info

    def get_agent(self, agent_id: str):
        return self.registry.get(agent_id)

    def list_agents(self):
        return self.registry.keys()
