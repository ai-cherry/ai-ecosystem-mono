from pydantic import BaseModel
from typing import Any, Dict

class AgentRequest(BaseModel):
    agent_id: str
    payload: Dict[str, Any]

class AgentResponse(BaseModel):
    status: str
    data: Dict[str, Any]
