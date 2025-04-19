"""
Schema models for workflow-related API endpoints.

These models define the request and response structures for workflow operations.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class WorkflowRequest(BaseModel):
    """
    Request model for starting a workflow.
    """
    data: str = Field(..., description="Text input to process")
    workflow_id: Optional[str] = Field(None, description="Custom workflow ID. If not provided, one will be generated.")
    
    class Config:
        schema_extra = {
            "example": {
                "data": "Analyze the sentiment of this review: 'I love this product!'",
                "workflow_id": "custom-workflow-123"
            }
        }


class EnhancedWorkflowRequest(BaseModel):
    """
    Request model for starting an enhanced workflow with additional options.
    """
    data: str = Field(..., description="Text input to process")
    workflow_id: Optional[str] = Field(None, description="Custom workflow ID. If not provided, one will be generated.")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID to continue")
    user_id: Optional[str] = Field(None, description="User ID associated with the request")
    retrieve_history: bool = Field(False, description="Whether to retrieve conversation history after processing")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional workflow-specific options")

    class Config:
        schema_extra = {
            "example": {
                "data": "Tell me more about that product.",
                "workflow_id": "custom-workflow-123",
                "conversation_id": "conv-456",
                "user_id": "user-789",
                "retrieve_history": True,
                "options": {
                    "temperature": 0.7,
                    "model": "gpt-4"
                }
            }
        }


class WorkflowResponse(BaseModel):
    """
    Response model for workflow creation.
    """
    workflow_id: str = Field(..., description="Identifier for the workflow execution")
    run_id: str = Field(..., description="Run ID for the workflow execution")


class WorkflowStatusResponse(BaseModel):
    """
    Response model for workflow status.
    """
    workflow_id: str = Field(..., description="Identifier for the workflow execution")
    status: str = Field(..., description="Current status of the workflow")
    result: Optional[Dict[str, Any]] = Field(None, description="Result data if workflow has completed")
    created_at: Optional[datetime] = Field(None, description="When the workflow was created")
    completed_at: Optional[datetime] = Field(None, description="When the workflow completed (if finished)")
    
    class Config:
        schema_extra = {
            "example": {
                "workflow_id": "workflow-123",
                "status": "COMPLETED",
                "result": {
                    "status": "completed",
                    "result": "The sentiment is positive.",
                    "confidence": 0.95
                },
                "created_at": "2025-01-15T12:30:45Z",
                "completed_at": "2025-01-15T12:30:50Z"
            }
        }


class WorkflowListResponse(BaseModel):
    """
    Response model for listing workflows.
    """
    workflows: List[WorkflowStatusResponse] = Field(..., description="List of workflow statuses")
    count: int = Field(..., description="Total number of workflows")
