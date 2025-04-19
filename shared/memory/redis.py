"""
Redis-based memory implementation.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Union

import redis
from langchain.memory import RedisChatMessageHistory

from shared.config import memory_settings
from shared.memory.interfaces import BaseMemory, ConversationMemory


class RedisMemory(ConversationMemory):
    """
    Redis-based memory implementation.
    
    This class provides methods to store and retrieve data from Redis,
    with specialized functionality for conversation history.
    """
    
    def __init__(self, redis_url: Optional[str] = None, prefix: str = "ai:"):
        """
        Initialize the Redis client.
        
        Args:
            redis_url: The Redis connection URL. If not provided, it will be
                read from the environment.
            prefix: Prefix for keys stored in Redis.
        """
        self.redis_url = redis_url or memory_settings.REDIS_URL
        self.prefix = prefix
        
        # Parse password from URL if present
        password = memory_settings.REDIS_PASSWORD
        if not password and ":" in self.redis_url:
            parts = self.redis_url.split("@")
            if len(parts) > 1:
                auth_parts = parts[0].split(":")
                if len(auth_parts) > 2:
                    password = auth_parts[2]
        
        # Initialize Redis client
        self.redis = redis.from_url(self.redis_url)
    
    def save(self, key: str, data: Any, ttl: Optional[int] = None) -> str:
        """
        Save data to Redis.
        
        Args:
            key: The key to store the data under.
            data: The data to store.
            ttl: Optional time-to-live in seconds.
            
        Returns:
            The key.
        """
        # Prefix the key
        prefixed_key = f"{self.prefix}{key}"
        
        # Serialize the data
        if isinstance(data, (dict, list)):
            serialized = json.dumps(data)
        else:
            serialized = str(data)
        
        # Save to Redis
        self.redis.set(prefixed_key, serialized)
        
        # Set TTL if provided
        if ttl:
            self.redis.expire(prefixed_key, ttl)
        
        return key
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve data from Redis.
        
        Args:
            key: The key to retrieve.
            
        Returns:
            The data, or None if not found.
        """
        # Prefix the key
        prefixed_key = f"{self.prefix}{key}"
        
        # Get from Redis
        result = self.redis.get(prefixed_key)
        
        if result is None:
            return None
        
        # Attempt to deserialize as JSON
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # Return as string if not valid JSON
            return result.decode("utf-8")
    
    def delete(self, key: str) -> bool:
        """
        Delete data from Redis.
        
        Args:
            key: The key to delete.
            
        Returns:
            True if successful, False otherwise.
        """
        # Prefix the key
        prefixed_key = f"{self.prefix}{key}"
        
        # Delete from Redis
        result = self.redis.delete(prefixed_key)
        
        return result > 0
    
    def save_message(self, 
                     conversation_id: str, 
                     message: Dict[str, Any], 
                     user_id: Optional[str] = None) -> str:
        """
        Save a message to a conversation history.
        
        Args:
            conversation_id: The ID of the conversation.
            message: The message data (should have 'content' and 'role' keys).
            user_id: Optional user ID associated with the message.
            
        Returns:
            A unique message ID.
        """
        # Ensure message has required fields
        if "content" not in message:
            raise ValueError("Message must have 'content' field")
        
        if "role" not in message:
            message["role"] = "user"
        
        # Create a unique message ID
        message_id = str(uuid.uuid4())
        
        # Use LangChain's RedisChatMessageHistory to store messages
        redis_key = f"chat:{conversation_id}"
        history = RedisChatMessageHistory(
            session_id=redis_key,
            url=self.redis_url
        )
        
        # Add metadata to the message
        msg_with_metadata = message.copy()
        msg_with_metadata["id"] = message_id
        
        if user_id:
            msg_with_metadata["user_id"] = user_id
        
        # Add timestamp if not present
        if "timestamp" not in msg_with_metadata:
            from datetime import datetime
            msg_with_metadata["timestamp"] = datetime.utcnow().isoformat()
        
        # Add message to history
        # LangChain expects messages in the format {"role": "...", "content": "..."}
        # but we're storing additional metadata in our message object, so we need to create
        # a standard LangChain message and then also store the full metadata separately
        history.add_message({
            "role": message["role"],
            "content": message["content"]
        })
        
        # Store the full message with metadata in a separate key
        metadata_key = f"message:{conversation_id}:{message_id}"
        self.save(metadata_key, msg_with_metadata)
        
        # Also keep a list of message IDs for easier retrieval
        message_list_key = f"message_ids:{conversation_id}"
        self.redis.rpush(f"{self.prefix}{message_list_key}", message_id)
        
        # Update conversation metadata
        metadata = {
            "updated_at": msg_with_metadata["timestamp"],
            "message_count": self.redis.llen(f"{self.prefix}{message_list_key}"),
        }
        
        if user_id:
            metadata["user_id"] = user_id
        
        self.save(f"conversation:{conversation_id}", metadata)
        
        return message_id
    
    def get_conversation(self, 
                         conversation_id: str, 
                         limit: Optional[int] = None, 
                         before: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history.
        
        Args:
            conversation_id: The conversation ID.
            limit: Maximum number of messages to retrieve.
            before: Retrieve messages before this message ID (not implemented for Redis).
            
        Returns:
            List of messages in the conversation.
        """
        # Use LangChain's RedisChatMessageHistory to get messages
        redis_key = f"chat:{conversation_id}"
        history = RedisChatMessageHistory(
            session_id=redis_key,
            url=self.redis_url
        )
        
        # Get messages from history
        messages = history.messages
        
        # If we need to retrieve messages with full metadata, we need to get them from
        # our separate metadata store
        message_list_key = f"message_ids:{conversation_id}"
        message_ids = self.redis.lrange(f"{self.prefix}{message_list_key}", 0, -1)
        
        result_messages = []
        
        # If we have message IDs, retrieve the full messages with metadata
        if message_ids:
            # Convert bytes to strings
            message_ids = [mid.decode("utf-8") for mid in message_ids]
            
            # Apply "before" filter if provided
            if before and before in message_ids:
                before_index = message_ids.index(before)
                message_ids = message_ids[:before_index]
            
            # Apply limit if provided
            if limit and limit < len(message_ids):
                message_ids = message_ids[-limit:]
            
            # Retrieve messages with metadata
            for mid in message_ids:
                metadata_key = f"message:{conversation_id}:{mid}"
                message = self.get(metadata_key)
                if message:
                    result_messages.append(message)
        else:
            # Fall back to LangChain's messages if we don't have separate metadata
            result_messages = [{"role": msg.type, "content": msg.content} for msg in messages]
            
            # Apply limit if provided
            if limit and limit < len(result_messages):
                result_messages = result_messages[-limit:]
        
        return result_messages
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """
        Clear a conversation history.
        
        Args:
            conversation_id: The conversation ID.
            
        Returns:
            True if successful.
        """
        # Use LangChain's RedisChatMessageHistory to clear messages
        redis_key = f"chat:{conversation_id}"
        history = RedisChatMessageHistory(
            session_id=redis_key,
            url=self.redis_url
        )
        
        # Clear the history
        history.clear()
        
        # Also clear our metadata
        message_list_key = f"message_ids:{conversation_id}"
        message_ids_key = f"{self.prefix}{message_list_key}"
        
        # Get message IDs
        message_ids = self.redis.lrange(message_ids_key, 0, -1)
        
        # Delete all message metadata
        for mid in message_ids:
            metadata_key = f"message:{conversation_id}:{mid.decode('utf-8')}"
            self.delete(metadata_key)
        
        # Delete message ID list
        self.redis.delete(message_ids_key)
        
        # Update conversation metadata
        self.save(f"conversation:{conversation_id}", {
            "updated_at": self._current_timestamp(),
            "message_count": 0
        })
        
        return True
    
    def cache_result(self, key: str, value: Any, ttl: int = 3600) -> None:
        """
        Cache arbitrary data with TTL.
        
        Args:
            key: The key to cache the data under.
            value: The data to cache.
            ttl: Time-to-live in seconds (default: 1 hour).
        """
        cache_key = f"cache:{key}"
        self.save(cache_key, value, ttl)
    
    def get_cached_result(self, key: str) -> Optional[Any]:
        """
        Retrieve cached data.
        
        Args:
            key: The key to retrieve.
            
        Returns:
            The cached data, or None if not found or expired.
        """
        cache_key = f"cache:{key}"
        return self.get(cache_key)
    
    def _current_timestamp(self) -> str:
        """
        Get the current UTC timestamp in ISO format.
        
        Returns:
            The current timestamp.
        """
        from datetime import datetime
        return datetime.utcnow().isoformat()
