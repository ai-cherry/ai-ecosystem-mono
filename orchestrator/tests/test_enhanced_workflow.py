"""
Integration tests for the enhanced workflow implementation.

This module tests the end-to-end flow using the EnhancedProcessingWorkflow,
which integrates async API, Temporal, memory systems, and LLM services.
"""

import asyncio
import uuid
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from orchestrator.app.api.v1.endpoints.process_async import router, get_temporal_client
from orchestrator.workflows.enhanced_workflow import (
    EnhancedProcessingWorkflow,
    process_with_llm_and_memory,
    retrieve_conversation_history
)
from orchestrator.tests.test_integration import (
    MockTemporalClient,
    MockMemory,
    MockLLMService
)


# ----- Fixtures -----

@pytest.fixture
def mock_llm_service():
    """Fixture for mock LLM service."""
    return MagicMock(spec=MockLLMService)


@pytest.fixture
def mock_memory():
    """Fixture for mock memory implementation."""
    return MockMemory()


@pytest.fixture
async def temporal_client():
    """Fixture for mock Temporal client."""
    return MockTemporalClient()


@pytest.fixture
def app(temporal_client, mock_memory):
    """Fixture for test app with dependencies."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    
    # Override dependencies
    async def get_test_temporal_client():
        return temporal_client
    
    app.dependency_overrides[get_temporal_client] = get_test_temporal_client
    
    # Return the app instance
    return app


@pytest.fixture
def client(app):
    """Test client for the app."""
    return TestClient(app)


# ----- Helper Functions -----

async def setup_and_run_enhanced_workflow(
    client, 
    temporal_client, 
    mock_memory, 
    mock_llm_service,
    input_data="Test input data",
    should_fail=False,
    conversation_id=None
):
    """Helper function to set up and run an enhanced workflow test."""
    # Make a request to the async API
    response = client.post("/api/v1/process", json={
        "data": input_data
    })
    
    # Check the response
    assert response.status_code == 200
    result = response.json()
    assert "workflow_id" in result
    
    workflow_id = result["workflow_id"]
    
    # Set up mocks for the activity implementations
    if not conversation_id:
        conversation_id = f"conversation-{uuid.uuid4()}"
    
    # Configure the mock LLM service
    if should_fail:
        mock_llm_service.process.side_effect = Exception("LLM processing failed")
    else:
        mock_llm_service.process.return_value = {
            "result": f"Enhanced processed: {input_data}",
            "confidence": 0.95
        }
    
    # Patch the activity implementations
    with patch("orchestrator.workflows.enhanced_workflow.RedisMemory", return_value=mock_memory), \
         patch("orchestrator.workflows.enhanced_workflow.LLMService", return_value=mock_llm_service):
        
        # Create activity function mocks that forward to the actual implementations
        async def mock_process_activity(data, conv_id=None, user_id=None):
            if not conv_id:
                conv_id = conversation_id
            
            # Call the real implementation with our mocks injected
            return await process_with_llm_and_memory(data, conv_id, user_id)
        
        async def mock_retrieve_activity(conv_id, limit=None):
            # Call the real implementation with our mocks injected
            return await retrieve_conversation_history(conv_id, limit)
        
        # Simulate workflow execution
        try:
            # Process the data
            activity_result = await mock_process_activity(input_data, conversation_id)
            
            # If retrieve_history is needed
            history_result = None
            if not should_fail:
                history_result = await mock_retrieve_activity(conversation_id)
                if history_result["status"] == "success":
                    activity_result["history"] = history_result["messages"]
            
            # Mark the workflow as completed with the result
            temporal_client.complete_workflow(workflow_id, activity_result)
            
        except Exception as e:
            # Handle activity failure
            temporal_client.complete_workflow(workflow_id, {
                "status": "failed",
                "conversation_id": conversation_id,
                "error": str(e)
            })
    
    # Return workflow ID and conversation ID for further assertions
    return workflow_id, conversation_id


# ----- Tests -----

@pytest.mark.asyncio
async def test_enhanced_workflow_success(client, temporal_client, mock_memory, mock_llm_service):
    """Test the success path for the enhanced workflow."""
    # Run the workflow
    workflow_id, conversation_id = await setup_and_run_enhanced_workflow(
        client,
        temporal_client,
        mock_memory,
        mock_llm_service,
        input_data="Enhanced test input"
    )
    
    # Check workflow status
    status_response = client.get(f"/api/v1/workflow/{workflow_id}")
    assert status_response.status_code == 200
    status_result = status_response.json()
    
    # Validate workflow completed successfully
    assert status_result["status"] == "COMPLETED"
    assert status_result["result"]["status"] == "success"
    assert "result" in status_result["result"]
    assert "Enhanced processed: Enhanced test input" in status_result["result"]["result"]
    
    # Verify LLM service was called correctly
    mock_llm_service.process.assert_called_once_with("Enhanced test input")
    
    # Check memory persistence
    assert len(mock_memory.conversations[conversation_id]) == 2
    assert mock_memory.conversations[conversation_id][0]["content"] == "Enhanced test input"
    assert mock_memory.conversations[conversation_id][0]["role"] == "user"
    assert mock_memory.conversations[conversation_id][1]["role"] == "assistant"
    assert "Enhanced processed: Enhanced test input" in mock_memory.conversations[conversation_id][1]["content"]


@pytest.mark.asyncio
async def test_enhanced_workflow_with_existing_conversation(client, temporal_client, mock_memory, mock_llm_service):
    """Test the workflow with an existing conversation ID."""
    # Create a pre-existing conversation
    existing_conversation_id = f"existing-conversation-{uuid.uuid4()}"
    mock_memory.save_message(
        existing_conversation_id,
        {"role": "user", "content": "Previous message"}
    )
    mock_memory.save_message(
        existing_conversation_id,
        {"role": "assistant", "content": "Previous response"}
    )
    
    # Run the workflow with the existing conversation
    workflow_id, _ = await setup_and_run_enhanced_workflow(
        client,
        temporal_client,
        mock_memory,
        mock_llm_service,
        input_data="Follow-up message",
        conversation_id=existing_conversation_id
    )
    
    # Check workflow result
    status_response = client.get(f"/api/v1/workflow/{workflow_id}")
    status_result = status_response.json()
    
    assert status_result["status"] == "COMPLETED"
    assert status_result["result"]["conversation_id"] == existing_conversation_id
    
    # Verify conversation history
    conversation = mock_memory.get_conversation(existing_conversation_id)
    assert len(conversation) == 4  # Initial 2 + new user message + new assistant response
    assert conversation[0]["content"] == "Previous message"
    assert conversation[1]["content"] == "Previous response"
    assert conversation[2]["content"] == "Follow-up message"
    assert "Enhanced processed: Follow-up message" in conversation[3]["content"]


@pytest.mark.asyncio
async def test_enhanced_workflow_llm_failure(client, temporal_client, mock_memory, mock_llm_service):
    """Test the workflow with LLM processing failure."""
    # Run the workflow with LLM failure
    workflow_id, conversation_id = await setup_and_run_enhanced_workflow(
        client,
        temporal_client,
        mock_memory,
        mock_llm_service,
        input_data="Failure input",
        should_fail=True
    )
    
    # Check workflow result
    status_response = client.get(f"/api/v1/workflow/{workflow_id}")
    status_result = status_response.json()
    
    # Verify fallback mechanism worked
    assert status_result["status"] == "COMPLETED"
    assert status_result["result"]["status"] == "fallback"
    assert "error" in status_result["result"]
    assert "LLM processing failed" in status_result["result"]["error"]
    
    # Verify error was logged in memory
    conversation = mock_memory.get_conversation(conversation_id)
    assert len(conversation) == 3  # User message + error message + fallback response
    assert conversation[0]["role"] == "user"
    assert conversation[1]["role"] == "system"
    assert "Error processing" in conversation[1]["content"]
    assert conversation[2]["role"] == "assistant"
    assert "I'm sorry" in conversation[2]["content"]


@pytest.mark.asyncio
async def test_multi_turn_conversation(client, temporal_client, mock_memory, mock_llm_service):
    """Test a multi-turn conversation through multiple workflow executions."""
    # First turn
    _, conversation_id = await setup_and_run_enhanced_workflow(
        client,
        temporal_client,
        mock_memory,
        mock_llm_service,
        input_data="First turn message"
    )
    
    # Configure mock for second turn
    mock_llm_service.process.return_value = {
        "result": "Second turn response",
        "confidence": 0.92
    }
    
    # Second turn using same conversation ID
    await setup_and_run_enhanced_workflow(
        client,
        temporal_client,
        mock_memory,
        mock_llm_service,
        input_data="Second turn message",
        conversation_id=conversation_id
    )
    
    # Configure mock for third turn
    mock_llm_service.process.return_value = {
        "result": "Third turn response",
        "confidence": 0.88
    }
    
    # Third turn
    workflow_id, _ = await setup_and_run_enhanced_workflow(
        client,
        temporal_client,
        mock_memory,
        mock_llm_service,
        input_data="Third turn message",
        conversation_id=conversation_id
    )
    
    # Verify final workflow result
    status_response = client.get(f"/api/v1/workflow/{workflow_id}")
    status_result = status_response.json()
    
    assert status_result["status"] == "COMPLETED"
    assert status_result["result"]["result"] == "Third turn response"
    
    # Verify full conversation history
    conversation = mock_memory.get_conversation(conversation_id)
    assert len(conversation) == 6  # 3 user messages + 3 assistant responses
    
    # Check message sequence
    assert conversation[0]["content"] == "First turn message"
    assert "Enhanced processed: First turn message" in conversation[1]["content"]
    assert conversation[2]["content"] == "Second turn message"
    assert conversation[3]["content"] == "Second turn response"
    assert conversation[4]["content"] == "Third turn message"
    assert conversation[5]["content"] == "Third turn response"
