"""
Schema models for builder team related endpoints.

These models define the request and response structures for the builder team API.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class BuilderTeamRequest(BaseModel):
    """
    Request model for builder team processing.
    """
    task: str = Field(..., description="The task to process with the builder team")
    team_id: Optional[str] = Field(None, description="Optional team ID for persistence")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional processing options")
    
    class Config:
        schema_extra = {
            "example": {
                "task": "Create a responsive landing page for our new product",
                "options": {
                    "memory_provider": "redis",
                    "llm_model": "gpt-4o"
                }
            }
        }


class BuilderTeamResponse(BaseModel):
    """
    Response model for builder team processing.
    """
    result: str = Field(..., description="The processed result from the builder team")
    team_id: str = Field(..., description="The ID of the team that processed the request")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the processing")
    
    class Config:
        schema_extra = {
            "example": {
                "result": "Here's a comprehensive plan for your landing page...",
                "team_id": "team-123456",
                "metadata": {
                    "processing_time": 3.5,
                    "roles_involved": ["architect", "developer", "designer"]
                }
            }
        }


class RoleResponse(BaseModel):
    """
    Response from a specific team role.
    """
    role: str = Field(..., description="The role that provided this response")
    content: str = Field(..., description="The response content")
    timestamp: str = Field(..., description="When this response was generated")
    
    class Config:
        schema_extra = {
            "example": {
                "role": "architect",
                "content": "For this landing page, I recommend a single-page design with the following sections...",
                "timestamp": "2025-04-19T13:15:45Z"
            }
        }


class DetailedTeamResponse(BaseModel):
    """
    Detailed response with individual role contributions.
    """
    result: str = Field(..., description="The final integrated result")
    team_id: str = Field(..., description="The ID of the team that processed the request")
    roles: List[RoleResponse] = Field(..., description="Responses from individual roles")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the processing")
