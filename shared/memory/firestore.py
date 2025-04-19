"""
Firestore-based memory implementation.
"""

import datetime
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union

from google.cloud import firestore

from shared.config import memory_settings
from shared.memory.interfaces import BaseMemory, ConversationMemory


class FirestoreMemory(ConversationMemory):
    """
    Firestore-based memory implementation.
    
    This class provides methods to store and retrieve data from Firestore,
    with specialized functionality for conversation history.
    """
    
    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize the Firestore client.
        
        Args:
            project_id: The GCP project ID. If not provided, it will be read
                from the environment.
        """
        self.project_id = project_id or memory_settings.FIRESTORE_PROJECT_ID
        self.db = firestore.Client(project=self.project_id)
    
    def save(self, key: str, data: Any) -> str:
        """
        Save data to Firestore.
        
        Args:
            key: The key to store the data under (collection/document).
            data: The data to store.
            
        Returns:
            The document ID.
        """
        # Parse the key (collection/document format)
        collection, doc_id = self._parse_key(key)
        
        # If data is not a dict, wrap it
        if not isinstance(data, dict):
            data = {"value": data}
        
        # Add timestamps
        data["created_at"] = firestore.SERVER_TIMESTAMP
        data["updated_at"] = firestore.SERVER_TIMESTAMP
        
        # Save to Firestore
        if doc_id:
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.set(data)
        else:
            doc_id = str(uuid.uuid4())
            doc_ref = self.db.collection(collection).document(doc_id)
            doc_ref.set(data)
        
        return f"{collection}/{doc_id}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve data from Firestore.
        
        Args:
            key: The key to retrieve (collection/document).
            
        Returns:
            The document data, or None if not found.
        """
        collection, doc_id = self._parse_key(key)
        
        if not doc_id:
            raise ValueError("Document ID is required for get operation")
        
        doc_ref = self.db.collection(collection).document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
        
        return doc.to_dict()
    
    def delete(self, key: str) -> bool:
        """
        Delete data from Firestore.
        
        Args:
            key: The key to delete (collection/document).
            
        Returns:
            True if successful, False otherwise.
        """
        collection, doc_id = self._parse_key(key)
        
        if not doc_id:
            raise ValueError("Document ID is required for delete operation")
        
        doc_ref = self.db.collection(collection).document(doc_id)
        doc_ref.delete()
        
        return True
    
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
            The message document ID.
        """
        # Ensure message has required fields
        if "content" not in message:
            raise ValueError("Message must have 'content' field")
        
        if "role" not in message:
            message["role"] = "user"
        
        # Create message data
        message_data = {
            "conversation_id": conversation_id,
            "content": message["content"],
            "role": message["role"],
            "timestamp": firestore.SERVER_TIMESTAMP,
        }
        
        if user_id:
            message_data["user_id"] = user_id
        
        # Save to messages collection
        message_id = str(uuid.uuid4())
        self.db.collection("messages").document(message_id).set(message_data)
        
        # Update conversation metadata
        conversation_ref = self.db.collection("conversations").document(conversation_id)
        conversation = conversation_ref.get()
        
        if conversation.exists:
            conversation_ref.update({
                "updated_at": firestore.SERVER_TIMESTAMP,
                "message_count": firestore.Increment(1)
            })
        else:
            conversation_ref.set({
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "message_count": 1,
                "user_id": user_id
            })
        
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
            before: Retrieve messages before this message ID.
            
        Returns:
            List of messages in the conversation.
        """
        query = (self.db.collection("messages")
                 .where("conversation_id", "==", conversation_id)
                 .order_by("timestamp", direction=firestore.Query.DESCENDING))
        
        if before:
            before_doc = self.db.collection("messages").document(before).get()
            if before_doc.exists:
                before_time = before_doc.get("timestamp")
                query = query.where("timestamp", "<", before_time)
        
        if limit:
            query = query.limit(limit)
        
        messages = []
        for doc in query.stream():
            message = doc.to_dict()
            message["id"] = doc.id
            messages.append(message)
        
        # Return in chronological order
        messages.reverse()
        return messages
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """
        Clear a conversation history.
        
        Args:
            conversation_id: The conversation ID.
            
        Returns:
            True if successful.
        """
        # Delete all messages
        batch_size = 500
        while True:
            # Get a batch of messages
            message_batch = (self.db.collection("messages")
                           .where("conversation_id", "==", conversation_id)
                           .limit(batch_size)
                           .stream())
            
            deleted = 0
            
            # Delete messages in batch
            batch = self.db.batch()
            for doc in message_batch:
                batch.delete(doc.reference)
                deleted += 1
            
            # If no documents to delete, break
            if deleted == 0:
                break
                
            # Commit the batch
            batch.commit()
            
            # If we deleted less than batch_size, we're done
            if deleted < batch_size:
                break
        
        # Update conversation metadata
        conversation_ref = self.db.collection("conversations").document(conversation_id)
        conversation_ref.update({
            "updated_at": firestore.SERVER_TIMESTAMP,
            "message_count": 0
        })
        
        return True
    
    def save_document(self, collection: str, data: Dict[str, Any], doc_id: Optional[str] = None) -> str:
        """
        Save a document to a Firestore collection.
        
        Args:
            collection: The collection to save to.
            data: The document data.
            doc_id: Optional document ID. If not provided, a UUID will be generated.
            
        Returns:
            The document ID.
        """
        return self.save(f"{collection}/{doc_id or ''}", data)
    
    def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document from a Firestore collection.
        
        Args:
            collection: The collection to retrieve from.
            doc_id: The document ID.
            
        Returns:
            The document data, or None if not found.
        """
        return self.get(f"{collection}/{doc_id}")
    
    def query_documents(self, 
                        collection: str, 
                        filters: List[Tuple[str, str, Any]], 
                        limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query documents from a Firestore collection.
        
        Args:
            collection: The collection to query.
            filters: List of (field, operator, value) tuples for filtering.
            limit: Maximum number of documents to retrieve.
            
        Returns:
            List of matching documents.
        """
        query = self.db.collection(collection)
        
        for field, operator, value in filters:
            query = query.where(field, operator, value)
        
        if limit:
            query = query.limit(limit)
        
        results = []
        for doc in query.stream():
            data = doc.to_dict()
            data["id"] = doc.id
            results.append(data)
        
        return results
    
    def _parse_key(self, key: str) -> Tuple[str, Optional[str]]:
        """
        Parse a key into collection and document ID.
        
        Args:
            key: The key to parse (collection/document).
            
        Returns:
            Tuple of (collection, document_id or None).
        """
        parts = key.split("/", 1)
        
        if len(parts) == 1:
            return parts[0], None
        
        return parts[0], parts[1] if parts[1] else None
