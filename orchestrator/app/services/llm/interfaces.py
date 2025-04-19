"""
Base interfaces for LLM services.

This module defines the abstract base classes and interfaces for
all LLM service implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union, List

# Using typing.Any instead of direct langchain imports for better compatibility
from typing import Any as BaseMessage


class BaseLLMService(ABC):
    """Base interface for all LLM service implementations."""
    
    @abstractmethod
    def process(
        self, 
        input_data: Union[str, Dict[str, Any], List[Any]]
    ) -> Dict[str, Any]:
        """
        Process input with LLM.
        
        Args:
            input_data: Either a string prompt, a dict with prompt configuration,
                       or a list of LangChain message objects
                       
        Returns:
            Dict containing the LLM response and metadata
        """
        pass


class LLMTestingCapability(ABC):
    """Interface for LLM testing capabilities."""
    
    @abstractmethod
    def enable_deterministic_mode(self, seed: int) -> None:
        """
        Enable deterministic mode with a specific seed.
        
        Args:
            seed: Seed value for deterministic outputs
        """
        pass
    
    @abstractmethod
    def enable_snapshot_mode(self, snapshot_dir: Optional[str] = None) -> None:
        """
        Enable snapshot testing mode.
        
        Args:
            snapshot_dir: Optional directory to store snapshots
        """
        pass


class LLMTraceableCapability(ABC):
    """Interface for LLM tracing capabilities."""
    
    @abstractmethod
    def enable_tracing(self, project_name: Optional[str] = None) -> None:
        """
        Enable LangChain tracing for this LLM service.
        
        Args:
            project_name: Optional project name for tracing
        """
        pass
    
    @abstractmethod
    def disable_tracing(self) -> None:
        """Disable LangChain tracing for this LLM service."""
        pass
