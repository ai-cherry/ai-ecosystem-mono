# Error Handling Best Practices

This document outlines the best practices for error handling in the AI Ecosystem.

## Principles of Good Error Handling

1. **Graceful Degradation**: System should continue functioning even when components fail
2. **Informative Messages**: Error messages should help identify and fix the problem
3. **Appropriate Recovery**: Different errors require different recovery strategies
4. **Security Consciousness**: Errors shouldn't expose sensitive information
5. **Observability**: Errors should be logged and monitored

## Implementation in FastAPI

### Global Exception Handler

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

class BaseAPIException(Exception):
    """Base exception for API errors."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        error_code: str = "internal_error",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

# Specific exception types
class ResourceNotFoundException(BaseAPIException):
    """Exception raised when a requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        super().__init__(
            message=f"{resource_type} with ID {resource_id} not found",
            status_code=404,
            error_code="resource_not_found",
            details={"resource_type": resource_type, "resource_id": resource_id, **kwargs}
        )

class ValidationException(BaseAPIException):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field_errors: Dict[str, str], **kwargs):
        super().__init__(
            message=message,
            status_code=400,
            error_code="validation_error",
            details={"field_errors": field_errors, **kwargs}
        )

class ExternalServiceException(BaseAPIException):
    """Exception raised when an external service fails."""
    
    def __init__(self, service_name: str, message: str, **kwargs):
        super().__init__(
            message=f"Error from external service {service_name}: {message}",
            status_code=502,
            error_code="external_service_error",
            details={"service_name": service_name, **kwargs}
        )

class RateLimitException(BaseAPIException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, limit: int, reset_after: int, **kwargs):
        super().__init__(
            message=f"Rate limit exceeded. Try again after {reset_after} seconds",
            status_code=429,
            error_code="rate_limit_exceeded",
            details={"limit": limit, "reset_after": reset_after, **kwargs}
        )

# Global exception handlers
@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    """Handle custom API exceptions."""
    logger.error(
        f"API Exception: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "error_code": exc.error_code,
            "details": exc.details,
            "path": request.url.path
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    field_errors = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        field_errors[field] = error["msg"]
    
    logger.warning(
        "Request validation error",
        extra={
            "status_code": 400,
            "error_code": "validation_error",
            "field_errors": field_errors,
            "path": request.url.path
        }
    )
    
    return JSONResponse(
        status_code=400,
        content={
            "error": True,
            "message": "Request validation error",
            "error_code": "validation_error",
            "details": {"field_errors": field_errors}
        }
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions."""
    logger.exception(
        f"Unhandled exception: {str(exc)}",
        extra={"path": request.url.path}
    )
    
    # In production, don't return the actual error message to prevent info leakage
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "An unexpected error occurred",
            "error_code": "internal_error"
        }
    )
```

### Using Custom Exceptions in Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from .exceptions import ResourceNotFoundException, ExternalServiceException

router = APIRouter()

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    try:
        # Try to get conversation from Firestore
        conversation = await firestore.get_conversation(conversation_id)
        
        if not conversation:
            raise ResourceNotFoundException(
                resource_type="Conversation",
                resource_id=conversation_id
            )
        
        return conversation
    except FirestoreError as e:
        raise ExternalServiceException(
            service_name="Firestore",
            message=str(e),
            operation="get_conversation"
        )
```

## Error Handling for External Services

### Pattern: Circuit Breaker

Implement a circuit breaker pattern to prevent cascading failures when external services are down.

```python
import time
from functools import wraps
from typing import Callable, TypeVar, Any

T = TypeVar('T')

class CircuitBreaker:
    """Circuit breaker implementation for external service calls."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        timeout: int = 10
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.timeout = timeout
        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.last_failure_time = 0
    
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            if self.state == "OPEN":
                # Check if recovery timeout has elapsed
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF-OPEN"
                else:
                    raise ExternalServiceException(
                        service_name=func.__name__,
                        message="Service is currently unavailable",
                        circuit_state=self.state
                    )
            
            try:
                # Set a timeout for the function call
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.timeout
                )
                
                # Reset circuit if it was half-open
                if self.state == "HALF-OPEN":
                    self.state = "CLOSED"
                    self.failures = 0
                
                return result
            except (asyncio.TimeoutError, Exception) as e:
                self.failures += 1
                self.last_failure_time = time.time()
                
                # Open circuit if failure threshold is reached
                if self.failures >= self.failure_threshold:
                    self.state = "OPEN"
                
                # Re-raise the exception
                if isinstance(e, asyncio.TimeoutError):
                    raise ExternalServiceException(
                        service_name=func.__name__,
                        message="Service timed out",
                        timeout=self.timeout
                    )
                else:
                    raise ExternalServiceException(
                        service_name=func.__name__,
                        message=str(e),
                        original_error=type(e).__name__
                    )
        
        return wrapper
```

### Using the Circuit Breaker

```python
from .circuit_breaker import CircuitBreaker

# Apply circuit breaker to external service calls
@CircuitBreaker(failure_threshold=3, recovery_timeout=60)
async def call_llm_service(prompt: str, model: str) -> str:
    # Make API call to LLM service
    response = await openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
```

## Error Handling with Temporal Workflows

Temporal provides built-in error handling and retry mechanics, which should be utilized for reliable background processing.

```python
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from datetime import timedelta

# Define a retry policy for activities
default_retry_policy = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=5,
    non_retryable_error_types=["ValidationException"]
)

# Activity with retry policy
@activity.defn(retry_policy=default_retry_policy)
async def process_document(document_id: str) -> dict:
    # Process document, with automatic retries on failure
    try:
        document = await firestore.get_document("documents", document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Process the document
        processed = await process_content(document)
        
        # Save the processed document
        await firestore.save_document("processed_documents", processed)
        
        return processed
    except Exception as e:
        # Log the error for observability
        logging.error(f"Error processing document {document_id}: {str(e)}")
        # Re-raise to trigger retry based on policy
        raise

# Workflow that uses activities
@workflow.defn
class DocumentProcessingWorkflow:
    @workflow.run
    async def run(self, document_id: str) -> dict:
        try:
            # Execute the activity with retry policy
            result = await workflow.execute_activity(
                process_document,
                document_id,
                start_to_close_timeout=timedelta(minutes=10)
            )
            return result
        except Exception as e:
            # Handle workflow-level failures
            workflow.logger.error(f"Workflow failed: {str(e)}")
            # Perform compensating actions if needed
            await workflow.execute_activity(
                notify_admin_of_failure,
                document_id,
                str(e),
                start_to_close_timeout=timedelta(minutes=1)
            )
            raise
```

## Graceful Degradation

Design the system to gracefully degrade when components fail:

```python
async def get_conversation_with_fallbacks(conversation_id: str):
    """Get conversation with fallback mechanisms."""
    try:
        # Try Redis first (fastest)
        conversation = await redis_memory.get_conversation(conversation_id)
        if conversation:
            return conversation
    except Exception as e:
        logger.warning(f"Redis read failed: {str(e)}")
        # Continue to fallback
    
    try:
        # Fallback to Firestore
        conversation = await firestore_memory.get_conversation(conversation_id)
        if conversation:
            # Update Redis cache for next time
            try:
                await redis_memory.save_conversation(conversation_id, conversation)
            except Exception as redis_err:
                logger.warning(f"Redis cache update failed: {str(redis_err)}")
            return conversation
    except Exception as e:
        logger.error(f"Firestore read failed: {str(e)}")
        # Final fallback: return empty conversation
        return {"messages": [], "metadata": {"recovered": False}}
    
    return {"messages": [], "metadata": {"empty": True}}
```

## Input Validation

Use Pydantic for robust input validation:

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import re

class ProcessRequest(BaseModel):
    """Request model for processing user input."""
    
    user_id: str = Field(..., min_length=3, max_length=50)
    conversation_id: Optional[str] = Field(None, min_length=3, max_length=50)
    input: str = Field(..., min_length=1, max_length=4000)
    
    @validator('user_id')
    def user_id_must_be_valid(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('user_id must contain only alphanumeric characters, underscores, and hyphens')
        return v
```

## Error Monitoring and Analysis

1. **Set up alerts for errors**:
   - Create alert policies for error spikes
   - Set up notifications for critical errors

2. **Analyze error trends**:
   - Track error rates over time
   - Identify most common error types
   - Correlate errors with system changes or traffic patterns

3. **Automate error grouping**:
   - Group similar errors together
   - Focus on new or increasing error types

## Best Practices Summary

1. **Use Custom Exceptions**:
   - Create a hierarchy of exception classes
   - Include meaningful error codes and messages
   - Attach contextual information

2. **Implement Graceful Degradation**:
   - Use fallback mechanisms
   - Degrade functionality rather than failing completely
   - Cache results to reduce dependency on external services

3. **Apply Retry Policies**:
   - Use exponential backoff
   - Set reasonable timeout values
   - Distinguish between transient and permanent failures

4. **Validate Inputs**:
   - Use Pydantic for schema validation
   - Apply custom validators for business rules
   - Return clear validation errors

5. **Log and Monitor Errors**:
   - Log errors with context
   - Set up alerts for critical errors
   - Analyze error patterns
