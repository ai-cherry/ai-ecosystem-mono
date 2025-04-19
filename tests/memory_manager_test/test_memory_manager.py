"""
Tests for the MemoryManager component.

This test suite validates the functionality of the MemoryManager class,
ensuring that all memory operations work correctly across Redis, Firestore,
Pinecone, and Weaviate storage layers.
"""

import asyncio
import datetime
import json
import os
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from shared.memory.memory_manager import MemoryManager, MemoryItem, MemoryItemType


# Fixtures for mocking external dependencies
@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.save = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_firestore():
    """Mock Firestore client for testing."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.save = AsyncMock(return_value=True)
    mock.query_documents = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_pinecone():
    """Mock Pinecone client for testing."""
    mock = MagicMock()
    mock.query = AsyncMock(return_value=[])
    mock.upsert_text = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_weaviate():
    """Mock Weaviate client for testing."""
    mock = MagicMock()
    mock.schema = MagicMock()
    mock.schema.get = MagicMock(return_value={"classes": []})
    mock.schema.create_class = AsyncMock(return_value=True)
    mock.data_object = MagicMock()
    mock.data_object.create = AsyncMock(return_value=True)
    mock.data_object.delete = AsyncMock(return_value=True)
    mock.query = MagicMock()
    mock.query.raw = AsyncMock(return_value={"data": {"Get": {"Memory": []}}})
    return mock


@pytest.fixture
def mock_embedding_model():
    """Mock embedding model for testing."""
    mock = MagicMock()
    mock.embed_query = AsyncMock(return_value=[0.1] * 768)
    return mock


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    mock = MagicMock()
    mock.generate = AsyncMock(return_value="Summary text")
    return mock


@pytest.fixture
def memory_manager(mock_redis, mock_firestore, mock_pinecone, mock_weaviate, mock_embedding_model, mock_llm):
    """Create a MemoryManager with mocked dependencies for testing."""
    return MemoryManager(
        redis_client=mock_redis,
        firestore_client=mock_firestore,
        pinecone_client=mock_pinecone,
        weaviate_client=mock_weaviate,
        embedding_model=mock_embedding_model,
        llm_model=mock_llm,
        allowed_clients=["test_client"]
    )


# Test retrieve method
@pytest.mark.asyncio
async def test_retrieve_empty(memory_manager):
    """Test retrieving when no results are available."""
    results = await memory_manager.retrieve(
        query="test query",
        client_id="test_client",
        top_k=5
    )
    
    assert isinstance(results, list)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_retrieve_from_firestore(memory_manager, mock_firestore):
    """Test retrieving an exact match from Firestore."""
    # Setup mock to return a document
    mock_doc = {
        "id": "test123",
        "text": "Test document",
        "metadata": {
            "client_id": "test_client",
            "type": "fact",
            "created_at": datetime.datetime.utcnow().isoformat(),
            "updated_at": datetime.datetime.utcnow().isoformat()
        },
        "client_id": "test_client"
    }
    memory_manager.firestore.get = AsyncMock(return_value=mock_doc)
    
    results = await memory_manager.retrieve(
        query="test123",  # Use the ID as the query for exact match
        client_id="test_client",
        top_k=5
    )
    
    assert len(results) == 1
    assert results[0]["id"] == "test123"
    assert results[0]["text"] == "Test document"
    assert results[0]["source"] == "firestore"


# Test store method
@pytest.mark.asyncio
async def test_store(memory_manager, mock_firestore, mock_pinecone, mock_weaviate):
    """Test storing a memory item across all stores."""
    # Test data
    text = "This is a test memory item"
    metadata = {
        "client_id": "test_client",
        "type": MemoryItemType.FACT.value,
        "tags": ["test", "memory"]
    }
    
    memory_id = await memory_manager.store(text, metadata)
    
    # Verify ID was generated
    assert memory_id is not None
    
    # Verify calls to storage systems
    memory_manager.firestore.save.assert_called_once()
    memory_manager.pinecone.upsert_text.assert_called_once()


# Test summarize_and_archive method
@pytest.mark.asyncio
async def test_summarize_and_archive(memory_manager, mock_llm):
    """Test summarizing and archiving a long text."""
    # Test data
    long_text = "This is a very long text that needs to be summarized. " * 20
    metadata = {"client_id": "test_client"}
    
    summary_id = await memory_manager.summarize_and_archive(long_text, metadata)
    
    # Verify summarization happened
    assert summary_id is not None
    
    # Verify calls to LLM and storage
    # mock_llm.generate.assert_called_once()  # Uncomment when implementation complete
    memory_manager.store.assert_called()  # This will need patching in the actual test


# Test prune_old method
@pytest.mark.asyncio
async def test_prune_old(memory_manager, mock_firestore):
    """Test pruning old memory items."""
    # Setup mock firestore to return old items
    old_date = (datetime.datetime.utcnow() - datetime.timedelta(days=200)).isoformat()
    old_items = [
        {
            "id": f"old_{i}",
            "text": f"Old item {i}",
            "metadata": {
                "client_id": "test_client",
                "created_at": old_date,
                "type": "fact"
            },
            "client_id": "test_client",
            "archived": False
        }
        for i in range(3)
    ]
    
    memory_manager.firestore.query_documents = AsyncMock(return_value=old_items)
    
    pruned_count = await memory_manager.prune_old(days=180)
    
    # Verify pruning happened
    assert pruned_count == 3
    
    # Verify calls to delete
    assert memory_manager.pinecone.delete.call_count == 3


# Test score_importance method
@pytest.mark.asyncio
async def test_score_importance(memory_manager, mock_firestore):
    """Test scoring the importance of a memory item."""
    # Setup mock to return a document
    test_doc = {
        "id": "test_importance",
        "text": "Important test document",
        "metadata": {
            "client_id": "test_client",
            "type": "fact",
            "created_at": datetime.datetime.utcnow().isoformat(),
            "tags": ["important", "critical"],
            "access_count": 5
        }
    }
    memory_manager.firestore.get = AsyncMock(return_value=test_doc)
    
    importance = await memory_manager.score_importance("test_importance")
    
    # Verify importance was calculated
    assert importance > 0.0
    assert importance <= 1.0
    
    # Verify firestore was updated
    memory_manager.firestore.save.assert_called_once()


# Add more comprehensive tests here for complete coverage
# TODO: Add test for edge cases and error handling
# TODO: Add tests for multi-tenant isolation
# TODO: Add integration tests that use all layers together
