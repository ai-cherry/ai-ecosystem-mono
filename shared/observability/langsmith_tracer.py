"""
LangSmith tracer for monitoring and debugging LLM operations.

This module provides integration with LangSmith for tracing LLM calls,
enabling detailed monitoring, debugging, and cost tracking for AI operations.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Union

# Conditional import for LangSmith
try:
    from langsmith import Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

from shared.config import observability_settings

# Initialize logger
logger = logging.getLogger(__name__)


class LangSmithTracer:
    """Middleware for tracing LLM operations to LangSmith."""
    
    def __init__(self, client_id: Optional[str] = None):
        """
        Initialize the LangSmith tracer.
        
        Args:
            client_id: Optional client identifier for tenant tracking
        """
        self.enabled = observability_settings.LANGSMITH_ENABLED
        self.project = observability_settings.LANGSMITH_PROJECT
        self.client_id = client_id or str(uuid.uuid4())
        
        # Initialize LangSmith client if available and enabled
        self.client = None
        if self.enabled and LANGSMITH_AVAILABLE:
            try:
                self.client = Client(
                    api_key=observability_settings.LANGSMITH_API_KEY
                )
                logger.info(f"LangSmith tracing enabled for project: {self.project}")
            except Exception as e:
                logger.error(f"Error initializing LangSmith client: {str(e)}")
                self.enabled = False
    
    async def trace_llm_call(
        self, 
        prompt: str,
        response: str,
        model: str,
        tokens_used: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trace an LLM call to LangSmith.
        
        Args:
            prompt: The prompt sent to the model
            response: The response received from the model
            model: Model identifier (e.g., "gpt-4")
            tokens_used: Total tokens consumed
            metadata: Additional context about the call
            
        Returns:
            Dictionary with trace information
        """
        if not self.enabled:
            return {"enabled": False, "run_id": None}
        
        metadata = metadata or {}
        run_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Enrich metadata with standard fields
        enriched_metadata = {
            "client_id": self.client_id,
            "model": model,
            "tokens": tokens_used,
            "timestamp": start_time,
            "cost_estimate": self._estimate_cost(model, tokens_used),
            **metadata
        }
        
        try:
            if self.client:
                # Create run in LangSmith
                # TODO: Verify LangSmith API methods when implementing
                # The actual method may be different depending on the LangSmith version
                # pylint: disable=no-member
                # This is a placeholder - the actual API might return a run object
                self.client.create_run(
                    name=metadata.get("operation_name", "llm_call"),
                    run_type="llm",
                    inputs={"prompt": prompt},
                    outputs={"response": response},
                    runtime={
                        "total_tokens": tokens_used,
                        "model": model
                    },
                    extra=enriched_metadata,
                    project_name=self.project,
                    run_id=run_id
                )
                
                logger.debug(f"LangSmith trace recorded: {run_id}")
                return {
                    "enabled": True,
                    "run_id": run_id,
                    "success": True
                }
            
        except Exception as e:
            logger.error(f"Error recording LangSmith trace: {str(e)}")
            
        return {
            "enabled": True,
            "run_id": run_id,
            "success": False,
            "error": "Failed to record trace"
        }
    
    async def start_trace(
        self,
        operation_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start a new trace for a complex operation (e.g., agent execution).
        
        Args:
            operation_name: Name of the operation being traced
            metadata: Additional context about the operation
            
        Returns:
            Dictionary with trace context for child spans
        """
        if not self.enabled:
            return {"enabled": False, "run_id": None}
        
        metadata = metadata or {}
        run_id = str(uuid.uuid4())
        
        try:
            if self.client:
                # Create parent run in LangSmith
                # TODO: Verify LangSmith API methods when implementing
                # The actual method may be different depending on the LangSmith version
                # pylint: disable=no-member
                self.client.create_run(
                    name=operation_name,
                    run_type="chain",
                    inputs=metadata.get("inputs", {}),
                    extra={
                        "client_id": self.client_id,
                        "start_time": time.time(),
                        **metadata
                    },
                    project_name=self.project,
                    run_id=run_id
                )
                
                logger.debug(f"Started LangSmith trace: {run_id} for {operation_name}")
                return {
                    "enabled": True,
                    "run_id": run_id,
                    "operation_name": operation_name,
                    "start_time": time.time()
                }
        except Exception as e:
            logger.error(f"Error starting LangSmith trace: {str(e)}")
        
        return {
            "enabled": True,
            "run_id": run_id,
            "operation_name": operation_name,
            "start_time": time.time(),
            "error": "Failed to start trace"
        }
    
    async def end_trace(
        self,
        trace_context: Dict[str, Any],
        result: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        End a previously started trace.
        
        Args:
            trace_context: Context from start_trace
            result: Final result of the operation
            metadata: Additional context to add
        """
        if not self.enabled or not trace_context.get("enabled", False):
            return
        
        run_id = trace_context.get("run_id")
        if not run_id:
            logger.warning("Cannot end trace: missing run_id in trace context")
            return
        
        metadata = metadata or {}
        end_time = time.time()
        duration = end_time - trace_context.get("start_time", end_time)
        
        try:
            if self.client:
                # Update the run with results
                # TODO: Verify LangSmith API methods when implementing
                # The actual method may be different depending on the LangSmith version
                # pylint: disable=no-member
                self.client.update_run(
                    run_id=run_id,
                    outputs={"result": result},
                    end_time=end_time,
                    extra={
                        "duration": duration,
                        **metadata
                    }
                )
                
                logger.debug(f"Ended LangSmith trace: {run_id} in {duration:.2f}s")
        except Exception as e:
            logger.error(f"Error ending LangSmith trace: {str(e)}")
    
    def _estimate_cost(self, model: str, tokens: int) -> float:
        """
        Estimate the cost of an LLM call based on model and tokens.
        
        Args:
            model: Model identifier
            tokens: Number of tokens used
            
        Returns:
            Estimated cost in USD
        """
        # Basic cost model - should be expanded with actual pricing
        cost_per_1k_tokens = {
            "gpt-3.5-turbo": 0.002,
            "gpt-4": 0.06,
            "gpt-4o": 0.01,
            "claude-3-opus": 0.15,
            "claude-3.5-sonnet": 0.03
        }
        
        base_cost = cost_per_1k_tokens.get(model, 0.01)  # Default if unknown
        return (tokens / 1000) * base_cost


# Singleton instance for global use
tracer = LangSmithTracer()


# Decorator for tracing function calls
def trace_llm(operation_name: str = None):
    """
    Decorator to trace LLM operations.
    
    Args:
        operation_name: Optional name for the operation
        
    Returns:
        Decorated function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if not tracer.enabled:
                return await func(*args, **kwargs)
            
            # Extract context from kwargs or use defaults
            context = {
                "operation_name": operation_name or func.__name__,
                "args": str(args),
                "kwargs": {k: v for k, v in kwargs.items() if k not in ["prompt", "api_key"]}
            }
            
            # Start timing
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # Extract info from result based on common response structures
                if hasattr(result, "usage") and hasattr(result.usage, "total_tokens"):
                    tokens_used = result.usage.total_tokens
                else:
                    tokens_used = 0
                
                if hasattr(result, "choices") and hasattr(result.choices[0], "message"):
                    response_text = result.choices[0].message.content
                elif hasattr(result, "content"):
                    response_text = result.content
                else:
                    response_text = str(result)
                
                # Determine model from inputs
                model = kwargs.get("model", "unknown")
                
                # Determine prompt
                prompt = kwargs.get("prompt", "")
                if not prompt and len(args) > 0:
                    prompt = str(args[0])
                
                # Record trace
                await tracer.trace_llm_call(
                    prompt=prompt,
                    response=response_text,
                    model=model,
                    tokens_used=tokens_used,
                    metadata={
                        "duration": time.time() - start_time,
                        **context
                    }
                )
                
                return result
            except Exception as e:
                # Record error in trace
                await tracer.trace_llm_call(
                    prompt=kwargs.get("prompt", str(args[0]) if args else ""),
                    response=f"ERROR: {str(e)}",
                    model=kwargs.get("model", "unknown"),
                    tokens_used=0,
                    metadata={
                        "duration": time.time() - start_time,
                        "error": str(e),
                        **context
                    }
                )
                raise
                
        return wrapper
    return decorator
