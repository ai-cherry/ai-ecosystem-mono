"""
OpenAI implementation of LLM service.

This module provides a concrete implementation of the LLM service interface
specifically for OpenAI's models (both chat and completion models).
"""
import os
from typing import Dict, Any, Optional, Union, List, cast

try:
    from langchain.chat_models import ChatOpenAI
    from langchain.llms import OpenAI
    from langchain.schema import (
        HumanMessage,
        SystemMessage,
        AIMessage,
    )
except ImportError:
    # Stubs for type checking if imports fail
    class ChatOpenAI:
        def __init__(self, *args, **kwargs): pass
        def generate(self, *args, **kwargs): pass
        
    class OpenAI:
        def __init__(self, *args, **kwargs): pass
        def generate(self, *args, **kwargs): pass
        
    class HumanMessage:
        def __init__(self, content: str): self.content = content
        
    class SystemMessage:
        def __init__(self, content: str): self.content = content
        
    class AIMessage:
        def __init__(self, content: str): self.content = content

from orchestrator.app.core.config import settings
from orchestrator.app.services.llm.base_implementation import (
    BaseLLMImplementation,
    TestingCapabilityMixin, 
    TraceableCapabilityMixin,
)


class OpenAIService(BaseLLMImplementation, TestingCapabilityMixin, TraceableCapabilityMixin):
    """OpenAI-specific implementation of the LLM service."""
    
    def __init__(
        self, 
        model_name: str = None,
        temperature: float = 0.7,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        streaming: bool = False,
        verbose: bool = False,
        seed: Optional[int] = None,
        enable_tracing: bool = True,
        snapshot_mode: bool = False,
    ):
        """
        Initialize OpenAI LLM service.
        
        Args:
            model_name: The name of the OpenAI model to use
            temperature: Controls randomness (0=deterministic, 1=creative)
            api_key: OpenAI API key (defaults to env var)
            organization: OpenAI organization ID
            streaming: Whether to stream responses
            verbose: Whether to enable verbose output
            seed: Optional seed for deterministic outputs
            enable_tracing: Whether to enable LangChain tracing
            snapshot_mode: Whether to use snapshot testing mode
        """
        # Call parent initializers
        BaseLLMImplementation.__init__(
            self, 
            model_name=model_name or settings.DEFAULT_LLM_MODEL,
            temperature=temperature
        )
        TestingCapabilityMixin.__init__(self)
        TraceableCapabilityMixin.__init__(self)
        
        # OpenAI-specific initialization
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.organization = organization
        self.streaming = streaming
        self.verbose = verbose
        
        # Set seed if provided
        if seed is not None:
            self.enable_deterministic_mode(seed)
        
        # Set snapshot mode if enabled
        if snapshot_mode:
            self.enable_snapshot_mode()
        
        # Enable tracing if requested
        if enable_tracing:
            self.enable_tracing()
            
        # Initialize the model
        self._initialize_model()
    
    def _initialize_model(self) -> None:
        """Initialize the OpenAI model based on configuration."""
        # Determine if this is a chat model
        is_chat_model = (
            self.model_name.startswith("gpt-3.5-turbo") or
            self.model_name.startswith("gpt-4") or
            "instruct" in self.model_name
        )
        
        model_kwargs = {}
        if self.seed is not None:
            model_kwargs["seed"] = self.seed
            
        if is_chat_model:
            self.model = ChatOpenAI(
                model_name=self.model_name,
                temperature=self.temperature,
                openai_api_key=self.api_key,
                openai_organization=self.organization,
                streaming=self.streaming,
                verbose=self.verbose,
                callback_manager=self.callback_manager,
                model_kwargs=model_kwargs
            )
        else:
            # Completion model
            self.model = OpenAI(
                model_name=self.model_name,
                temperature=self.temperature,
                openai_api_key=self.api_key,
                openai_organization=self.organization,
                streaming=self.streaming,
                verbose=self.verbose,
                callback_manager=self.callback_manager,
                model_kwargs=model_kwargs
            )
            
        self.is_chat_model = is_chat_model
    
    def _format_messages(self, input_data: Union[str, Dict[str, Any], List[Any]]) -> List[Any]:
        """
        Convert input to a standardized message format for OpenAI.
        
        Args:
            input_data: Raw input in various formats
            
        Returns:
            List of LangChain message objects
        """
        if isinstance(input_data, str):
            return [HumanMessage(content=input_data)]
        
        elif isinstance(input_data, dict):
            messages = []
            
            # Handle system message
            if "system" in input_data:
                messages.append(SystemMessage(content=input_data["system"]))
                
            # Handle user message
            if "user" in input_data:
                messages.append(HumanMessage(content=input_data["user"]))
                
            # Handle structured messages list
            if "messages" in input_data and isinstance(input_data["messages"], list):
                for msg in input_data["messages"]:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    
                    if role == "system":
                        messages.append(SystemMessage(content=content))
                    elif role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
            
            return messages if messages else [HumanMessage(content="")]
        
        else:
            # Assume it's already a list of message objects
            return input_data
    
    def process(
        self, 
        input_data: Union[str, Dict[str, Any], List[Any]]
    ) -> Dict[str, Any]:
        """
        Process input with OpenAI LLM.
        
        Args:
            input_data: Either a string prompt, a dict with prompt configuration,
                       or a list of LangChain message objects
                       
        Returns:
            Dict containing the LLM response and metadata
        """
        # Convert input to messages format
        messages = self._format_messages(input_data)
        
        # Handle snapshot testing if enabled
        if self.snapshot_mode:
            input_hash = self._compute_input_hash(messages)
            snapshot = self._load_snapshot(input_hash)
            
            if snapshot:
                # Return saved snapshot for deterministic testing
                return snapshot
        
        # Process with the LLM
        try:
            response = self.model.generate([messages])
            
            # Extract and format the response
            result = {
                "content": response.generations[0][0].text,
                "model": self.model_name,
                "metadata": {
                    "token_usage": response.llm_output.get("token_usage", {}),
                    "model_name": self.model_name,
                    "temperature": self.temperature,
                }
            }
            
            # Add seed information if available
            if self.seed is not None:
                result["metadata"]["seed"] = self.seed
            
            # Save snapshot if in snapshot mode
            if self.snapshot_mode:
                self._save_snapshot(input_hash, result)
                
            return result
            
        except Exception as e:
            # Handle errors gracefully
            return self._handle_error(e)
    
    def enable_deterministic_mode(self, seed: int) -> None:
        """
        Enable deterministic mode with a specific seed for OpenAI.
        
        Args:
            seed: Seed value for deterministic outputs
        """
        super().enable_deterministic_mode(seed)
        
        # Update model with seed if it's already initialized
        if hasattr(self, 'model'):
            if not hasattr(self.model, 'model_kwargs'):
                self.model.model_kwargs = {}
            
            self.model.model_kwargs["seed"] = seed


# Factory function to create an OpenAI service
def create_openai_service(**kwargs) -> OpenAIService:
    """
    Create an OpenAI service with the specified configuration.
    
    Args:
        **kwargs: Configuration parameters for the OpenAI service
        
    Returns:
        Configured OpenAI service
    """
    return OpenAIService(**kwargs)
