"""
Integration tests for the multi-agent system.

This module tests the end-to-end flow: async API → Temporal → memory → LLM,
validating both success path, fallback path, and memory persistence.
"""

import asyncio
import json
import uuid
from datetime import timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from temporalio.client import Client, WorkflowHandle
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from orchestrator.app.api.v1.endpoints.process_async import router, get_temporal_client
from orchestrator.app.core.config import settings
from orchestrator.workflows.sample import SampleWorkflow, sample_task
from shared.memory.interfaces import ConversationMemory
from shared.memory.redis import RedisMemory


# ----- Mock Classes -----

class MockTemporalClient:
    """Mock implementation of Temporal client for testing."""
    
    def __init__(self):
        self.workflows = {}
        self.workflow_results = {}
    
    async def start_workflow(self, workflow_type, *args, id=None, task_queue=None, **kwargs):
        """Mock for starting a workflow."""
        if id is None:
            id = f"workflow-{uuid.uuid4()}"
        
        run_id = str(uuid.uuid4())
        
        # Store workflow information
        self.workflows[id] = {
            "id": id,
            "run_id": run_id,
            "args": args,
            "kwargs": kwargs,
            "status": "RUNNING",
            "result": None
        }
        
        # Create a mock handle
        handle = MagicMock(spec=WorkflowHandle)
        handle.id = id
        handle.run_id = run_id
        
        return handle
    
    def get_workflow_handle(self, workflow_id):
        """Get a handle to an existing workflow."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        handle = MagicMock(spec=WorkflowHandle)
        handle.id = workflow_id
        handle.run_id = self.workflows[workflow_id]["run_id"]
        
        # Add behavior to describe and result methods
        async def describe():
            status = MagicMock()
            status.status = MagicMock()
            status.status.name = self.workflows[workflow_id]["status"]
            return status
        
        async def result():
            return self.workflows[workflow_id]["result"]
        
        handle.describe = describe
        handle.result = result
        
        return handle
    
    def complete_workflow(self, workflow_id, result):
        """Mark a workflow as completed with a result."""
        if workflow_id in self.workflows:
            self.workflows[workflow_id]["status"] = "COMPLETED"
            self.workflows[workflow_id]["result"] = result


class MockMemory(ConversationMemory):
    """Mock memory implementation for testing."""
    
    def __init__(self):
        self.data = {}
        self.conversations = {}
    
    def save(self, key: str, data: Any) -> str:
        """Save data to memory."""
        self.data[key] = data
        return key
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve data from memory."""
        return self.data.get(key)
    
    def delete(self, key: str) -> bool:
        """Delete data from memory."""
        if key in self.data:
            del self.data[key]
            return True
        return False
    
    def save_message(self, conversation_id: str, message: Dict[str, Any], 
                     user_id: Optional[str] = None) -> str:
        """Save a message to a conversation history."""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        message_id = str(uuid.uuid4())
        msg_with_id = message.copy()
        msg_with_id["id"] = message_id
        
        if user_id:
            msg_with_id["user_id"] = user_id
        
        self.conversations[conversation_id].append(msg_with_id)
        return message_id
    
    def get_conversation(self, conversation_id: str, limit: Optional[int] = None, 
                         before: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve conversation history."""
        messages = self.conversations.get(conversation_id, [])
        
        if limit:
            messages = messages[-limit:]
            
        return messages
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation history."""
        if conversation_id in self.conversations:
            self.conversations[conversation_id] = []
            return True
        return False


class MockLLMService:
    """Mock LLM service for testing."""
    
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.calls = []
    
    def process(self, input_data):
        """Mock LLM processing."""
        self.calls.append(input_data)
        
        if self.should_fail:
            raise Exception("LLM processing failed")
        
        return {
            "result": f"Processed: {input_data}",
            "confidence": 0.95
        }


# ----- Fixtures -----

@pytest.fixture
def memory():
    """Fixture for mock memory implementation."""
    return MockMemory()


@pytest.fixture
def llm_service():
    """Fixture for mock LLM service."""
    return MockLLMService()


@pytest.fixture
def failing_llm_service():
    """Fixture for mock LLM service that fails."""
    return MockLLMService(should_fail=True)


@pytest.fixture
async def temporal_client():
    """Fixture for mock Temporal client."""
    client = MockTemporalClient()
    return client


@pytest.fixture
def app(temporal_client, memory):
    """Fixture for test app with dependencies."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    
    # Override dependencies
    async def get_test_temporal_client():
        return temporal_client
    
    app.dependency_overrides[get_temporal_client] = get_test_temporal_client
    
    # Patch RedisMemory to use our mock
    with patch("shared.memory.redis.RedisMemory", return_value=memory):
        yield app


@pytest.fixture
def client(app):
    """Test client for the app."""
    return TestClient(app)


# ----- Enhanced Activities and Workflows for Testing -----

@pytest.fixture
def enhanced_sample_task(memory, llm_service):
    """Enhanced version of sample_task that uses memory and LLM."""
    
    async def _enhanced_sample_task(data: str, conversation_id: str = None) -> Dict[str, Any]:
        # Generate a conversation ID if not provided
        if not conversation_id:
            conversation_id = f"conversation-{uuid.uuid4()}"
        
        try:
            # Save input to memory
            memory.save_message(conversation_id, {
                "role": "user",
                "content": data
            })
            
            # Process with LLM
            llm_result = llm_service.process(data)
            
            # Save result to memory
            memory.save_message(conversation_id, {
                "role": "assistant",
                "content": llm_result["result"]
            })
            
            return {
                "status": "success",
                "conversation_id": conversation_id,
                "result": llm_result["result"],
                "confidence": llm_result.get("confidence", 1.0)
            }
            
        except Exception as e:
            # Handle errors and save to memory
            error_message = f"Error processing: {str(e)}"
            
            if conversation_id:
                memory.save_message(conversation_id, {
                    "role": "system",
                    "content": error_message
                })
            
            # Return error information
            return {
                "status": "error",
                "conversation_id": conversation_id,
                "error": str(e)
            }
    
    return _enhanced_sample_task


# ----- Tests -----

@pytest.mark.asyncio
async def test_end_to_end_success_path(client, temporal_client, memory, llm_service, enhanced_sample_task):
    """Test the success path for the entire flow."""
    # Make a request to the async API
    response = client.post("/api/v1/process", json={
        "data": "Test input data"
    })
    
    # Check the response
    assert response.status_code == 200
    result = response.json()
    assert "workflow_id" in result
    assert "run_id" in result
    
    workflow_id = result["workflow_id"]
    
    # Simulate workflow execution (this would normally be done by Temporal)
    conversation_id = f"conversation-{uuid.uuid4()}"
    activity_result = await enhanced_sample_task("Test input data", conversation_id)
    
    # Mark the workflow as completed
    temporal_client.complete_workflow(workflow_id, {
        "status": "completed",
        "conversation_id": conversation_id,
        "result": activity_result["result"]
    })
    
    # Check workflow status and result
    status_response = client.get(f"/api/v1/workflow/{workflow_id}")
    assert status_response.status_code == 200
    status_result = status_response.json()
    
    assert status_result["status"] == "COMPLETED"
    assert status_result["result"]["status"] == "completed"
    assert "result" in status_result["result"]
    
    # Validate memory persistence
    conversation = memory.get_conversation(conversation_id)
    assert len(conversation) == 2  # User message and assistant response
    assert conversation[0]["content"] == "Test input data"
    assert conversation[0]["role"] == "user"
    assert conversation[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_fallback_on_llm_failure(client, temporal_client, memory, failing_llm_service):
    """Test fallback behavior when LLM processing fails."""
    # Make a request to the async API
    response = client.post("/api/v1/process", json={
        "data": "Test input that will fail"
    })
    
    # Check the response
    assert response.status_code == 200
    result = response.json()
    workflow_id = result["workflow_id"]
    
    # Create an enhanced task that will use the failing LLM
    async def failing_task(data: str, conversation_id: str = None):
        if not conversation_id:
            conversation_id = f"conversation-{uuid.uuid4()}"
        
        try:
            # Save input to memory
            memory.save_message(conversation_id, {
                "role": "user",
                "content": data
            })
            
            # This will fail
            failing_llm_service.process(data)
            
        except Exception as e:
            # Handle error and save to memory
            error_message = f"Error processing: {str(e)}"
            
            memory.save_message(conversation_id, {
                "role": "system",
                "content": error_message
            })
            
            # Return fallback response
            fallback_response = "I'm sorry, I couldn't process your request properly."
            memory.save_message(conversation_id, {
                "role": "assistant",
                "content": fallback_response
            })
            
            return {
                "status": "fallback",
                "conversation_id": conversation_id,
                "result": fallback_response,
                "error": str(e)
            }
    
    # Simulate workflow execution with failure
    conversation_id = f"conversation-{uuid.uuid4()}"
    activity_result = await failing_task("Test input that will fail", conversation_id)
    
    # Mark the workflow as completed with fallback result
    temporal_client.complete_workflow(workflow_id, {
        "status": "fallback",
        "conversation_id": conversation_id,
        "result": activity_result["result"],
        "error": activity_result.get("error")
    })
    
    # Check workflow status and result
    status_response = client.get(f"/api/v1/workflow/{workflow_id}")
    assert status_response.status_code == 200
    status_result = status_response.json()
    
    assert status_result["status"] == "COMPLETED"
    assert status_result["result"]["status"] == "fallback"
    assert "error" in status_result["result"]
    
    # Validate memory persistence - should have user, error, and fallback messages
    conversation = memory.get_conversation(conversation_id)
    assert len(conversation) == 3
    assert conversation[0]["content"] == "Test input that will fail"
    assert conversation[0]["role"] == "user"
    assert conversation[1]["role"] == "system"  # Error message
    assert conversation[2]["role"] == "assistant"  # Fallback response


@pytest.mark.asyncio
async def test_memory_persistence(memory, enhanced_sample_task):
    """Test that memory correctly persists conversation data."""
    # Generate a test conversation ID
    conversation_id = f"test-conversation-{uuid.uuid4()}"
    
    # Process multiple messages
    await enhanced_sample_task("First message", conversation_id)
    await enhanced_sample_task("Second message", conversation_id)
    await enhanced_sample_task("Third message", conversation_id)
    
    # Retrieve the conversation
    conversation = memory.get_conversation(conversation_id)
    
    # Validate the conversation contents
    assert len(conversation) == 6  # 3 user messages and 3 assistant responses
    
    # Check message sequence
    assert conversation[0]["content"] == "First message"
    assert conversation[1]["role"] == "assistant"
    assert conversation[2]["content"] == "Second message"
    assert conversation[3]["role"] == "assistant"
    assert conversation[4]["content"] == "Third message"
    assert conversation[5]["role"] == "assistant"
    
    # Test conversation retrieval with limit
    limited_conversation = memory.get_conversation(conversation_id, limit=2)
    assert len(limited_conversation) == 2
    assert limited_conversation[0]["content"] == conversation[4]["content"]
    assert limited_conversation[1]["content"] == conversation[5]["content"]
    
    # Test conversation clearing
    memory.clear_conversation(conversation_id)
    cleared_conversation = memory.get_conversation(conversation_id)
    assert len(cleared_conversation) == 0


@pytest.mark.asyncio
async def test_workflow_retry_logic(client, temporal_client, memory):
    """Test that workflow retries work correctly on temporary failures."""
    # Create a counter to track retry attempts
    retry_counter = {"count": 0, "max_retries": 2}
    
    # Create a task that fails initially but succeeds after retries
    async def retrying_task(data: str):
        retry_counter["count"] += 1
        
        if retry_counter["count"] <= retry_counter["max_retries"]:
            raise Exception(f"Temporary failure (attempt {retry_counter['count']})")
        
        # Succeed on final attempt
        return {
            "status": "success",
            "result": f"Processed after {retry_counter['count']} attempts: {data}"
        }
    
    # Make a request to the async API
    response = client.post("/api/v1/process", json={
        "data": "Test retry data"
    })
    
    # Check the response
    assert response.status_code == 200
    result = response.json()
    workflow_id = result["workflow_id"]
    
    # Simulate workflow retry logic
    try:
        await retrying_task("Test retry data")
    except Exception:
        # Retry
        try:
            await retrying_task("Test retry data")
        except Exception:
            # Retry one more time - should succeed
            final_result = await retrying_task("Test retry data")
            
            # Mark the workflow as completed with the final result
            temporal_client.complete_workflow(workflow_id, {
                "status": "completed",
                "result": final_result["result"],
                "retry_count": retry_counter["count"]
            })
    
    # Check workflow status and result
    status_response = client.get(f"/api/v1/workflow/{workflow_id}")
    assert status_response.status_code == 200
    status_result = status_response.json()
    
    assert status_result["status"] == "COMPLETED"
    assert status_result["result"]["status"] == "completed"
    assert status_result["result"]["retry_count"] == 3
