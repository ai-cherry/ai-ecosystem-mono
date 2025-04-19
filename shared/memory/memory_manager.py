"""
MemoryManager: a unified, multi‑layer memory orchestration component for our ai-ecosystem-mono repo.
Implements:
  - Short‑term cache in Redis (ephemeral context, TTL‑based)
  - Structured store in Firestore (keyed, canonical facts & artifact records)
  - Semantic vector memory in Pinecone (global long‑term embeddings)
  - Hybrid schema & graph memory in Weaviate (dynamic or relational embeddings)
  - Summarization & pruning of old entries via OpenAI/LLM
  - Importance scoring & retention policies
  - Unified `retrieve(query, context)` and `store(item, metadata)` APIs
  - Audit logging, TTL enforcement, and metadata synchronization across stores
  - Hooks for Temporal workflows to load & persist memory per workflow ID
  - Security: encryption at rest, RBAC checks, metadata tags for tenant isolation

Guidelines for Copilot:
  1. Create a Python class `MemoryManager` with constructor accepting clients for redis, firestore, pinecone, weaviate, and an embedding model.
  2. Implement `async def retrieve(self, query: str, client_id: str, top_k: int = 5) -> List[MemoryItem]` that:
     • Searches Firestore for exact matches (by key or metadata filter `client_id`)
     • Performs semantic similarity lookup in Pinecone + Weaviate (filtered by `client_id`)
     • Merges and sorts results by combined relevance & item importance score
     • Returns structured list of snippets or records
  3. Implement `async def store(self, text: str, metadata: dict, ttl_hours: Optional[int] = None)` that:
     • Writes structured record to Firestore (e.g. under `memories/`)
     • Generates embedding via the model and upserts to Pinecone + Weaviate with metadata
     • If `ttl_hours` provided, cache in Redis under a namespaced key and set expiry
     • Logs the store operation in an audit Firestore collection
  4. Add summarization helpers:
     • `async def summarize_and_archive(self, long_text: str, metadata: dict) -> str`
       – Run an LLM to produce a concise summary
       – Call `store(summary, metadata)` and optionally prune raw text
  5. Add pruning / forgetting logic in `async def prune_old(self, days: int = 180)` that:
     • Scans Firestore for entries older than `days` or with low importance score
     • Summarizes or archives them, then deletes or moves raw data
     • Deletes corresponding vectors in Pinecone/Weaviate via metadata filter
  6. Include `async def score_importance(self, memory_id: str) -> float` to compute or update a custom score (based on recency, access count, manual tags)
  7. Implement a simple RBAC check in each method (e.g. raise if `client_id` not allowed)
  8. Use consistent IDs & metadata tags across all stores for sync & audit
  9. Provide unit‑test stubs at bottom: `test_retrieve()`, `test_store_and_retrieve()`, `test_prune_old()`
 10. Add docstrings pointing to design rationale (multi‑layered memory, hybrid storage)

Above all, generate clean, modular code using best practices (async I/O, type hints, dependency injection). Once Copilot scaffolds the class, review and refine each method to wire up the real clients and handle errors.

# Paste this prompt at the top of memory_manager.py and start accepting Copilot suggestions!
"""

from typing import Any, Dict, List, Optional, Union, TypedDict
import asyncio
import datetime
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from enum import Enum

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.docstore.document import Document

import weaviate
from google.cloud import firestore
import pinecone
import redis

from shared.config import memory_settings
from shared.memory.interfaces import BaseMemory
from shared.memory.redis import RedisMemory
from shared.memory.firestore import FirestoreMemory
from shared.memory.vectorstore import VectorStore


class MemoryItemType(str, Enum):
    """Types of memory items."""
    FACT = "fact"
    CONVERSATION = "conversation"
    DOCUMENT = "document"
    SUMMARY = "summary"
    EMBEDDING = "embedding"


class MemoryItem(TypedDict):
    """Structure for memory items returned from retrieval."""
    id: str
    text: str
    metadata: Dict[str, Any]
    score: float
    source: str  # 'firestore', 'redis', 'pinecone', 'weaviate'
    type: MemoryItemType
    importance: float
    created_at: str
    updated_at: str


class MemoryManager:
    """
    Unified memory management system that orchestrates multiple storage layers.
    
    This class provides a unified interface for storing and retrieving information
    across different memory systems:
    - Short-term memory (Redis): For ephemeral, fast-access data with TTL
    - Structured storage (Firestore): For canonical records and structured data
    - Vector storage (Pinecone): For semantic search via embeddings
    - Graph/schema storage (Weaviate): For relational data with semantic properties
    
    The MemoryManager handles synchronization, consistency, and operations like
    importance scoring and pruning across these systems.
    """
    
    def __init__(
        self,
        redis_client: Optional[RedisMemory] = None,
        firestore_client: Optional[FirestoreMemory] = None,
        pinecone_client: Optional[VectorStore] = None,
        weaviate_client: Optional[Any] = None,
        embedding_model: Optional[Any] = None,
        llm_model: Optional[Any] = None,
        allowed_clients: Optional[List[str]] = None
    ):
        """
        Initialize the MemoryManager with various storage clients.
        
        Args:
            redis_client: Client for Redis operations
            firestore_client: Client for Firestore operations
            pinecone_client: Client for Pinecone vector operations
            weaviate_client: Client for Weaviate operations
            embedding_model: Model for generating embeddings
            llm_model: Model for text generation/summarization
            allowed_clients: List of client IDs with access permissions
        """
        # Initialize storage clients
        self.redis = redis_client or RedisMemory()
        self.firestore = firestore_client or FirestoreMemory()
        self.pinecone = pinecone_client or VectorStore()
        
        # Initialize Weaviate client if not provided
        self.weaviate = weaviate_client
        if not self.weaviate:
            # Setup with default configuration if client not provided
            weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
            weaviate_api_key = os.getenv("WEAVIATE_API_KEY", None)
            
            auth_config = weaviate.auth.AuthApiKey(api_key=weaviate_api_key) if weaviate_api_key else None
            self.weaviate = weaviate.Client(url=weaviate_url, auth_client_secret=auth_config)
            
            # Create schema if it doesn't exist
            self._ensure_weaviate_schema()
        
        # Initialize models
        self.embedding_model = embedding_model or OpenAIEmbeddings(
            openai_api_key=memory_settings.OPENAI_API_KEY
        )
        
        self.llm = llm_model or ChatOpenAI(
            temperature=0,
            model_name="gpt-4-turbo",
            openai_api_key=memory_settings.OPENAI_API_KEY
        )
        
        # Create summarization chain
        self.summarize_chain = load_summarize_chain(self.llm, chain_type="map_reduce")
        
        # Security configuration
        self.allowed_clients = allowed_clients or []
        
        # Logger setup
        self.logger = logging.getLogger(__name__)
    
    async def retrieve(self, query: str, client_id: str, top_k: int = 5) -> List[MemoryItem]:
        """
        Retrieve memory items relevant to the query across all storage layers.
        
        Args:
            query: The search query text
            client_id: The client ID for access control and filtering
            top_k: Maximum number of items to return per source
            
        Returns:
            List of relevant memory items, merged and sorted by relevance
        """
        # Security check
        self._check_client_access(client_id)
        
        # Track operation for auditing
        operation_id = str(uuid.uuid4())
        await self._log_audit(operation_id, "retrieve", client_id, {"query": query, "top_k": top_k})
        
        results = []
        
        # Step 1: Try to get exact matches from Redis (for cached items)
        try:
            cache_key = f"memory:cache:{client_id}:{query.lower().strip()}"
            cached_results = self.redis.get(cache_key)
            if cached_results:
                self.logger.info(f"Cache hit for query: {query}")
                return json.loads(cached_results)
        except Exception as e:
            self.logger.error(f"Error retrieving from Redis: {str(e)}")
        
        # Step 2: Check Firestore for exact or keyword matches
        try:
            # Look for exact key matches first
            exact_match = self.firestore.get(f"memories/{query}")
            if exact_match and exact_match.get("client_id") == client_id:
                # Format as MemoryItem
                item = self._format_firestore_result(exact_match, score=1.0)
                results.append(item)
            
            # Then look for metadata filter matches
            filters = [
                ("client_id", "==", client_id),
                # Add relevant keyword filters based on query
                ("tags", "array_contains", query.lower())
            ]
            firestore_matches = self.firestore.query_documents("memories", filters, limit=top_k)
            
            # Convert to MemoryItems and add to results
            for match in firestore_matches:
                # Skip if it's a duplicate of the exact match
                if exact_match and match.get("id") == exact_match.get("id"):
                    continue
                item = self._format_firestore_result(match, score=0.9)  # Slightly lower than exact match
                results.append(item)
        except Exception as e:
            self.logger.error(f"Error retrieving from Firestore: {str(e)}")
        
        # Step 3: Query Pinecone for semantic search
        try:
            pinecone_results = self.pinecone.query(
                query_text=query,
                top_k=top_k,
                metadata_filter={"client_id": client_id}
            )
            
            # Convert to MemoryItems and add to results
            for match in pinecone_results:
                item = self._format_pinecone_result(match)
                
                # Update importance score if we have it
                item_id = match["metadata"].get("id", "")
                if item_id:
                    importance = await self.score_importance(item_id)
                    item["importance"] = importance
                
                results.append(item)
        except Exception as e:
            self.logger.error(f"Error retrieving from Pinecone: {str(e)}")
        
        # Step 4: Query Weaviate for semantic + relational search
        try:
            weaviate_results = await self._query_weaviate(query, client_id, top_k)
            
            # Add to overall results
            results.extend(weaviate_results)
        except Exception as e:
            self.logger.error(f"Error retrieving from Weaviate: {str(e)}")
        
        # Step 5: Merge, sort, and return results
        # Remove duplicates (prefer higher scores if same ID from different sources)
        unique_results = {}
        for item in results:
            item_id = item["id"]
            if item_id not in unique_results or item["score"] > unique_results[item_id]["score"]:
                unique_results[item_id] = item
        
        # Convert back to list and sort by combined score (relevance + importance)
        final_results = list(unique_results.values())
        final_results.sort(key=lambda x: (x["score"] * 0.7) + (x.get("importance", 0) * 0.3), reverse=True)
        
        # Limit to top_k results overall
        final_results = final_results[:top_k]
        
        # Cache these results for future quick lookup
        try:
            cache_key = f"memory:cache:{client_id}:{query.lower().strip()}"
            self.redis.save(cache_key, json.dumps(final_results), ttl=300)  # Cache for 5 minutes
        except Exception as e:
            self.logger.error(f"Error caching results: {str(e)}")
        
        return final_results
    
    async def store(self, text: str, metadata: dict, ttl_hours: Optional[int] = None) -> str:
        """
        Store a memory item across all relevant storage layers.
        
        Args:
            text: The text content to store
            metadata: Metadata associated with the content
            ttl_hours: Optional TTL for short-term memory in hours
            
        Returns:
            The ID of the stored memory item
        """
        # Security check
        client_id = metadata.get("client_id")
        if not client_id:
            raise ValueError("client_id is required in metadata")
        
        self._check_client_access(client_id)
        
        # Generate a unique ID if not provided
        memory_id = metadata.get("id", str(uuid.uuid4()))
        metadata["id"] = memory_id
        
        # Ensure timestamp
        if "created_at" not in metadata:
            metadata["created_at"] = datetime.utcnow().isoformat()
        metadata["updated_at"] = datetime.utcnow().isoformat()
        
        # Set default memory type if not specified
        if "type" not in metadata:
            metadata["type"] = MemoryItemType.FACT.value
        
        # Prepare structured record
        memory_data = {
            "id": memory_id,
            "text": text,
            "metadata": metadata,
            "client_id": client_id
        }
        
        # Step 1: Store in Firestore (structured store - source of truth)
        try:
            firestore_key = f"memories/{memory_id}"
            self.firestore.save(firestore_key, memory_data)
        except Exception as e:
            self.logger.error(f"Error storing in Firestore: {str(e)}")
            raise
        
        # Step 2: Generate embedding and store in Pinecone
        try:
            self.pinecone.upsert_text(text, metadata)
        except Exception as e:
            self.logger.error(f"Error storing in Pinecone: {str(e)}")
            # Continue - we can still use the other stores
        
        # Step 3: Store in Weaviate with schema awareness
        try:
            await self._store_in_weaviate(text, metadata, memory_id)
        except Exception as e:
            self.logger.error(f"Error storing in Weaviate: {str(e)}")
            # Continue - we can still use the other stores
        
        # Step 4: If TTL provided, cache in Redis
        if ttl_hours is not None and ttl_hours > 0:
            try:
                ttl_seconds = ttl_hours * 3600
                redis_key = f"memory:{client_id}:{memory_id}"
                self.redis.save(redis_key, memory_data, ttl=ttl_seconds)
            except Exception as e:
                self.logger.error(f"Error caching in Redis: {str(e)}")
        
        # Step 5: Log the operation for audit
        try:
            operation_id = str(uuid.uuid4())
            await self._log_audit(
                operation_id, 
                "store", 
                client_id, 
                {"memory_id": memory_id, "ttl_hours": ttl_hours}
            )
        except Exception as e:
            self.logger.error(f"Error logging audit: {str(e)}")
        
        return memory_id
    
    async def summarize_and_archive(self, long_text: str, metadata: dict) -> str:
        """
        Summarize a long text, store the summary, and optionally archive the original.
        
        Args:
            long_text: The long text to summarize
            metadata: Metadata associated with the text
            
        Returns:
            The ID of the stored summary
        """
        # Security check
        client_id = metadata.get("client_id")
        if not client_id:
            raise ValueError("client_id is required in metadata")
        
        self._check_client_access(client_id)
        
        # Split text into manageable chunks if needed
        max_chunk_size = 4000
        chunks = []
        if len(long_text) > max_chunk_size:
            words = long_text.split()
            current_chunk = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 > max_chunk_size:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [word]
                    current_length = len(word)
                else:
                    current_chunk.append(word)
                    current_length += len(word) + 1
            
            if current_chunk:
                chunks.append(" ".join(current_chunk))
        else:
            chunks = [long_text]
        
        # Create LangChain documents for summarization
        documents = [Document(page_content=chunk) for chunk in chunks]
        
        # Generate summary
        try:
            summary = self.summarize_chain.run(documents)
        except Exception as e:
            self.logger.error(f"Error during summarization: {str(e)}")
            # Fallback to first 200 characters + ellipsis as summary if summarization fails
            summary = long_text[:200] + "..." if len(long_text) > 200 else long_text
        
        # Prepare metadata for summary
        summary_metadata = metadata.copy()
        summary_metadata["type"] = MemoryItemType.SUMMARY.value
        summary_metadata["original_length"] = len(long_text)
        
        if "original_id" not in summary_metadata and "id" in metadata:
            summary_metadata["original_id"] = metadata["id"]
            # Generate new ID for summary
            if "id" in summary_metadata:
                del summary_metadata["id"]
        
        # Store the summary
        summary_id = await self.store(summary, summary_metadata)
        
        # Archive the original text if needed
        # This could move it to cold storage, mark it as archived, etc.
        if metadata.get("archive_original", True) and "id" in metadata:
            original_id = metadata["id"]
            
            # Get original from Firestore
            firestore_key = f"memories/{original_id}"
            original_doc = self.firestore.get(firestore_key)
            
            if original_doc:
                # Mark as archived and reference summary
                original_doc["archived"] = True
                original_doc["summary_id"] = summary_id
                original_doc["metadata"]["archived"] = True
                original_doc["metadata"]["summary_id"] = summary_id
                
                # Update in Firestore
                self.firestore.save(firestore_key, original_doc)
        
        return summary_id
    
    async def prune_old(self, days: int = 180, min_importance_score: float = 0.3) -> int:
        """
        Prune old or low-importance memories across all storage layers.
        
        Args:
            days: Age threshold in days for pruning
            min_importance_score: Minimum importance score to retain
            
        Returns:
            Number of pruned items
        """
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()
        
        pruned_count = 0
        
        # Step 1: Find candidates for pruning in Firestore
        try:
            # Find old items
            old_items_filter = [
                ("created_at", "<", cutoff_str),
                ("archived", "==", False)  # Don't re-prune already archived items
            ]
            old_items = self.firestore.query_documents("memories", old_items_filter)
            
            # Find low importance items (requires checking each)
            importance_pruned = []
            for item in old_items:
                try:
                    item_id = item.get("id")
                    importance = await self.score_importance(item_id)
                    
                    # If important enough, keep it regardless of age
                    if importance >= min_importance_score:
                        continue
                    
                    importance_pruned.append(item)
                except Exception as e:
                    self.logger.error(f"Error scoring importance for {item_id}: {str(e)}")
            
            # Combine lists (may have duplicates, will handle later)
            prune_candidates = old_items + importance_pruned
            
            # Step 2: Process each candidate
            for item in prune_candidates:
                item_id = item.get("id")
                if not item_id:
                    continue
                    
                client_id = item.get("client_id")
                if not client_id:
                    continue
                
                # Check if we have permission for this client
                try:
                    self._check_client_access(client_id)
                except Exception:
                    # Skip items we don't have permission for
                    continue
                
                # Skip if already processed this ID (avoid duplicates)
                if getattr(self, "_pruned_ids", None) is None:
                    self._pruned_ids = set()
                
                if item_id in self._pruned_ids:
                    continue
                    
                self._pruned_ids.add(item_id)
                
                # 2.1. Summarize if it's a long text
                text = item.get("text", "")
                if len(text) > 200:  # Only summarize if reasonably long
                    metadata = item.get("metadata", {}).copy()
                    metadata["client_id"] = client_id
                    metadata["pruned_from"] = item_id
                    metadata["archive_original"] = True
                    
                    try:
                        await self.summarize_and_archive(text, metadata)
                    except Exception as e:
                        self.logger.error(f"Error summarizing item {item_id}: {str(e)}")
                
                # 2.2. Delete or archive from all stores
                try:
                    # Delete from Pinecone
                    self.pinecone.delete(item_id)
                    
                    # Delete from Weaviate
                    await self._delete_from_weaviate(item_id)
                    
                    # Delete from Redis
                    self.redis.delete(f"memory:{client_id}:{item_id}")
                    
                    # Mark as archived in Firestore (keep a record)
                    firestore_key = f"memories/{item_id}"
                    item["archived"] = True
                    item["pruned_at"] = datetime.utcnow().isoformat()
                    self.firestore.save(firestore_key, item)
                    
                    pruned_count += 1
                except Exception as e:
                    self.logger.error(f"Error pruning item {item_id}: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Error during pruning operation: {str(e)}")
        
        # Clean up temp storage
        if hasattr(self, "_pruned_ids"):
            delattr(self, "_pruned_ids")
        
        return pruned_count
    
    async def score_importance(self, memory_id: str) -> float:
        """
        Compute or update the importance score for a memory item.
        
        Importance scoring factors:
        - Recency: More recent items score higher
        - Access frequency: More frequently accessed items score higher
        - Manual importance: Explicitly set importance values
        - Content type: Some types may be inherently more important
        
        Args:
            memory_id: The ID of the memory item
            
        Returns:
            Importance score between 0.0 and 1.0
        """
        # Get the item from Firestore (source of truth)
        firestore_key = f"memories/{memory_id}"
        item = self.firestore.get(firestore_key)
        
        if not item:
            return 0.0
        
        metadata = item.get("metadata", {})
        
        # Start with base score
        score = 0.5
        
        # Factor 1: Explicit importance if set
        explicit_importance = metadata.get("importance")
        if explicit_importance is not None:
            try:
                explicit_score = float(explicit_importance)
                # Explicit score is weighted heavily
                score = explicit_score * 0.6 + score * 0.4
            except (ValueError, TypeError):
                pass
        
        # Factor 2: Recency
        created_at = metadata.get("created_at")
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                now = datetime.utcnow()
                age_days = (now - created_date).days
                
                # Newer items score higher
                recency_score = max(0, 1 - (age_days / 365))  # Linear decay over a year
                score = score * 0.7 + recency_score * 0.3
            except (ValueError, TypeError):
                pass
        
        # Factor 3: Access count
        access_count = metadata.get("access_count", 0)
        if access_count:
            try:
                # Normalize access count (assumed max ~100)
                access_score = min(1.0, access_count / 100)
                score = score * 0.8 + access_score * 0.2
            except (ValueError, TypeError):
                pass
        
        # Factor 4: Content type importance
        type_importance = {
            MemoryItemType.FACT.value: 0.7,
            MemoryItemType.CONVERSATION.value: 0.5,
            MemoryItemType.DOCUMENT.value: 0.6,
            MemoryItemType.SUMMARY.value: 0.8,  # Summaries are important
            MemoryItemType.EMBEDDING.value: 0.4
        }
        
        content_type = metadata.get("type", MemoryItemType.FACT.value)
        type_score = type_importance.get(content_type, 0.5)
        score = score * 0.9 + type_score * 0.1
        
        # Factor 5: Tags (some tags might indicate importance)
        important_tags = {"important", "critical", "key", "permanent"}
        tags = set(metadata.get("tags", []))
        
        if tags & important_tags:  # If there's any overlap
            score = min(1.0, score + 0.2)  # Boost score but cap at 1.0
        
        # Update access count and importance score in Firestore
        try:
            item["metadata"]["access_count"] = access_count + 1
            item["metadata"]["importance_score"] = score
            item["metadata"]["last_accessed"] = datetime.utcnow().isoformat()
            self.firestore.save(firestore_key, item)
        except Exception as e:
            self.logger.error(f"Error updating importance for {memory_id}: {str(e)}")
        
        return score
    
    def _check_client_access(self, client_id: str) -> None:
        """
        Check if the client has access permissions.
        
        Args:
            client_id: The client ID to check
            
        Raises:
            PermissionError: If the client doesn't have access
        """
        # If no allowed clients specified, allow all
        if not self.allowed_clients:
            return
            
        # Check if client ID is in allowed list
        if client_id not in self.allowed_clients:
            self.logger.warning(f"Access denied for client {client_id}")
            raise PermissionError(f"Client {client_id} does not have access to this memory manager")
    
    def _ensure_weaviate_schema(self) -> None:
        """Create the Weaviate schema if it doesn't exist."""
        # Check if schema exists
        try:
            schema = self.weaviate.schema.get()
            classes = [c["class"] for c in schema["classes"]] if "classes" in schema else []
            
            # If Memory class already exists, we're done
            if "Memory" in classes:
                return
                
            # Define Memory class
            memory_class = {
                "class": "Memory",
                "description": "A memory item in the graph",
                "vectorizer": "text2vec-openai",  # Assuming use of OpenAI embeddings
                "properties": [
                    {
                        "name": "text",
                        "description": "The content of the memory",
                        "dataType": ["text"]
                    },
                    {
                        "name": "type",
                        "description": "The type of memory",
                        "dataType": ["string"]
                    },
                    {
                        "name": "clientId",
                        "description": "The client ID associated with this memory",
                        "dataType": ["string"],
                        "indexInverted": True
                    },
                    {
                        "name": "createdAt",
                        "description": "When this memory was created",
                        "dataType": ["date"]
                    },
                    {
                        "name": "importance",
                        "description": "The importance score of this memory",
                        "dataType": ["number"]
                    },
                    {
                        "name": "tags",
                        "description": "Associated tags",
                        "dataType": ["string[]"]
                    },
                    {
                        "name": "relatesTo",
                        "description": "Related memories",
                        "dataType": ["Memory"]
                    }
                ]
            }
            
            # Create the schema in Weaviate
            self.weaviate.schema.create_class(memory_class)
            self.logger.info("Created Memory class in Weaviate schema")
            
        except Exception as e:
            self.logger.error(f"Error creating Weaviate schema: {str(e)}")
    
    async def _store_in_weaviate(self, text: str, metadata: dict, memory_id: str) -> None:
        """Store a memory item in Weaviate."""
        try:
            # Convert metadata to Weaviate format
            weaviate_props = {
                "text": text,
                "type": metadata.get("type", MemoryItemType.FACT.value),
                "clientId": metadata.get("client_id", ""),
                "createdAt": metadata.get("created_at", datetime.utcnow().isoformat()),
                "importance": metadata.get("importance_score", 0.5),
            }
            
            # Include tags if available
            if "tags" in metadata:
                weaviate_props["tags"] = metadata["tags"]
            
            # Store the item with the specified UUID
            self.weaviate.data_object.create(
                weaviate_props,
                "Memory",
                memory_id
            )
        except Exception as e:
            self.logger.error(f"Error storing in Weaviate: {str(e)}")
            raise
    
    async def _delete_from_weaviate(self, memory_id: str) -> None:
        """Delete a memory item from Weaviate."""
        try:
            self.weaviate.data_object.delete(
                "Memory",
                memory_id
            )
        except Exception as e:
            self.logger.error(f"Error deleting from Weaviate: {str(e)}")
    
    async def _query_weaviate(self, query: str, client_id: str, top_k: int = 5) -> List[MemoryItem]:
        """Query Weaviate for related memories."""
        try:
            # Prepare GraphQL query with client_id filter
            graphql_query = {
                "query": f"""
                {{
                  Get {{
                    Memory(
                      nearText: {{
                        concepts: ["{query}"]
                      }}
                      where: {{
                        path: ["clientId"]
                        operator: Equal
                        valueString: "{client_id}"
                      }}
                      limit: {top_k}
                    ) {{
                      _additional {{
                        id
                        certainty
                      }}
                      text
                      type
                      clientId
                      createdAt
                      importance
                      tags
                    }}
                  }}
                }}
                """
            }
            
            # Execute the query
            result = self.weaviate.query.raw(graphql_query)
            
            # Process results
            memories = []
            if result and "data" in result and "Get" in result["data"] and "Memory" in result["data"]["Get"]:
                for item in result["data"]["Get"]["Memory"]:
                    certainty = item["_additional"]["certainty"] if "_additional" in item and "certainty" in item["_additional"] else 0.0
                    
                    memory_item = MemoryItem(
                        id=item["_additional"]["id"],
                        text=item["text"],
                        metadata={
                            "client_id": item["clientId"],
                            "type": item["type"],
                            "created_at": item["createdAt"],
                            "tags": item.get("tags", [])
                        },
                        score=certainty,
                        source="weaviate",
                        type=item["type"],
                        importance=item.get("importance", 0.5),
                        created_at=item["createdAt"],
                        updated_at=item.get("updatedAt", item["createdAt"])
                    )
                    memories.append(memory_item)
                    
            return memories
            
        except Exception as e:
            self.logger.error(f"Error querying Weaviate: {str(e)}")
            return []
    
    def _format_firestore_result(self, doc: dict, score: float = 0.0) -> MemoryItem:
        """Format a Firestore document as a MemoryItem."""
        metadata = doc.get("metadata", {})
        memory_type = metadata.get("type", MemoryItemType.FACT.value)
        
        return MemoryItem(
            id=doc.get("id", ""),
            text=doc.get("text", ""),
            metadata=metadata,
            score=score,
            source="firestore",
            type=memory_type,
            importance=metadata.get("importance_score", 0.5),
            created_at=metadata.get("created_at", ""),
            updated_at=metadata.get("updated_at", "")
        )
    
    def _format_pinecone_result(self, match: dict) -> MemoryItem:
        """Format a Pinecone match as a MemoryItem."""
        metadata = match.get("metadata", {})
        memory_type = metadata.get("type", MemoryItemType.EMBEDDING.value)
        
        return MemoryItem(
            id=metadata.get("id", ""),
            text=metadata.get("text", ""),
            metadata=metadata,
            score=match.get("score", 0.0),
            source="pinecone",
            type=memory_type,
            importance=metadata.get("importance_score", 0.5),
            created_at=metadata.get("created_at", ""),
            updated_at=metadata.get("updated_at", "")
        )
    
    async def _log_audit(self, operation_id: str, operation_type: str, client_id: str, details: dict) -> None:
        """Log an audit entry for a memory operation."""
        try:
            audit_entry = {
                "id": operation_id,
                "operation_type": operation_type,
                "client_id": client_id,
                "details": details,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": details.get("user_id", "system")
            }
            
            self.firestore.save(f"memory_audit/{operation_id}", audit_entry)
        except Exception as e:
            self.logger.error(f"Error logging audit: {str(e)}")


# Unit test stubs

async def test_retrieve():
    """Test retrieving memory items."""
    # TODO: Implement unit test for retrieve functionality
    pass

async def test_store_and_retrieve():
    """Test storing and then retrieving a memory item."""
    # TODO: Implement unit test for full memory lifecycle
    pass

async def test_prune_old():
    """Test pruning old or low-importance memory items."""
    # TODO: Implement unit test for pruning functionality
    pass
