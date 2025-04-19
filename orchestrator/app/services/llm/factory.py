"""
LLM service factory.

This module provides a factory for creating LLM services with various providers.
"""
from typing import Dict, Any, Optional, Type, Union

from app.services.llm.interfaces import BaseLLMService
from app.services.llm.openai_service import OpenAIService


class LLMServiceFactory:
    """Factory for creating LLM services."""
    
    # Registry of available service providers
    _registry = {
        "openai": OpenAIService,
        "gpt-3.5": OpenAIService,
        "gpt-4": OpenAIService,
        "gpt-4o": OpenAIService,
    }
    
    @classmethod
    def register_provider(cls, provider_name: str, service_class: Type[BaseLLMService]) -> None:
        """
        Register a new provider with the factory.
        
        Args:
            provider_name: The name of the provider
            service_class: The service class to instantiate for this provider
        """
        cls._registry[provider_name.lower()] = service_class
    
    @classmethod
    def create_service(
        cls, 
        provider: str = "openai",
        model_name: Optional[str] = None,
        **kwargs
    ) -> BaseLLMService:
        """
        Create an LLM service for the specified provider.
        
        Args:
            provider: The provider name (e.g., "openai", "anthropic")
            model_name: The name of the model to use
            **kwargs: Additional configuration parameters for the service
            
        Returns:
            An initialized LLM service
            
        Raises:
            ValueError: If the provider is not supported
        """
        provider = provider.lower()
        
        # Check if provider is directly available
        if provider in cls._registry:
            service_class = cls._registry[provider]
        else:
            # Try to infer provider from model name
            if model_name:
                # Extract provider from model name prefix
                for prefix, service_class in cls._registry.items():
                    if model_name.startswith(prefix):
                        break
                else:
                    raise ValueError(f"Unsupported provider or model: {provider}/{model_name}")
            else:
                raise ValueError(f"Unsupported provider: {provider}")
        
        # Create the service with specified configuration
        return service_class(model_name=model_name, **kwargs)
    
    @classmethod
    def get_available_providers(cls) -> list:
        """
        Get a list of available providers.
        
        Returns:
            List of provider names
        """
        return list(cls._registry.keys())


def create_llm_service(
    provider: str = "openai", 
    model_name: Optional[str] = None,
    **kwargs
) -> BaseLLMService:
    """
    Convenience function to create an LLM service.
    
    Args:
        provider: The provider name
        model_name: The model name
        **kwargs: Additional configuration parameters
        
    Returns:
        An initialized LLM service
    """
    return LLMServiceFactory.create_service(
        provider=provider,
        model_name=model_name,
        **kwargs
    )
