"""
Asynchronous processing endpoints using Temporal workflows.

This module contains API endpoints that use Temporal workflows to process
requests asynchronously, returning workflow IDs that can be used to track progress.
"""

import logging
from uuid import uuid4
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from temporalio.client import Client, WorkflowExecutionStatus
# WorkflowNotFoundError doesn't exist in temporalio 1.10.0
# Using appropriate exception handling instead
from temporalio.exceptions import ApplicationError

from app.core.config import settings
from app.services.api.process_service import ProcessService, default_process_service
# Import workflows with relative paths to match the project structure
from workflows.sample import SampleWorkflow
from workflows.planner_tool_responder import PlannerToolResponderWorkflow
from workflows.enhanced_workflow import EnhancedProcessingWorkflow

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()


class AsyncProcessRequest(BaseModel):
    """Request model for async processing."""
    # Support the same fields as the synchronous endpoint
    messages: Optional[list] = Field(None, description="List of message objects with role and content")
    system: Optional[str] = Field(None, description="System prompt")
    user: Optional[str] = Field(None, description="User prompt")
    model: Optional[str] = Field(None, description="Model to use for processing")
    provider: Optional[str] = Field(None, description="LLM provider to use")
    
    # Async-specific fields
    workflow_id: Optional[str] = Field(None, description="Custom workflow ID. If not provided, one will be generated.")
    workflow_type: str = Field("planner-tool-responder", description="Type of workflow to use. Options: planner-tool-responder, sample, enhanced")
    
    class Config:
        schema_extra = {
            "example": {
                "user": "Research benefits of containerization.",
                "system": "You are a helpful assistant that provides thorough research.",
                "workflow_type": "planner-tool-responder"
            }
        }
    
    @validator('workflow_type')
    @classmethod
    def validate_workflow_type(cls, v):
        valid_types = ['planner-tool-responder', 'sample', 'enhanced']
        if v not in valid_types:
            raise ValueError(f"Invalid workflow type. Must be one of: {', '.join(valid_types)}")
        return v
    
    # Additional fields for enhanced workflow
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID to continue")
    user_id: Optional[str] = Field(None, description="User ID associated with the request")
    retrieve_history: bool = Field(False, description="Whether to retrieve conversation history after processing")
    
    def get_input_for_workflow(self) -> Dict[str, Any]:
        """Convert to format expected by workflows."""
        data = self.dict(exclude={'workflow_id', 'workflow_type'}, exclude_none=True)
        
        # For the sample workflow that expects a string, convert to string if needed
        if self.workflow_type == 'sample' and 'user' in data:
            return data.get('user', '')
        
        # For enhanced workflow, format the input properly
        if self.workflow_type == 'enhanced':
            # Extract enhanced workflow specific fields
            enhanced_input = {
                "input_data": data.get('user', ''),
                "conversation_id": self.conversation_id,
                "user_id": self.user_id,
                "retrieve_history": self.retrieve_history
            }
            return enhanced_input
            
        return data


class AsyncProcessResponse(BaseModel):
    """Response model for async processing."""
    workflow_id: str = Field(..., description="Identifier for the workflow execution")
    run_id: str = Field(..., description="Run ID for the workflow execution")
    workflow_type: str = Field(..., description="Type of workflow that was started")
    status: str = Field("STARTED", description="Initial status of the workflow")


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""
    workflow_id: str = Field(..., description="Identifier for the workflow execution")
    workflow_type: Optional[str] = Field(None, description="Type of workflow")
    status: str = Field(..., description="Current status of the workflow")
    result: Optional[Dict[str, Any]] = Field(None, description="Result data if workflow has completed")


async def get_temporal_client() -> Client:
    """
    Create and return a Temporal client.
    
    This is a dependency that will be injected into route handlers.
    
    Returns:
        A Temporal client connected to the configured server
    """
    try:
        client = await Client.connect(
            settings.TEMPORAL_HOST_URL,
            namespace=settings.TEMPORAL_NAMESPACE
        )
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Temporal: {e}")
        raise HTTPException(
            status_code=503,
            detail="Workflow service unavailable"
        )


@router.post("/process", response_model=AsyncProcessResponse)
async def process_async(
    request: AsyncProcessRequest,
    client: Client = Depends(get_temporal_client),
    service: ProcessService = Depends(lambda: default_process_service)
) -> AsyncProcessResponse:
    """
    Start an asynchronous workflow to process the request.
    
    This endpoint immediately returns workflow identification information
    that can be used to check the status or result later.
    
    Args:
        request: The processing request
        client: Temporal client (injected dependency)
        service: Process service (injected dependency)
        
    Returns:
        Workflow identification information
        
    Raises:
        HTTPException: If the workflow fails to start
    """
    try:
        # Generate a unique workflow ID if not provided
        workflow_id = request.workflow_id or f"workflow-{uuid4()}"
        
        # Get the data in the format expected by the workflow
        workflow_input = request.get_input_for_workflow()
        
        # Determine which workflow to use
        if request.workflow_type == 'planner-tool-responder':
            workflow_fn = PlannerToolResponderWorkflow.run
        elif request.workflow_type == 'enhanced':
            workflow_fn = EnhancedProcessingWorkflow.run
        else:  # 'sample' is the default fallback
            workflow_fn = SampleWorkflow.run
        
        # Start the workflow
        handle = await client.start_workflow(
            workflow_fn,
            workflow_input,
            id=workflow_id,
            task_queue=settings.TEMPORAL_TASK_QUEUE
        )
        
        logger.info(f"Started {request.workflow_type} workflow {handle.id} (run_id: {handle.run_id})")
        
        # Return workflow IDs for the client to track status
        return AsyncProcessResponse(
            workflow_id=handle.id,
            run_id=handle.run_id,
            workflow_type=request.workflow_type
        )
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start workflow: {str(e)}"
        )


@router.get("/workflow/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_result(
    workflow_id: str,
    client: Client = Depends(get_temporal_client)
) -> WorkflowStatusResponse:
    """
    Get the status and result of a workflow by ID.
    
    This endpoint checks the current status of a workflow and returns its
    result if it has completed.
    
    Args:
        workflow_id: The ID of the workflow to check
        client: Temporal client (injected dependency)
        
    Returns:
        The current status and possibly result of the workflow
        
    Raises:
        HTTPException: If the workflow is not found or the request fails
    """
    try:
        # Get the workflow handle
        handle = client.get_workflow_handle(workflow_id)
        
        # Check if the workflow is still running
        status = await handle.describe()
        status_name = status.status.name
        
        # Determine workflow type from ID (could also be stored in a database)
        workflow_type = None
        if workflow_id.startswith("workflow-"):
            if "planner" in workflow_id:
                workflow_type = "planner-tool-responder"
            elif "enhanced" in workflow_id:
                workflow_type = "enhanced"
            else:
                workflow_type = "sample"
        
        response = WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=status_name,
            workflow_type=workflow_type
        )
        
        # If workflow has completed, fetch the result
        if status.status == WorkflowExecutionStatus.COMPLETED:
            result = await handle.result()
            response.result = result
        
        return response
    except ApplicationError as e:
        # Check if it's a not found error based on the error message
        if "workflow not found" in str(e).lower() or "does not exist" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"Workflow with ID '{workflow_id}' not found"
            )
        # Otherwise re-raise as a general server error
        raise HTTPException(
            status_code=500,
            detail=f"Workflow application error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workflow: {str(e)}"
        )


@router.get("/workflows", response_model=List[WorkflowStatusResponse])
async def list_workflows(
    limit: int = 10,
    client: Client = Depends(get_temporal_client)
) -> List[WorkflowStatusResponse]:
    """
    List recent workflows.
    
    Args:
        limit: Maximum number of workflows to return
        client: Temporal client (injected dependency)
        
    Returns:
        List of workflow status information
    """
    try:
        # Get handles for recent workflows
        # Note: This is a simplified implementation. In production,
        # you would want to use more advanced filtering and pagination.
        workflows = []
        async for workflow in client.list_workflows(
            query="WorkflowType='PlannerToolResponderWorkflow' OR WorkflowType='SampleWorkflow' OR WorkflowType='EnhancedProcessingWorkflow'",
            page_size=limit
        ):
            workflow_id = workflow.id
            if workflow.workflow_type == "PlannerToolResponderWorkflow":
                workflow_type = "planner-tool-responder"
            elif workflow.workflow_type == "EnhancedProcessingWorkflow":
                workflow_type = "enhanced"
            else:
                workflow_type = "sample"
            
            workflows.append(WorkflowStatusResponse(
                workflow_id=workflow_id,
                status=workflow.status.name,
                workflow_type=workflow_type
            ))
            
            if len(workflows) >= limit:
                break
        
        return workflows
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list workflows: {str(e)}"
        )
