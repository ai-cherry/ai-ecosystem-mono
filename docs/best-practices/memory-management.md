# Memory Management Best Practices

This document outlines the best practices for memory management in the AI Ecosystem.

## Overview

The AI Ecosystem uses three types of memory:

1. **Long-term Memory (Firestore)**: Persistent storage for conversation history and structured data
2. **Short-term Memory (Redis)**: Fast cache for session state and recent context
3. **Vector Memory (Pinecone)**: Storage for embeddings to enable semantic search

## Usage Patterns

### When to Use Each Memory Type

| Memory Type | Use Cases | Characteristics |
|-------------|-----------|-----------------|
| **Firestore** | - Complete conversation logs<br>- User profiles<br>- Agent state<br>- Configuration data | - Durable storage<br>- Structured data<br>- Document-based<br>- High consistency |
| **Redis** | - Current session context<br>- Recent messages<br>- Temporary caching<br>- Rate limiting | - Ultra-fast access<br>- Expirable data<br>- Simple key-value<br>- Low latency |
| **Vector DB** | - Semantic search<br>- Embeddings storage<br>- Knowledge retrieval<br>- Similar content matching | - Similarity search<br>- Embedding-based<br>- Specialized indices<br>- Optimized for vectors |

## Implementation Guidelines

### Firestore Usage

```python
# Example of storing a conversation in Firestore
from shared.memory import FirestoreMemory

firestore = FirestoreMemory()

# Save a user message to conversation history
message_id = firestore.save_message(
    conversation_id="conv-123",
    message={
        "role": "user",
        "content": "What's the weather like today?",
        "timestamp": datetime.utcnow().isoformat()
    },
    user_id="user-456"
)

# Retrieve conversation history
messages = firestore.get_conversation(
    conversation_id="conv-123", 
    limit=10
)
```

### Redis Usage

```python
# Example of caching in Redis
from shared.memory import RedisMemory

redis = RedisMemory()

# Cache a result with TTL
redis.cache_result(
    key="weather:nyc:today",
    value={"temp": 72, "condition": "sunny"},
    ttl=3600  # expires in 1 hour
)

# Get cached result
weather = redis.get_cached_result("weather:nyc:today")
```

### Vector Store Usage

```python
# Example of vector store operations
from shared.memory import VectorStore

vector_store = VectorStore()

# Store text with embedding
doc_id = vector_store.upsert_text(
    text="Python is a high-level programming language.",
    metadata={"category": "programming", "source": "docs"}
)

# Search for similar content
results = vector_store.query(
    query_text="What programming languages are high-level?",
    top_k=3
)
```

## Performance Considerations

### Optimizing Memory Access

1. **Batch Operations**: When possible, batch multiple operations to reduce network overhead
   ```python
   # Instead of multiple single inserts
   for doc in documents:
       vector_store.upsert_text(doc.text, doc.metadata)
   
   # Use batch insertion if available
   vector_store.from_texts([doc.text for doc in documents], [doc.metadata for doc in documents])
   ```

2. **Caching Strategies**:
   - Cache common vector search results in Redis
   - Pre-compute embeddings for frequently accessed content
   - Use tiered caching (in-memory → Redis → Vector DB → Firestore)

3. **Asynchronous Processing**:
   - For non-critical writes, consider async operations
   - Use background tasks for indexing or updating embeddings

## Data Consistency

### Handling Updates Across Multiple Stores

When data is updated, ensure consistency across all memory types:

```python
# When conversation is updated
async def update_conversation(conversation_id: str, new_message: dict):
    # 1. Update Firestore (source of truth)
    message_id = firestore.save_message(conversation_id, new_message)
    
    # 2. Update Redis cache
    redis.save_message(conversation_id, new_message)
    
    # 3. Update vector store for semantic search
    if is_relevant_for_vector_store(new_message):
        doc_id = await vector_store.upsert_text(
            text=new_message["content"],
            metadata={
                "conversation_id": conversation_id,
                "message_id": message_id,
                "timestamp": new_message.get("timestamp")
            }
        )
```

## Monitoring Memory Usage

1. Monitor memory size and growth:
   - Firestore document counts and size
   - Redis memory usage
   - Vector store index size

2. Set up alerts for:
   - Approaching storage limits
   - Slow query performance
   - Cache miss rates

## Error Handling

Implement robust error handling for memory operations:

```python
async def get_with_fallback(key: str):
    try:
        # Try Redis first (fastest)
        result = await redis.get(key)
        if result:
            return result
            
        # Fall back to Firestore
        result = await firestore.get(key)
        if result:
            # Refresh Redis cache
            await redis.save(key, result, ttl=3600)
            return result
            
        return None
    except Exception as e:
        # Log error but don't crash
        logging.error(f"Memory access error: {e}")
        # Fall back to default value if possible
        return get_default_value(key)
```

## Best Practices Summary

1. **Use the Right Store for the Job**:
   - Firestore for durable, structured data
   - Redis for ephemeral, frequent access
   - Vector DB for semantic search

2. **Optimize for Performance**:
   - Cache hot data in Redis
   - Use batch operations
   - Implement async processing

3. **Ensure Data Consistency**:
   - Maintain a single source of truth
   - Use transactions when needed
   - Update all stores when data changes

4. **Handle Errors Gracefully**:
   - Implement fallbacks
   - Log errors
   - Degrade gracefully
