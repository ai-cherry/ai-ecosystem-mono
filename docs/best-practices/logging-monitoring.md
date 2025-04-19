# Logging and Monitoring Best Practices

This document outlines the best practices for logging and monitoring in the AI Ecosystem.

## Structured Logging

### Overview

Structured logging ensures that log data is machine-readable and easy to query. This is crucial for effective monitoring and debugging.

### Implementation

#### Setting Up Structured Logging

```python
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

class StructuredLogFormatter(logging.Formatter):
    """Formatter for structured JSON logs."""
    
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "path": record.pathname,
            "line": record.lineno,
        }
        
        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
            }
        
        # Add extra fields if available
        if hasattr(record, 'extra') and record.extra:
            log_data.update(record.extra)
            
        return json.dumps(log_data)

def setup_logging(service_name: str, level: int = logging.INFO) -> None:
    """Set up structured logging for the service.
    
    Args:
        service_name: Name of the service for log identification
        level: Logging level (default: INFO)
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    
    # Create console handler with structured formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredLogFormatter(service_name))
    root_logger.addHandler(handler)
    
    # Suppress overly verbose logs from libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google.auth").setLevel(logging.WARNING)
```

#### Using Structured Logging

```python
import logging
from uuid import uuid4
from contextvars import ContextVar

# Context variable to track request ID across async operations
request_id: ContextVar[str] = ContextVar('request_id', default='')

class LoggingMiddleware:
    """FastAPI middleware to add request context to logs."""
    
    async def __call__(self, request: Request, call_next):
        # Generate or extract request ID
        req_id = request.headers.get('X-Request-ID', str(uuid4()))
        request_id.set(req_id)
        
        # Add response headers
        response = await call_next(request)
        response.headers['X-Request-ID'] = req_id
        
        return response

def get_logger(name: str):
    """Get a logger with request context capability."""
    logger = logging.getLogger(name)
    
    # Add methods to include context
    original_debug = logger.debug
    original_info = logger.info
    original_warning = logger.warning
    original_error = logger.error
    
    def debug_with_context(msg: str, *args, **kwargs):
        return original_debug(msg, *args, extra={"request_id": request_id.get(), **kwargs.get("extra", {})})
    
    def info_with_context(msg: str, *args, **kwargs):
        return original_info(msg, *args, extra={"request_id": request_id.get(), **kwargs.get("extra", {})})
    
    def warning_with_context(msg: str, *args, **kwargs):
        return original_warning(msg, *args, extra={"request_id": request_id.get(), **kwargs.get("extra", {})})
    
    def error_with_context(msg: str, *args, **kwargs):
        return original_error(msg, *args, extra={"request_id": request_id.get(), **kwargs.get("extra", {})})
    
    logger.debug = debug_with_context
    logger.info = info_with_context
    logger.warning = warning_with_context
    logger.error = error_with_context
    
    return logger
```

### Example Usage

```python
# In main.py or startup
setup_logging("orchestrator")
app.add_middleware(LoggingMiddleware)

# In a FastAPI endpoint
from fastapi import APIRouter, Depends
from .logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.post("/process")
async def process_request(request: ProcessRequest):
    logger.info(
        f"Processing request", 
        extra={"user_id": request.user_id, "input_length": len(request.input)}
    )
    
    try:
        # Process the request
        result = await process_user_input(request)
        
        logger.info(
            f"Request processed successfully",
            extra={"duration_ms": calculate_duration(), "tokens_used": result.token_count}
        )
        
        return result
    except Exception as e:
        logger.error(
            f"Error processing request: {str(e)}",
            exc_info=True,
            extra={"error_type": type(e).__name__}
        )
        raise
```

## Log Levels and Content

### When to Use Each Log Level

| Level | Usage | Examples |
|-------|-------|----------|
| **DEBUG** | Detailed information for debugging | Function parameters, intermediate results, cache hits/misses |
| **INFO** | Confirmation that things are working | Request received, external API called, task completed |
| **WARNING** | Something unexpected, but not an error | Deprecated feature used, retry attempted, slow response time |
| **ERROR** | Something failed, but application can continue | API call failed, database connection error |
| **CRITICAL** | Application cannot continue | Unrecoverable error, cannot start service |

### What to Log

#### Always Include

1. **Timestamp** (ISO-8601 format)
2. **Service/Component Name**
3. **Log Level**
4. **Message**
5. **Request ID** (for tracing)

#### Contextual Information

1. **User ID** (if applicable)
2. **Endpoint/Operation**
3. **Performance Metrics** (duration, resources used)
4. **Resource Identifiers** (conversation IDs, document IDs)

#### Do Not Log

1. **Passwords or API Keys**
2. **Personally Identifiable Information (PII)**
3. **Sensitive Business Data**
4. **Complete Request/Response Bodies** (log size & sensitive data concerns)

## Monitoring

### Key Metrics to Monitor

#### System Metrics

1. **Cloud Run Metrics**
   - Instance count
   - CPU utilization
   - Memory usage
   - Request latency
   - Error rates

2. **Database Metrics**
   - Firestore read/write operations
   - Redis memory usage and hit/miss ratios
   - Vector DB search latency and index size

#### Application Metrics

1. **User Activity**
   - Requests per minute
   - Active users
   - Average session duration

2. **AI Model Performance**
   - Token usage
   - Model response time
   - Rate limiting status

3. **Memory Service Usage**
   - Cache hit ratio
   - Vector search queries per second
   - Document retrieval time

### Setting Up Alerts

Configure alerts for the following conditions:

1. **Error Rate Threshold**
   - Alert when error rate exceeds 1% of requests
   - Critical alert at 5% of requests

2. **Latency Thresholds**
   - P95 latency > 2000ms (warning)
   - P95 latency > 5000ms (critical)

3. **Resource Utilization**
   - CPU usage > 80% for 5 minutes
   - Memory usage > 85% for 5 minutes

4. **Service Health**
   - Service unavailable
   - Database unavailable
   - Consecutive failure count > 5

## Integration with GCP

### Cloud Logging

The Google Cloud Platform provides built-in logging capabilities. When running on Cloud Run, logs written to stdout/stderr are automatically collected.

#### Viewing Logs

```bash
# View logs for a specific Cloud Run service
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ai-orchestrator" --limit=10

# Filter logs by severity
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=10

# Filter logs by request ID
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.request_id=abc-123" --limit=10
```

### Cloud Monitoring

Set up custom dashboards in Cloud Monitoring to visualize:

1. **Request Volume and Latency**
2. **Error Rates**
3. **Resource Utilization**
4. **Cost Metrics**

## Best Practices Summary

1. **Use Structured Logging**
   - Emit JSON-formatted logs
   - Include context and request IDs
   - Use appropriate log levels

2. **Monitor Key Metrics**
   - System health and performance
   - Application-specific metrics
   - User activity and experience

3. **Set Up Alerting**
   - Define clear thresholds
   - Reduce false positives
   - Ensure alerts are actionable

4. **Implement Distributed Tracing**
   - Track requests across services
   - Identify bottlenecks
   - Debug complex issues

5. **Review Logs Regularly**
   - Look for patterns and anomalies
   - Use logs to improve the system
   - Refine logging based on needs
