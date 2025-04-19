"""
Base LLM service with support for deterministic testing and seeded models.

This module provides backward compatibility with the original LLMService
while leveraging the new modular architecture.
"""
import os
from typing import Dict, Any, Optional, Union, List

# Import the new architecture
from orchestrator.app.services.llm.factory import create_llm_service
from orchestrator.app.services.llm.interfaces import BaseLLMService


class LLMService:
    """
    Base service for LLM interactions with deterministic testing support.
    
    This class maintains backward compatibility with existing code while
    using the new modular LLM service architecture internally.
    """
    
    def __init__(
        self, 
        model_name: str = "gpt-4o",
        temperature: float = 0.7,
        seed: Optional[int] = None,
        enable_tracing: bool = True,
        snapshot_mode: bool = False
    ):
        """
        Initialize LLM service with support for deterministic outputs.
        
        Args:
            model_name: The name of the LLM model to use
            temperature: Controls randomness (0=deterministic, 1=creative)
            seed: Optional seed for deterministic outputs
            enable_tracing: Whether to enable LangSmith tracing
            snapshot_mode: Whether to use snapshot testing mode
        """
        # Create a service using the new factory
        self._service = create_llm_service(
            provider="openai",  # Default provider
            model_name=model_name,
            temperature=temperature,
            seed=seed,
            enable_tracing=enable_tracing,
            snapshot_mode=snapshot_mode
        )
        
        # Store configuration for compatibility
        self.seed = seed
        self.snapshot_mode = snapshot_mode
        
        # For backward compatibility, expose model
        # Try to get the model attribute if it exists
        self.model = getattr(self._service, 'model', None)
    
    def process(
        self, 
        input_data: Union[str, Dict[str, Any], List[Any]]
    ) -> Dict[str, Any]:
        """
        Process input with LLM, supporting deterministic testing.
        
        Args:
            input_data: Either a string prompt, a dict with prompt configuration,
                       or a list of message objects
                       
        Returns:
            Dict containing the LLM response and metadata
        """
        # Delegate to the new service implementation
        return self._service.process(input_data)


def create_llm_service_with_defaults(**kwargs) -> BaseLLMService:
    """
    Create an LLM service with project defaults.
    
    Args:
        **kwargs: Override default configuration
        
    Returns:
        Configured LLM service
    """
    return create_llm_service(**kwargs)
