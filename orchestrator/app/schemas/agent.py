"""
Schema models for agent-related API endpoints.

These models define the request and response structures for agent operations.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator


class ToolConfig(BaseModel):
    """
    Configuration for an agent tool.
    """
    id: str = Field(..., description="Unique identifier for the tool")
    name: str = Field(..., description="Display name of the tool")
    description: str = Field(..., description="Description of what the tool does")
    parameters: Dict[str, Any] = Field(..., description="Parameters for the tool")
    enabled: bool = Field(True, description="Whether the tool is enabled")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "web_search",
                "name": "Web Search",
                "description": "Search the web for information",
                "parameters": {
                    "query": {
                        "type": "string", 
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer", 
                        "description": "Maximum number of results",
                        "default": 5
                    }
                },
                "enabled": True
            }
        }


class MemoryBackendConfig(BaseModel):
    """
    Configuration for a memory backend.
    """
    id: str = Field(..., description="Unique identifier for the memory backend")
    name: str = Field(..., description="Display name for the memory backend")
    type: str = Field(..., description="Type of memory backend (redis, firestore, vectorstore)")
    config: Dict[str, Any] = Field(..., description="Configuration parameters for the memory backend")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "redis_memory",
                "name": "Redis Memory",
                "type": "redis",
                "config": {
                    "redis_url": "redis://localhost:6379",
                    "ttl": 3600
                }
            }
        }


class AgentConfig(BaseModel):
    """
    Configuration for an agent.
    """
    id: Optional[str] = Field(None, description="Unique identifier for the agent (generated if not provided)")
    name: str = Field(..., description="Display name of the agent")
    description: Optional[str] = Field("", description="Description of the agent's purpose and capabilities")
    persona: str = Field(..., description="Personality and behavior instructions for the agent")
    tools: List[str] = Field([], description="List of tool IDs that the agent can use")
    memory_backend: str = Field(..., description="Memory backend ID for the agent to use")
    created_at: Optional[datetime] = Field(None, description="When the agent was created")
    updated_at: Optional[datetime] = Field(None, description="When the agent was last updated")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Customer Support Agent",
                "description": "Helps customers with product inquiries and troubleshooting",
                "persona": "You are a friendly and knowledgeable customer support agent. Always be polite and helpful.",
                "tools": ["knowledge_base", "ticket_system"],
                "memory_backend": "redis_memory"
            }
        }


class AgentDeployRequest(BaseModel):
    """
    Request to deploy an agent to a runtime environment.
    """
    agent_id: str = Field(..., description="ID of the agent to deploy")
    environment: str = Field("development", description="Target environment (development, staging, production)")
    replicas: int = Field(1, description="Number of agent instances to deploy")
    
    @validator('replicas')
    @classmethod
    def validate_replicas(cls, v):
        if v < 1:
            raise ValueError('replicas must be at least 1')
        if v > 10:
            raise ValueError('replicas cannot exceed 10')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "agent_id": "agent-123",
                "environment": "development",
                "replicas": 1
            }
        }


class AgentSummary(BaseModel):
    """
    Summary information about an agent (for listings).
    """
    id: str = Field(..., description="Unique identifier for the agent")
    name: str = Field(..., description="Display name of the agent")
    description: str = Field("", description="Brief description of the agent")
    tools_count: int = Field(0, description="Number of tools the agent can use")
    created_at: datetime = Field(..., description="When the agent was created")
    updated_at: Optional[datetime] = Field(None, description="When the agent was last updated")
    status: str = Field("inactive", description="Current status of the agent (active, inactive, error)")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "agent-123",
                "name": "Customer Support Agent",
                "description": "Helps customers with product inquiries",
                "tools_count": 2,
                "created_at": "2025-01-15T12:30:45Z",
                "updated_at": "2025-01-16T09:15:22Z",
                "status": "active"
            }
        }


class AgentListResponse(BaseModel):
    """
    Response model for listing agents.
    """
    agents: List[AgentSummary] = Field(..., description="List of agent summaries")
    count: int = Field(..., description="Total number of agents")
