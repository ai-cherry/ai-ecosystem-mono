"""
Process service for handling API requests.

This module provides a service layer between API endpoints and backend 
processing, with proper error handling and validation.
"""
import logging
from typing import Dict, Any, Optional, Union

from app.services.llm.factory import create_llm_service

# Set up logging
logger = logging.getLogger(__name__)


class ProcessService:
    """Service for processing API requests."""
    
    def __init__(self, llm_provider: str = "openai", model_name: Optional[str] = None):
        """
        Initialize the process service.
        
        Args:
            llm_provider: The LLM provider to use
            model_name: The model name to use
        """
        self.llm_provider = llm_provider
        self.model_name = model_name
        
        # Create LLM service lazily on first use
        self._llm_service = None
    
    @property
    def llm_service(self):
        """Get (or lazily create) the LLM service."""
        if not self._llm_service:
            self._llm_service = create_llm_service(
                provider=self.llm_provider,
                model_name=self.model_name
            )
        return self._llm_service
    
    async def process_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request using the LLM service.
        
        Args:
            data: The request data
            
        Returns:
            The processed result
        """
        try:
            # Validate required fields
            if not data or not isinstance(data, dict):
                return self._create_error_response(
                    "Invalid request format. Expected a JSON object."
                )
            
            # Process with LLM
            result = self.llm_service.process(data)
            
            # Add service metadata
            result["service_info"] = {
                "provider": self.llm_provider,
                "model": self.model_name or self.llm_service.model_name
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            return self._create_error_response(f"Processing error: {str(e)}")
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            message: The error message
            
        Returns:
            Error response dictionary
        """
        return {
            "error": message,
            "content": "Error processing request",
            "metadata": {
                "provider": self.llm_provider,
                "model": self.model_name
            }
        }


# Singleton instance with default configuration
default_process_service = ProcessService()
