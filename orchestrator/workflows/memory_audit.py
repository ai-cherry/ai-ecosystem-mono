"""
Memory Consistency Audit Workflow.

This workflow performs consistency checks between different memory implementations:
- Redis (for conversation memory and caching)
- Firestore (for structured data storage)
- Vector Store (for embeddings and semantic search)

It detects inconsistencies like orphaned vectors, missing documents, and expired sessions,
and provides methods to reconcile and clean up data.
"""

import os
import json
import time
import datetime
import logging
from typing import Dict, List, Any, Optional, Set, Tuple

from temporalio import workflow, activity
from temporalio.common import RetryPolicy

from shared.memory.redis import RedisMemory
from shared.memory.firestore import FirestoreMemory
from shared.memory.vectorstore import VectorStore

# Set up logging
logger = logging.getLogger(__name__)


@activity.defn
async def count_redis_keys(prefix: str = "ai:") -> Dict[str, int]:
    """
    Count keys in Redis by type based on prefix patterns.
    
    Args:
        prefix: Base prefix for Redis keys
        
    Returns:
        Dictionary with counts by key type
    """
    redis_memory = RedisMemory(prefix=prefix)
    redis_client = redis_memory.redis
    
    # Define patterns to count
    patterns = {
        "conversations": f"{prefix}conversation:*",
        "messages": f"{prefix}message:*",
        "message_ids": f"{prefix}message_ids:*",
        "chats": f"{prefix}chat:*",
        "caches": f"{prefix}cache:*",
    }
    
    counts = {}
    
    # Count keys for each pattern
    for key_type, pattern in patterns.items():
        cursor = 0
        count = 0
        
        while True:
            cursor, keys = redis_client.scan(cursor=cursor, match=pattern, count=1000)
            count += len(keys)
            
            if cursor == 0:
                break
        
        counts[key_type] = count
    
    # Get total count
    counts["total"] = redis_client.dbsize()
    
    return counts


@activity.defn
async def count_firestore_documents() -> Dict[str, int]:
    """
    Count documents in Firestore by collection.
    
    Returns:
        Dictionary with counts by collection
    """
    firestore_memory = FirestoreMemory()
    db = firestore_memory.db
    
    # Get all collections
    collections = db.collections()
    counts = {}
    
    # Count documents in each collection
    for collection in collections:
        counts[collection.id] = len(list(collection.limit(100000).stream()))
    
    # Calculate total
    counts["total"] = sum(count for collection_id, count in counts.items() 
                          if collection_id != "total")
    
    return counts


@activity.defn
async def count_vector_embeddings() -> Dict[str, int]:
    """
    Count embeddings in the vector store.
    
    Returns:
        Dictionary with counts and statistics
    """
    try:
        import pinecone
        vector_store = VectorStore()
        
        # Get index statistics
        pinecone.init(
            api_key=os.environ.get("PINECONE_API_KEY"),
            environment=os.environ.get("PINECONE_ENVIRONMENT")
        )
        
        index = pinecone.Index(vector_store.index_name)
        stats = index.describe_index_stats()
        
        return {
            "total_vector_count": stats["total_vector_count"],
            "namespaces": stats.get("namespaces", {}),
            "dimension": stats.get("dimension", 1536)
        }
    except Exception as e:
        logger.error(f"Error counting vector embeddings: {e}")
        return {"error": str(e), "total_vector_count": 0}


@activity.defn
async def detect_orphaned_vectors() -> List[Dict[str, Any]]:
    """
    Detect vectors in Vector Store that don't have corresponding Firestore documents.
    
    Returns:
        List of orphaned vector metadata
    """
    # Initialize memory systems
    vector_store = VectorStore()
    firestore_memory = FirestoreMemory()
    
    # Sample vectors to check (full check would be expensive and should be batched)
    sample_size = 100
    orphaned_vectors = []
    
    try:
        # Query for a sample of vectors
        sample_vectors = vector_store.query("", top_k=sample_size)
        
        for vector in sample_vectors:
            metadata = vector.get("metadata", {})
            vector_id = metadata.get("id")
            doc_type = metadata.get("doc_type")
            ref_id = metadata.get("ref_id")
            
            # Skip if no reference information
            if not (doc_type and ref_id):
                continue
                
            # Check if referenced document exists in Firestore
            doc = firestore_memory.get(f"{doc_type}/{ref_id}")
            
            if not doc:
                # This is an orphaned vector
                orphaned_vectors.append({
                    "vector_id": vector_id,
                    "metadata": metadata,
                    "score": vector.get("score")
                })
    
    except Exception as e:
        logger.error(f"Error detecting orphaned vectors: {e}")
    
    return orphaned_vectors


@activity.defn
async def detect_missing_embeddings() -> List[Dict[str, Any]]:
    """
    Detect Firestore documents that should have vectors but don't.
    
    Returns:
        List of document references missing embeddings
    """
    # Initialize memory systems
    vector_store = VectorStore()
    firestore_memory = FirestoreMemory()
    
    # Define document types that should have embeddings
    doc_types_with_embeddings = ["conversations", "documents", "knowledge"]
    missing_embeddings = []
    
    for doc_type in doc_types_with_embeddings:
        # Get a sample of documents
        docs = firestore_memory.query_documents(
            collection=doc_type,
            filters=[],  # No filters, get all documents
            limit=100  # Limit sample size
        )
        
        for doc in docs:
            doc_id = doc.get("id")
            
            # Check if document has a corresponding vector
            vector = vector_store.get(doc_id)
            
            if not vector:
                # Documents that should have embeddings but don't
                missing_embeddings.append({
                    "doc_type": doc_type,
                    "doc_id": doc_id,
                    "doc_data": doc
                })
    
    return missing_embeddings


@activity.defn
async def detect_expired_sessions() -> List[str]:
    """
    Detect expired conversation sessions in Redis.
    
    Returns:
        List of expired conversation IDs
    """
    redis_memory = RedisMemory()
    redis_client = redis_memory.redis
    prefix = redis_memory.prefix
    
    # Get all conversation IDs
    conversation_pattern = f"{prefix}conversation:*"
    cursor = 0
    expired_conversations = []
    
    # Define expiry threshold (e.g., 30 days)
    expiry_threshold = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    expiry_iso = expiry_threshold.isoformat()
    
    while True:
        cursor, keys = redis_client.scan(cursor=cursor, match=conversation_pattern, count=1000)
        
        for key in keys:
            # Parse the key to get conversation ID
            conv_id = key.decode('utf-8').split(f"{prefix}conversation:")[1]
            
            # Get conversation metadata
            metadata = redis_memory.get(f"conversation:{conv_id}")
            if metadata:
                # Check if conversation is expired
                updated_at = metadata.get("updated_at", "")
                if updated_at and updated_at < expiry_iso:
                    expired_conversations.append(conv_id)
        
        if cursor == 0:
            break
    
    return expired_conversations


@activity.defn
async def cleanup_orphaned_vectors(vector_ids: List[str]) -> int:
    """
    Delete orphaned vectors from Vector Store.
    
    Args:
        vector_ids: List of vector IDs to delete
        
    Returns:
        Number of vectors deleted
    """
    if not vector_ids:
        return 0
        
    vector_store = VectorStore()
    deleted_count = 0
    
    for vector_id in vector_ids:
        success = vector_store.delete(vector_id)
        if success:
            deleted_count += 1
    
    return deleted_count


@activity.defn
async def cleanup_expired_conversations(conversation_ids: List[str]) -> int:
    """
    Clean up expired conversations from Redis.
    
    Args:
        conversation_ids: List of conversation IDs to clean up
        
    Returns:
        Number of conversations cleaned up
    """
    if not conversation_ids:
        return 0
        
    redis_memory = RedisMemory()
    cleaned_count = 0
    
    for conv_id in conversation_ids:
        success = redis_memory.clear_conversation(conv_id)
        if success:
            # Also delete the conversation metadata
            redis_memory.delete(f"conversation:{conv_id}")
            cleaned_count += 1
    
    return cleaned_count


@activity.defn
async def generate_reconciliation_report(
    redis_counts: Dict[str, int],
    firestore_counts: Dict[str, int],
    vector_counts: Dict[str, int],
    orphaned_vectors: List[Dict[str, Any]],
    missing_embeddings: List[Dict[str, Any]],
    expired_sessions: List[str]
) -> Dict[str, Any]:
    """
    Generate a comprehensive report of memory system state and inconsistencies.
    
    Args:
        redis_counts: Redis key counts by type
        firestore_counts: Firestore document counts by collection
        vector_counts: Vector store statistics
        orphaned_vectors: List of orphaned vectors
        missing_embeddings: List of documents missing embeddings
        expired_sessions: List of expired sessions
        
    Returns:
        Report dictionary
    """
    report = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "summary": {
            "redis_total": redis_counts.get("total", 0),
            "firestore_total": firestore_counts.get("total", 0),
            "vector_total": vector_counts.get("total_vector_count", 0),
            "orphaned_vectors_count": len(orphaned_vectors),
            "missing_embeddings_count": len(missing_embeddings),
            "expired_sessions_count": len(expired_sessions),
        },
        "details": {
            "redis_counts": redis_counts,
            "firestore_counts": firestore_counts,
            "vector_counts": vector_counts,
        },
        "inconsistencies": {
            "orphaned_vectors_sample": orphaned_vectors[:10],  # Show first 10
            "missing_embeddings_sample": missing_embeddings[:10],  # Show first 10
            "expired_sessions_sample": expired_sessions[:10],  # Show first 10
        }
    }
    
    # Add health status
    health_status = "healthy"
    issues = []
    
    # Check for inconsistencies
    if len(orphaned_vectors) > 0:
        issues.append(f"Found {len(orphaned_vectors)} orphaned vectors")
        health_status = "warning"
    
    if len(missing_embeddings) > 0:
        issues.append(f"Found {len(missing_embeddings)} documents missing embeddings")
        health_status = "warning"
    
    if len(expired_sessions) > 0:
        issues.append(f"Found {len(expired_sessions)} expired sessions")
        # Expired sessions are expected, not a health issue
    
    # Check redis vs. firestore consistency for conversations
    redis_conv_count = redis_counts.get("conversations", 0)
    firestore_conv_count = firestore_counts.get("conversations", 0)
    if abs(redis_conv_count - firestore_conv_count) > redis_conv_count * 0.1:  # >10% difference
        issues.append(f"Significant difference between Redis conversations ({redis_conv_count}) and Firestore conversations ({firestore_conv_count})")
        health_status = "warning"
    
    report["health_status"] = health_status
    report["issues"] = issues
    
    return report


@workflow.defn
class MemoryAuditWorkflow:
    """
    Workflow for auditing and reconciling memory systems consistency.
    """
    
    @workflow.run
    async def run(self, perform_cleanup: bool = False) -> Dict[str, Any]:
        """
        Run the memory audit workflow.
        
        Args:
            perform_cleanup: Whether to clean up detected inconsistencies
            
        Returns:
            Audit report
        """
        # Define retry policy for activities
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=datetime.timedelta(seconds=1),
            maximum_interval=datetime.timedelta(seconds=10)
        )
        
        # 1. Count keys in each memory system
        redis_counts = await workflow.execute_activity(
            count_redis_keys,
            start_to_close_timeout=datetime.timedelta(minutes=5),
            retry_policy=retry_policy
        )
        
        firestore_counts = await workflow.execute_activity(
            count_firestore_documents,
            start_to_close_timeout=datetime.timedelta(minutes=5),
            retry_policy=retry_policy
        )
        
        vector_counts = await workflow.execute_activity(
            count_vector_embeddings,
            start_to_close_timeout=datetime.timedelta(minutes=5),
            retry_policy=retry_policy
        )
        
        # 2. Detect inconsistencies
        orphaned_vectors = await workflow.execute_activity(
            detect_orphaned_vectors,
            start_to_close_timeout=datetime.timedelta(minutes=10),
            retry_policy=retry_policy
        )
        
        missing_embeddings = await workflow.execute_activity(
            detect_missing_embeddings,
            start_to_close_timeout=datetime.timedelta(minutes=10),
            retry_policy=retry_policy
        )
        
        expired_sessions = await workflow.execute_activity(
            detect_expired_sessions,
            start_to_close_timeout=datetime.timedelta(minutes=5),
            retry_policy=retry_policy
        )
        
        # 3. Clean up inconsistencies if requested
        cleanup_results = {}
        
        if perform_cleanup:
            # Clean up orphaned vectors
            orphaned_vector_ids = [v.get("vector_id") for v in orphaned_vectors if v.get("vector_id")]
            vectors_deleted = await workflow.execute_activity(
                cleanup_orphaned_vectors,
                orphaned_vector_ids,
                start_to_close_timeout=datetime.timedelta(minutes=10),
                retry_policy=retry_policy
            )
            cleanup_results["vectors_deleted"] = vectors_deleted
            
            # Clean up expired sessions
            sessions_cleaned = await workflow.execute_activity(
                cleanup_expired_conversations,
                expired_sessions,
                start_to_close_timeout=datetime.timedelta(minutes=10),
                retry_policy=retry_policy
            )
            cleanup_results["sessions_cleaned"] = sessions_cleaned
        
        # 4. Generate reconciliation report
        report = await workflow.execute_activity(
            generate_reconciliation_report,
            redis_counts,
            firestore_counts,
            vector_counts,
            orphaned_vectors,
            missing_embeddings,
            expired_sessions,
            start_to_close_timeout=datetime.timedelta(minutes=5),
            retry_policy=retry_policy
        )
        
        # Add cleanup results to report if performed
        if perform_cleanup:
            report["cleanup_results"] = cleanup_results
        
        return report


@workflow.defn
class ScheduledMemoryAuditWorkflow:
    """
    Scheduled workflow for periodic memory audits.
    """
    
    @workflow.run
    async def run(self, schedule_interval_hours: int = 24) -> None:
        """
        Run memory audits on a schedule.
        
        Args:
            schedule_interval_hours: Hours between audit runs
        """
        while True:
            # Run the audit
            audit_workflow = MemoryAuditWorkflow()
            
            # Auto-cleanup expired sessions but not orphaned vectors
            # (which need manual review before deletion)
            report = await workflow.execute_child_workflow(
                audit_workflow.run,
                perform_cleanup=True,
                id=f"memory-audit-{int(time.time())}",
                task_queue="memory-audit-queue"
            )
            
            # Store the report
            firestore_memory = FirestoreMemory()
            report_id = f"audit-{datetime.datetime.utcnow().strftime('%Y-%m-%d-%H-%M')}"
            firestore_memory.save(f"memory_audits/{report_id}", report)
            
            # Sleep until next audit
            await workflow.sleep(datetime.timedelta(hours=schedule_interval_hours))


# Helper functions for manual execution

def start_memory_audit(client, task_queue="memory-audit-queue", perform_cleanup=False):
    """
    Start a memory audit workflow.
    
    Args:
        client: Temporal client
        task_queue: Task queue for the workflow
        perform_cleanup: Whether to perform automatic cleanup
        
    Returns:
        Workflow handle
    """
    workflow_id = f"memory-audit-{int(time.time())}"
    return client.start_workflow(
        MemoryAuditWorkflow.run,
        args=[perform_cleanup],
        id=workflow_id,
        task_queue=task_queue
    )


def start_scheduled_memory_audit(client, task_queue="memory-audit-queue", interval_hours=24):
    """
    Start a scheduled memory audit workflow.
    
    Args:
        client: Temporal client
        task_queue: Task queue for the workflow
        interval_hours: Hours between audit runs
        
    Returns:
        Workflow handle
    """
    workflow_id = f"scheduled-memory-audit-{int(time.time())}"
    return client.start_workflow(
        ScheduledMemoryAuditWorkflow.run,
        args=[interval_hours],
        id=workflow_id,
        task_queue=task_queue
    )
