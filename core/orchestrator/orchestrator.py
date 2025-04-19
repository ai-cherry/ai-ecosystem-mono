from fastapi import APIRouter
from models import AgentRequest, AgentResponse

router = APIRouter()

@router.post("/agent")
async def handle_agent_request(request: AgentRequest) -> AgentResponse:
    # Placeholder for LangChain and Temporal client logic
    return AgentResponse(status="success", data={"message": "Agent processed"})