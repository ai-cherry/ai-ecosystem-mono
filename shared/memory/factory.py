"""
Memory system factory.

This module provides a factory for creating memory system instances with proper
connection pooling, consistent error handling, and dependency injection.
"""
from typing import Dict, Any, Optional, Type, Union

from shared.config import memory_settings
from shared.memory.interfaces import BaseMemory, ConversationMemory, VectorMemory
from shared.memory.redis import RedisMemory
from shared.memory.firestore import FirestoreMemory
from shared.memory.vectorstore import VectorStore


class MemorySystemFactory:
    """Factory for creating memory system instances."""
    
    # Registry of available memory implementations by type
    _registry = {
        "base": {
            "redis": RedisMemory,
            "firestore": FirestoreMemory,
            "vector": VectorStore,
        },
        "conversation": {
            "redis": RedisMemory,
        },
        "vector": {
            "pinecone": VectorStore,
        }
    }
    
    # Connection pool
    _connections = {}
    
    @classmethod
    def register_implementation(
        cls, 
        memory_type: str, 
        provider: str,
        implementation_class: Type[BaseMemory]
    ) -> None:
        """
        Register a new memory implementation with the factory.
        
        Args:
            memory_type: Type of memory (base, conversation, vector)
            provider: The provider name (redis, firestore, pinecone, etc.)
            implementation_class: The class to instantiate for this provider
        """
        if memory_type not in cls._registry:
            cls._registry[memory_type] = {}
        
        cls._registry[memory_type][provider.lower()] = implementation_class
    
    @classmethod
    def create_memory(
        cls, 
        memory_type: str = "base",
        provider: Optional[str] = None,
        reuse_connection: bool = True,
        connection_key: Optional[str] = None,
        **kwargs
    ) -> BaseMemory:
        """
        Create a memory instance for the specified type and provider.
        
        Args:
            memory_type: Type of memory (base, conversation, vector)
            provider: The provider name (redis, firestore, pinecone)
                      If not specified, uses the default from settings
            reuse_connection: Whether to reuse existing connections
            connection_key: Optional custom key for connection pooling
            **kwargs: Additional configuration parameters
            
        Returns:
            An initialized memory instance
            
        Raises:
            ValueError: If the memory type or provider is not supported
        """
        # Determine provider from settings if not specified
        if not provider:
            if memory_type == "vector":
                provider = memory_settings.VECTOR_STORE_TYPE
            else:
                provider = "redis"  # Default for other types
        
        provider = provider.lower()
        
        # Check if type and provider are supported
        if memory_type not in cls._registry:
            raise ValueError(f"Unsupported memory type: {memory_type}")
        
        if provider not in cls._registry[memory_type]:
            raise ValueError(
                f"Unsupported provider '{provider}' for memory type '{memory_type}'. "
                f"Available providers: {list(cls._registry[memory_type].keys())}"
            )
        
        # Get the implementation class
        implementation_class = cls._registry[memory_type][provider]
        
        # Handle connection pooling
        if reuse_connection:
            # Generate connection key if not provided
            if not connection_key:
                connection_key = f"{memory_type}:{provider}"
                
                # Add relevant configuration to key
                if provider == "redis" and "redis_url" in kwargs:
                    connection_key += f":{kwargs['redis_url']}"
                elif provider == "firestore" and "project_id" in kwargs:
                    connection_key += f":{kwargs['project_id']}"
                elif provider == "pinecone" and "index_name" in kwargs:
                    connection_key += f":{kwargs['index_name']}"
            
            # Return cached connection if available
            if connection_key in cls._connections:
                return cls._connections[connection_key]
        
        # Create new instance
        instance = implementation_class(**kwargs)
        
        # Cache connection if pooling is enabled
        if reuse_connection:
            cls._connections[connection_key] = instance
        
        return instance
    
    @classmethod
    def create_conversation_memory(cls, provider: str = "redis", **kwargs) -> ConversationMemory:
        """
        Create a conversation memory instance.
        
        Args:
            provider: The provider name (default: redis)
            **kwargs: Additional configuration parameters
            
        Returns:
            A conversation memory instance
        """
        return cls.create_memory("conversation", provider, **kwargs)
    
    @classmethod
    def create_vector_memory(cls, provider: str = None, **kwargs) -> VectorMemory:
        """
        Create a vector memory instance.
        
        Args:
            provider: The provider name (default: from settings)
            **kwargs: Additional configuration parameters
            
        Returns:
            A vector memory instance
        """
        return cls.create_memory("vector", provider, **kwargs)
    
    @classmethod
    def clear_connection_pool(cls) -> None:
        """Clear the connection pool to release resources."""
        cls._connections.clear()
    
    @classmethod
    def get_available_providers(cls, memory_type: str = "base") -> list:
        """
        Get a list of available providers for the specified memory type.
        
        Args:
            memory_type: Type of memory
            
        Returns:
            List of provider names
        """
        if memory_type in cls._registry:
            return list(cls._registry[memory_type].keys())
        return []


# Convenience functions

def create_memory(memory_type: str = "base", provider: str = None, **kwargs) -> BaseMemory:
    """Create a memory instance with the specified configuration."""
    return MemorySystemFactory.create_memory(memory_type, provider, **kwargs)

def create_conversation_memory(**kwargs) -> ConversationMemory:
    """Create a conversation memory instance."""
    return MemorySystemFactory.create_conversation_memory(**kwargs)

def create_vector_memory(**kwargs) -> VectorMemory:
    """Create a vector memory instance."""
    return MemorySystemFactory.create_vector_memory(**kwargs)
