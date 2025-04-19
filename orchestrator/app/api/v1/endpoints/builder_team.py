"""
Builder Team API endpoints.

This module contains endpoints for interacting with the builder team agents.
"""

import logging
import uuid
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from orchestrator.app.schemas.builder_team import (
    BuilderTeamRequest, 
    BuilderTeamResponse,
    DetailedTeamResponse
)
from agents.builder_team.agent_manager import BuilderTeamAgentManager

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Store for ongoing tasks
task_store = {}


@router.post("/process", response_model=BuilderTeamResponse)
async def process_task(request: BuilderTeamRequest) -> BuilderTeamResponse:
    """
    Process a task with the builder team.
    
    This endpoint uses the BuilderTeamAgentManager to synchronously process a task.
    
    Args:
        request: The task request with instructions
        
    Returns:
        The processed result from the builder team
    """
    try:
        logger.info(f"Processing task: {request.task}")
        
        # Create team manager with optional team_id
        manager = BuilderTeamAgentManager(
            team_id=request.team_id,
            **request.options if request.options else {}
        )
        
        # Run the task
        result = manager.run(request.task)
        
        return BuilderTeamResponse(
            result=result,
            team_id=manager.team_id,
            metadata={
                "task": request.task,
                "options": request.options
            }
        )
    except Exception as e:
        logger.error(f"Error processing task: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing task: {str(e)}"
        )


@router.post("/async", response_model=BuilderTeamResponse)
async def process_task_async(
    request: BuilderTeamRequest, 
    background_tasks: BackgroundTasks
) -> BuilderTeamResponse:
    """
    Asynchronously process a task with the builder team.
    
    This endpoint starts the task processing in the background and returns immediately.
    
    Args:
        request: The task request with instructions
        background_tasks: FastAPI background tasks
        
    Returns:
        Initial response with task_id
    """
    # Generate a task ID
    task_id = str(uuid.uuid4())
    
    # Create team manager
    manager = BuilderTeamAgentManager(
        team_id=request.team_id or f"team-{task_id}",
        **request.options if request.options else {}
    )
    
    # Store task info
    task_store[task_id] = {
        "task": request.task,
        "status": "pending",
        "team_id": manager.team_id,
        "result": None
    }
    
    # Add task to background tasks
    background_tasks.add_task(
        _run_task_in_background,
        task_id=task_id,
        manager=manager,
        task=request.task
    )
    
    return BuilderTeamResponse(
        result=f"Task '{request.task}' has been queued for processing",
        team_id=manager.team_id,
        metadata={
            "task_id": task_id,
            "status": "pending"
        }
    )


@router.get("/status/{task_id}", response_model=BuilderTeamResponse)
async def get_task_status(task_id: str) -> BuilderTeamResponse:
    """
    Get the status of a builder team task.
    
    Args:
        task_id: The ID of the task
        
    Returns:
        Task status information
    """
    # Check if task exists
    if task_id not in task_store:
        raise HTTPException(
            status_code=404,
            detail=f"Task '{task_id}' not found"
        )
    
    task_info = task_store[task_id]
    
    return BuilderTeamResponse(
        result=task_info.get("result", "Task is still processing"),
        team_id=task_info["team_id"],
        metadata={
            "task": task_info["task"],
            "status": task_info["status"],
            "task_id": task_id
        }
    )


# Helper function for background processing
async def _run_task_in_background(task_id: str, manager: BuilderTeamAgentManager, task: str):
    """
    Run a task in the background.
    
    Args:
        task_id: The ID of the task
        manager: The BuilderTeamAgentManager instance
        task: The task description
    """
    try:
        # Update status
        task_store[task_id]["status"] = "running"
        
        # Run the task
        result = manager.run(task)
        
        # Store result
        task_store[task_id]["result"] = result
        task_store[task_id]["status"] = "completed"
    except Exception as e:
        logger.error(f"Error in background task {task_id}: {str(e)}")
        task_store[task_id]["status"] = "failed"
        task_store[task_id]["result"] = f"Error: {str(e)}"
