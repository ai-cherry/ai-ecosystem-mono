# Security, Configuration, and Scalability Best Practices

This document outlines the best practices for security, configuration management, and scalability in the AI Ecosystem.

## Secrets Management

### Principles

1. **Never store secrets in code or version control**
2. **Provide least-privilege access to secrets**
3. **Rotate secrets regularly**
4. **Monitor and audit secret access**
5. **Use encryption for all sensitive data**

### Google Cloud Secret Manager

#### Setting Up Secrets

```bash
# Create a new secret
gcloud secrets create openai-api-key --replication-policy="automatic"

# Add a version with the secret value
echo -n "sk-yourapikeyhere" | gcloud secrets versions add openai-api-key --data-file=-

# Grant access to a service account
gcloud secrets add-iam-policy-binding openai-api-key \
    --member="serviceAccount:ai-orchestrator-sa@your-project.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

#### Accessing Secrets in Terraform

```hcl
# Secret definition in Terraform
resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key"
  
  replication {
    user_managed {
      replicas {
        location = "us-central1"
      }
    }
  }
}

# Create a version (populated from Terraform variables)
resource "google_secret_manager_secret_version" "openai_api_key_version" {
  secret = google_secret_manager_secret.openai_api_key.id
  secret_data = var.openai_api_key
}

# Reference in Cloud Run service
resource "google_cloud_run_service" "orchestrator" {
  # ...
  
  template {
    spec {
      containers {
        # ...
        
        env {
          name = "OPENAI_API_KEY"
          value_from {
            secret_key_ref {
              name = google_secret_manager_secret.openai_api_key.secret_id
              key  = "latest"
            }
          }
        }
      }
    }
  }
}
```

#### Accessing Secrets in Python

```python
from google.cloud import secretmanager

def access_secret(project_id, secret_id, version_id="latest"):
    """Access a secret version from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")
```

### Environment Variables for Local Development

For local development, use `.env` files that are not checked into version control:

```bash
# .env.example (checked into version control)
# Template for required environment variables
OPENAI_API_KEY=your_api_key_here
PINECONE_API_KEY=your_api_key_here
REDIS_URL=redis://localhost:6379
GCP_PROJECT_ID=your_project_id

# .env (not checked into version control)
# Actual environment variables with real values
OPENAI_API_KEY=sk-actualkey123
PINECONE_API_KEY=abc123def456
REDIS_URL=redis://localhost:6379
GCP_PROJECT_ID=my-project-123
```

### Secure Access Patterns

```python
from pydantic import BaseSettings, Field
from typing import Optional
import os
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API keys for external services (loaded from environment or Secret Manager)
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    pinecone_api_key: str = Field(..., env="PINECONE_API_KEY")
    
    # Connection strings
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    
    # GCP configuration
    gcp_project_id: Optional[str] = Field(None, env="GCP_PROJECT_ID")
    
    # Feature flags
    enable_vector_search: bool = Field(True, env="ENABLE_VECTOR_SEARCH")
    enable_caching: bool = Field(True, env="ENABLE_CACHING")
    
    # Performance tuning
    max_concurrent_requests: int = Field(50, env="MAX_CONCURRENT_REQUESTS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache()
def get_settings():
    """Get application settings as a cached singleton."""
    return Settings()

# Access settings in application code
settings = get_settings()
openai_api_key = settings.openai_api_key
```

## Configuration Management

### Pydantic for Configuration

Use Pydantic's `BaseSettings` class to manage configuration with validation:

```python
from pydantic import BaseSettings, Field, validator
from typing import List, Optional, Dict, Any
import os
import json

class MemorySettings(BaseSettings):
    """Settings for memory services."""
    
    # Firestore settings
    firestore_project_id: Optional[str] = Field(None, env="FIRESTORE_PROJECT_ID")
    
    # Redis settings
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    redis_ttl: int = Field(3600, env="REDIS_TTL")  # Default TTL in seconds
    
    # Vector store settings
    vector_store_type: str = Field("pinecone", env="VECTOR_STORE_TYPE")
    pinecone_api_key: Optional[str] = Field(None, env="PINECONE_API_KEY")
    pinecone_environment: str = Field("us-west1-gcp", env="PINECONE_ENVIRONMENT")
    pinecone_index_name: str = Field("ai-orchestrator", env="PINECONE_INDEX_NAME")
    
    # Embedding settings
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    embedding_model: str = Field("text-embedding-ada-002", env="EMBEDDING_MODEL")
    
    @validator('vector_store_type')
    def validate_vector_store_type(cls, v):
        allowed = ["pinecone", "weaviate", "firestore"]
        if v not in allowed:
            raise ValueError(f"vector_store_type must be one of {allowed}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

class LLMSettings(BaseSettings):
    """Settings for LLM services."""
    
    # OpenAI settings
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    default_model: str = Field("gpt-4", env="DEFAULT_MODEL")
    temperature: float = Field(0.7, env="TEMPERATURE")
    max_tokens: int = Field(1000, env="MAX_TOKENS")
    
    # Timeout settings
    request_timeout: int = Field(60, env="REQUEST_TIMEOUT")  # seconds
    
    # Rate limiting
    rate_limit_requests: int = Field(60, env="RATE_LIMIT_REQUESTS")  # requests per minute
    
    class Config:
        env_file = ".env"
        case_sensitive = True

class APISettings(BaseSettings):
    """Settings for the API."""
    
    # Server settings
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    debug: bool = Field(False, env="DEBUG")
    
    # CORS settings
    cors_origins: List[str] = Field(["*"], env="CORS_ORIGINS")
    
    # Authentication
    auth_enabled: bool = Field(False, env="AUTH_ENABLED")
    auth_token: Optional[str] = Field(None, env="AUTH_TOKEN")
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_memory_settings():
    """Get memory settings."""
    return MemorySettings()

@lru_cache()
def get_llm_settings():
    """Get LLM settings."""
    return LLMSettings()

@lru_cache()
def get_api_settings():
    """Get API settings."""
    return APISettings()
```

### Environment-Specific Configuration

```python
from enum import Enum
from pydantic import BaseSettings, Field

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class AppSettings(BaseSettings):
    """Application settings with environment-specific configuration."""
    
    # Current environment
    environment: Environment = Field(Environment.DEVELOPMENT, env="ENVIRONMENT")
    
    # Common settings
    service_name: str = Field("ai-orchestrator", env="SERVICE_NAME")
    
    # Environment-specific settings
    @property
    def log_level(self):
        """Get log level based on environment."""
        if self.environment == Environment.DEVELOPMENT:
            return "DEBUG"
        elif self.environment == Environment.STAGING:
            return "INFO"
        else:
            return "WARNING"
    
    @property
    def firestore_emulator_host(self):
        """Get Firestore emulator host for local development."""
        if self.environment == Environment.DEVELOPMENT:
            return os.getenv("FIRESTORE_EMULATOR_HOST", "localhost:8080")
        return None
    
    class Config:
        env_file = f".env.{os.getenv('ENVIRONMENT', 'development').lower()}"
        env_file_encoding = "utf-8"
```

## Scalability

### Stateless Services

Design services to be stateless by externalizing all state to managed services:

```python
@app.post("/process")
async def process_request(request: ProcessRequest):
    """Process a user request."""
    # Don't store state in the service instance
    # Instead, use external services for state management
    
    # Get conversation history from Firestore
    conversation = await firestore_memory.get_conversation(request.conversation_id)
    
    # Process the request with LLM
    response = await llm_service.generate_response(
        prompt=request.input,
        conversation_history=conversation
    )
    
    # Store the updated conversation back to Firestore
    await firestore_memory.save_message(
        conversation_id=request.conversation_id,
        message={
            "role": "user",
            "content": request.input,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    await firestore_memory.save_message(
        conversation_id=request.conversation_id,
        message={
            "role": "assistant",
            "content": response,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    return {"response": response}
```

### Asynchronous Processing

Use asynchronous programming to handle many concurrent requests:

```python
import asyncio
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

async def process_in_background(request_data: dict):
    """Process a request in the background."""
    # Process the request
    # This runs in the background without blocking the response
    result = await compute_intensive_task(request_data)
    
    # Store the result
    await store_result(request_data["id"], result)

@app.post("/async-process")
async def async_process(request: RequestModel, background_tasks: BackgroundTasks):
    """Process a request asynchronously."""
    # Generate a request ID
    request_id = str(uuid.uuid4())
    
    # Store the request for processing
    await store_request(request_id, request.dict())
    
    # Start background processing
    background_tasks.add_task(process_in_background, {
        "id": request_id,
        "data": request.dict()
    })
    
    return {"request_id": request_id, "status": "processing"}

@app.get("/status/{request_id}")
async def get_status(request_id: str):
    """Get the status of an asynchronous request."""
    status = await get_request_status(request_id)
    if status["state"] == "completed":
        result = await get_request_result(request_id)
        return {"status": status, "result": result}
    return {"status": status}
```

### Scaling with Cloud Run

Configure Cloud Run for optimal scaling:

```hcl
resource "google_cloud_run_service" "orchestrator" {
  # ...

  template {
    metadata {
      annotations = {
        # Minimum number of instances (prevents cold starts)
        "autoscaling.knative.dev/minScale" = "1"
        
        # Maximum number of instances (controls costs)
        "autoscaling.knative.dev/maxScale" = "100"
        
        # CPU allocation (always allocate CPU)
        "run.googleapis.com/cpu-throttling" = "false"
        
        # Concurrency (requests per instance)
        "run.googleapis.com/container-concurrency" = "80"
      }
    }
    
    spec {
      containers {
        # Resource limits
        resources {
          limits = {
            cpu    = "1000m"  # 1 vCPU
            memory = "512Mi"  # 512 MB RAM
          }
        }
      }
      
      # Timeout for requests
      timeout_seconds = 300  # 5 minutes
    }
  }
}
```

### Database Scaling Considerations

#### Firestore

- Use appropriate indexing for query patterns
- Distribute writes across different document collections
- Avoid transactions that span multiple document collections

```python
# Example of efficient Firestore indexing
# Create a composite index for a common query pattern
firestore_index = {
  "collectionGroup": "messages",
  "queryScope": "COLLECTION",
  "fields": [
    { "fieldPath": "conversation_id", "order": "ASCENDING" },
    { "fieldPath": "timestamp", "order": "DESCENDING" }
  ]
}

# In Terraform, define the index
resource "google_firestore_index" "messages_by_conversation" {
  collection = "messages"
  
  fields {
    field_path = "conversation_id"
    order      = "ASCENDING"
  }
  
  fields {
    field_path = "timestamp"
    order      = "DESCENDING"
  }
}
```

#### Redis

- Use connection pooling
- Set appropriate key TTLs to manage memory usage
- Consider Redis Cluster for higher throughput

```python
import redis.asyncio as redis
from typing import Optional

class RedisPool:
    """Redis connection pool manager."""
    
    _pool: Optional[redis.ConnectionPool] = None
    
    @classmethod
    async def get_pool(cls, redis_url: str, max_connections: int = 10):
        """Get or create a Redis connection pool."""
        if cls._pool is None:
            cls._pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=max_connections,
                decode_responses=True
            )
        return cls._pool
    
    @classmethod
    async def get_connection(cls, redis_url: str):
        """Get a Redis connection from the pool."""
        pool = await cls.get_pool(redis_url)
        return redis.Redis(connection_pool=pool)
```

#### Vector Database

- Pre-compute and batch index embeddings
- Use dimensionality reduction techniques for large embedding models
- Cache frequently accessed vector search results in Redis

```python
# Example of efficient vector storage with batching
async def batch_upsert_texts(texts: List[str], metadatas: List[dict] = None):
    """Batch upsert texts to vector store."""
    # Generate embeddings in batches
    embeddings = []
    batch_size = 100
    
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_embeddings = await generate_embeddings(batch_texts)
        embeddings.extend(batch_embeddings)
    
    # Upsert to vector store
    await vector_store.upsert_vectors(embeddings, texts, metadatas)
```

## Performance Optimization

### Caching Strategies

Implement multiple layers of caching:

```python
from functools import lru_cache
import hashlib
import json

# In-memory cache for frequently used functions
@lru_cache(maxsize=1000)
def compute_expensive_result(input_value: str) -> str:
    # Expensive computation
    return result

# Redis cache for distributed caching
async def get_cached_result(key: str, compute_func, ttl: int = 3600):
    """Get a result from cache or compute it."""
    # Try to get from Redis
    redis_client = await RedisPool.get_connection(settings.redis_url)
    cached = await redis_client.get(key)
    
    if cached:
        return json.loads(cached)
    
    # Compute the result
    result = await compute_func()
    
    # Cache the result
    await redis_client.set(key, json.dumps(result), ex=ttl)
    
    return result

# Helper for generating cache keys
def make_cache_key(*args, **kwargs) -> str:
    """Generate a cache key from arguments."""
    key_dict = {"args": args, "kwargs": kwargs}
    key_str = json.dumps(key_dict, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()
```

### Optimizing API Calls

```python
import time
import asyncio
from typing import Dict, List, Any, Callable, TypeVar

T = TypeVar('T')

class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.call_timestamps = []
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        
        # Remove timestamps older than 1 minute
        self.call_timestamps = [t for t in self.call_timestamps if now - t < 60]
        
        # If we've reached the limit, wait
        if len(self.call_timestamps) >= self.calls_per_minute:
            oldest = min(self.call_timestamps)
            wait_time = 60 - (now - oldest)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        # Add current timestamp
        self.call_timestamps.append(time.time())

# Apply rate limiting to API calls
rate_limiter = RateLimiter(calls_per_minute=60)

async def call_api_with_rate_limiting(func: Callable[..., T], *args, **kwargs) -> T:
    """Call an API function with rate limiting."""
    await rate_limiter.wait_if_needed()
    return await func(*args, **kwargs)
```

## Security Best Practices Summary

1. **Use Secret Manager for Sensitive Values**:
   - API keys
   - Database credentials
   - Authentication tokens

2. **Validate and Sanitize All Input**:
   - Use Pydantic for validation
   - Escape user input before using in queries
   - Implement rate limiting for APIs

3. **Implement Authentication and Authorization**:
   - Use industry standard auth protocols
   - Apply least privilege principle
   - Audit access regularly

4. **Secure Network Communications**:
   - Use HTTPS for all endpoints
   - Use VPC connectors for internal communication
   - Implement appropriate firewall rules

## Configuration Best Practices Summary

1. **Centralize Configuration with Pydantic**:
   - Define clear schemas for all settings
   - Validate configuration values
   - Cache settings for performance

2. **Support Multiple Environments**:
   - Development
   - Staging 
   - Production

3. **Use Environment Variables for Configuration**:
   - Follow 12-factor app principles
   - Provide templates for required variables
   - Use .env files for local development

## Scalability Best Practices Summary

1. **Design Stateless Services**:
   - Store all state in external services
   - Make services horizontally scalable
   - Avoid instance-specific data

2. **Implement Asynchronous Processing**:
   - Use background tasks for long-running operations
   - Implement queuing for high-throughput scenarios
   - Allow for parallel processing

3. **Optimize Resource Usage**:
   - Implement multi-level caching
   - Use connection pooling
   - Apply rate limiting
