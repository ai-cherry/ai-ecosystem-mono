"""
Common interfaces for memory implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


class BaseMemory(ABC):
    """Base interface for all memory implementations."""
    
    @abstractmethod
    def save(self, key: str, data: Any) -> str:
        """Save data to memory."""
        pass
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve data from memory."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete data from memory."""
        pass


class ConversationMemory(BaseMemory):
    """Interface for conversation history storage."""
    
    @abstractmethod
    def save_message(self, 
                     conversation_id: str, 
                     message: Dict[str, Any], 
                     user_id: Optional[str] = None) -> str:
        """Save a message to a conversation history."""
        pass
    
    @abstractmethod
    def get_conversation(self, 
                         conversation_id: str, 
                         limit: Optional[int] = None, 
                         before: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve conversation history."""
        pass
    
    @abstractmethod
    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation history."""
        pass


class VectorMemory(BaseMemory):
    """Interface for vector storage and search."""
    
    @abstractmethod
    def upsert_text(self, 
                    text: str, 
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create embedding and store in vector store."""
        pass
    
    @abstractmethod
    def query(self, 
              query_text: str, 
              top_k: int = 5) -> List[Dict[str, Any]]:
        """Query vector store for similar texts."""
        pass
    
    @abstractmethod
    def delete_by_metadata(self, metadata_filter: Dict[str, Any]) -> int:
        """Delete vectors matching metadata filter."""
        pass
