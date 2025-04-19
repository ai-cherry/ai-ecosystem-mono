from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from app.services.api.process_service import ProcessService, default_process_service

router = APIRouter()


class ProcessRequest(BaseModel):
    """Request model for processing."""
    messages: Optional[list] = Field(None, description="List of message objects with role and content")
    system: Optional[str] = Field(None, description="System prompt")
    user: Optional[str] = Field(None, description="User prompt")
    model: Optional[str] = Field(None, description="Model to use for processing")
    provider: Optional[str] = Field(None, description="LLM provider to use")
    
    class Config:
        schema_extra = {
            "example": {
                "user": "Tell me a joke about programming.",
                "system": "You are a helpful assistant with a sense of humor."
            }
        }


@router.post("/")
async def process_endpoint(
    request: ProcessRequest,
    service: ProcessService = Depends(lambda: default_process_service)
):
    """
    Process a request with the LLM service.
    
    Args:
        request: The processing request
        service: The process service (injected dependency)
        
    Returns:
        The LLM response
    """
    try:
        # Create custom service if model or provider specified
        if request.model or request.provider:
            service = ProcessService(
                llm_provider=request.provider or service.llm_provider,
                model_name=request.model
            )
        
        # Process the request
        result = await service.process_request(request.dict(exclude_none=True))
        
        return JSONResponse(content=result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Processing error: {str(e)}"
        )
