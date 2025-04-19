"""
Base implementation of LLM services.

This module provides base implementations of the LLM service interfaces
with common functionality shared across different LLM providers.
"""
import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Type

# Handle different langchain versions gracefully
try:
    from langchain.callbacks.manager import CallbackManager
    from langchain.callbacks.tracers import LangChainTracer
except ImportError:
    # Fallback for older langchain versions
    try:
        from langchain.callbacks import CallbackManager
        from langchain.callbacks import LangChainTracer
    except ImportError:
        # Create stub classes if importing fails
        class CallbackManager:
            def __init__(self, handlers=None):
                self.handlers = handlers or []
                
        class LangChainTracer:
            def __init__(self, project_name="default"):
                self.project_name = project_name

from orchestrator.app.services.llm.interfaces import (
    BaseLLMService,
    LLMTestingCapability,
    LLMTraceableCapability
)


class BaseLLMImplementation(BaseLLMService):
    """Base implementation for LLM services with common utility methods."""
    
    def __init__(
        self, 
        model_name: str,
        temperature: float = 0.7,
    ):
        """
        Initialize base LLM implementation.
        
        Args:
            model_name: The name of the LLM model to use
            temperature: Controls randomness (0=deterministic, 1=creative)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.callback_manager = CallbackManager([])
    
    def _format_messages(self, input_data: Union[str, Dict[str, Any], List[Any]]) -> List[Any]:
        """
        Convert input to a standardized message format.
        
        Args:
            input_data: Raw input in various formats
            
        Returns:
            List of messages in a standardized format
        """
        # This method should be implemented by each provider-specific class
        # as message formats may differ between providers
        raise NotImplementedError("Must be implemented by provider-specific classes")
    
    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Error response dictionary
        """
        return {
            "error": str(error),
            "content": "Error processing request",
            "metadata": {
                "model_name": getattr(self, "model_name", "unknown"),
                "error_type": error.__class__.__name__
            }
        }


class TestingCapabilityMixin(LLMTestingCapability):
    """Mixin to add testing capabilities to LLM services."""
    
    def __init__(self, snapshot_dir: str = "tests/snapshots/llm_responses"):
        """
        Initialize testing capabilities.
        
        Args:
            snapshot_dir: Directory to store snapshots
        """
        self.seed = None
        self.snapshot_mode = False
        self.snapshot_dir = Path(snapshot_dir)
    
    def enable_deterministic_mode(self, seed: int) -> None:
        """
        Enable deterministic mode with a specific seed.
        
        Args:
            seed: Seed value for deterministic outputs
        """
        self.seed = seed
        # Child classes should apply this seed to their LLM implementations
    
    def enable_snapshot_mode(self, snapshot_dir: Optional[str] = None) -> None:
        """
        Enable snapshot testing mode.
        
        Args:
            snapshot_dir: Optional directory to store snapshots
        """
        self.snapshot_mode = True
        if snapshot_dir:
            self.snapshot_dir = Path(snapshot_dir)
            
        # Create snapshot directory if it doesn't exist
        if not self.snapshot_dir.exists():
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    def _compute_input_hash(self, messages: List[Any]) -> str:
        """
        Compute hash of input messages for snapshot matching.
        
        Args:
            messages: The input messages
            
        Returns:
            Hash string for the input
        """
        # Create a serializable representation of messages
        if hasattr(messages[0], "__class__") and hasattr(messages[0], "content"):
            # This looks like LangChain messages
            serialized = json.dumps([{
                "type": msg.__class__.__name__,
                "content": msg.content
            } for msg in messages], sort_keys=True)
        else:
            # Generic serialization fallback
            serialized = json.dumps(messages, sort_keys=True)
            
        return hashlib.md5(serialized.encode()).hexdigest()
    
    def _get_snapshot_path(self, input_hash: str) -> Path:
        """
        Get path for snapshot file based on input hash.
        
        Args:
            input_hash: Hash of the input
            
        Returns:
            Path to the snapshot file
        """
        return self.snapshot_dir / f"{input_hash}.json"
    
    def _save_snapshot(self, input_hash: str, response: Dict[str, Any]) -> None:
        """
        Save response to snapshot file.
        
        Args:
            input_hash: Hash of the input
            response: The response to save
        """
        with open(self._get_snapshot_path(input_hash), 'w') as f:
            json.dump(response, f, indent=2)
    
    def _load_snapshot(self, input_hash: str) -> Optional[Dict[str, Any]]:
        """
        Load response from snapshot file if it exists.
        
        Args:
            input_hash: Hash of the input
            
        Returns:
            Loaded response or None if not found
        """
        snapshot_path = self._get_snapshot_path(input_hash)
        if snapshot_path.exists():
            with open(snapshot_path, 'r') as f:
                return json.load(f)
        return None


class TraceableCapabilityMixin(LLMTraceableCapability):
    """Mixin to add tracing capabilities to LLM services."""
    
    def __init__(self):
        """Initialize tracing capabilities."""
        self.tracing_enabled = False
        self.callbacks = []
    
    def enable_tracing(self, project_name: Optional[str] = None) -> None:
        """
        Enable LangChain tracing for this LLM service.
        
        Args:
            project_name: Optional project name for tracing
        """
        if os.getenv("LANGCHAIN_API_KEY"):
            project = project_name or os.getenv("LANGCHAIN_PROJECT", "ai-ecosystem")
            tracer = LangChainTracer(project_name=project)
            
            # Add to callbacks if not already present
            if not any(isinstance(cb, LangChainTracer) for cb in self.callbacks):
                self.callbacks.append(tracer)
                
            self.tracing_enabled = True
            
            # Update the callback manager if it exists
            if hasattr(self, 'callback_manager'):
                self.callback_manager = CallbackManager(self.callbacks)
    
    def disable_tracing(self) -> None:
        """Disable LangChain tracing for this LLM service."""
        # Remove any tracers from callbacks
        self.callbacks = [cb for cb in self.callbacks 
                          if not isinstance(cb, LangChainTracer)]
        self.tracing_enabled = False
        
        # Update the callback manager if it exists
        if hasattr(self, 'callback_manager'):
            self.callback_manager = CallbackManager(self.callbacks)
