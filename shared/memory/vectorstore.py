"""
Vector Store memory implementation using LangChain.
"""

import os
import uuid
from typing import Any, Dict, List, Optional, Union

from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
import pinecone

from shared.config import memory_settings
from shared.memory.interfaces import VectorMemory


class VectorStore(VectorMemory):
    """
    Vector Store implementation using LangChain and Pinecone.
    
    This class provides methods to store embeddings and perform
    similarity search for text.
    """
    
    def __init__(
        self,
        index_name: Optional[str] = None,
        embedding_model: Optional[Any] = None,
        api_key: Optional[str] = None,
        environment: Optional[str] = None
    ):
        """
        Initialize the Vector Store.
        
        Args:
            index_name: The name of the Pinecone index. If not provided,
                it will be read from the environment.
            embedding_model: The embedding model to use. If not provided,
                OpenAIEmbeddings will be used.
            api_key: The Pinecone API key. If not provided, it will be
                read from the environment.
            environment: The Pinecone environment. If not provided, it will
                be read from the environment.
        """
        self.api_key = api_key or memory_settings.PINECONE_API_KEY
        self.environment = environment or memory_settings.PINECONE_ENVIRONMENT
        self.index_name = index_name or memory_settings.PINECONE_INDEX_NAME
        
        # Initialize embedding model
        self.embedding_model = embedding_model or OpenAIEmbeddings(
            openai_api_key=memory_settings.OPENAI_API_KEY
        )
        
        # Initialize Pinecone
        self._init_pinecone()
        
        # Initialize vector store
        self.vectorstore = Pinecone.from_existing_index(
            self.index_name,
            self.embedding_model
        )
    
    def save(self, key: str, data: Any) -> str:
        """
        Save data to the vector store.
        
        Args:
            key: The key to store the data under.
            data: The data to store.
            
        Returns:
            The document ID.
        """
        # For simplicity, this just delegates to upsert_text
        if isinstance(data, str):
            return self.upsert_text(data, {"id": key})
        elif isinstance(data, dict) and "text" in data:
            metadata = data.copy()
            text = metadata.pop("text")
            metadata["id"] = key
            return self.upsert_text(text, metadata)
        else:
            raise ValueError("Data must be a string or a dict with a 'text' key")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve data from the vector store.
        
        Note: This is not the primary use case for a vector store,
        which is typically used for similarity search rather than key-based
        retrieval. For key-based retrieval, use Firestore or Redis instead.
        
        Args:
            key: The key to retrieve.
            
        Returns:
            The document data, or None if not found.
        """
        # Query the vector store for the exact ID
        results = self.vectorstore.similarity_search(
            query="",  # Empty query
            k=1,
            filter={"id": key}
        )
        
        if not results:
            return None
        
        return {
            "text": results[0].page_content,
            "metadata": results[0].metadata
        }
    
    def delete(self, key: str) -> bool:
        """
        Delete data from the vector store.
        
        Args:
            key: The key to delete.
            
        Returns:
            True if successful, False otherwise.
        """
        # Use Pinecone's delete method
        try:
            index = pinecone.Index(self.index_name)
            index.delete(ids=[key])
            return True
        except Exception as e:
            print(f"Error deleting from vector store: {e}")
            return False
    
    def upsert_text(self, 
                    text: str, 
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create embedding and store in vector store.
        
        Args:
            text: The text to embed and store.
            metadata: Optional metadata to associate with the text.
            
        Returns:
            The document ID.
        """
        metadata = metadata or {}
        
        # Generate a document ID if not provided in metadata
        doc_id = metadata.get("id", str(uuid.uuid4()))
        
        # Ensure ID is included in metadata
        metadata["id"] = doc_id
        
        # Add text with metadata to vector store
        self.vectorstore.add_texts(
            texts=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )
        
        return doc_id
    
    def query(self, 
              query_text: str, 
              top_k: int = 5,
              metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query vector store for similar texts.
        
        Args:
            query_text: The query text.
            top_k: Maximum number of results to return.
            metadata_filter: Optional filter for metadata fields.
            
        Returns:
            List of matching documents with similarity scores.
        """
        # Build the similarity search
        results = self.vectorstore.similarity_search_with_score(
            query=query_text,
            k=top_k,
            filter=metadata_filter
        )
        
        # Format the results
        return [
            {
                "text": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            }
            for doc, score in results
        ]
    
    def delete_by_metadata(self, metadata_filter: Dict[str, Any]) -> int:
        """
        Delete vectors matching metadata filter.
        
        Args:
            metadata_filter: Filter specifying which vectors to delete.
            
        Returns:
            Number of deleted vectors.
        """
        # This requires implementation-specific handling
        # For Pinecone, we need to first query for IDs that match the filter
        try:
            index = pinecone.Index(self.index_name)
            
            # Note: This is a simplified approach. Real implementation would
            # likely need pagination for large datasets
            query_response = index.query(
                vector=[0] * 1536,  # Dummy vector
                filter=metadata_filter,
                top_k=10000,  # Get as many matches as possible
                include_metadata=False
            )
            
            # Extract IDs
            ids_to_delete = [match.id for match in query_response.matches]
            
            if not ids_to_delete:
                return 0
            
            # Delete IDs
            index.delete(ids=ids_to_delete)
            
            return len(ids_to_delete)
        except Exception as e:
            print(f"Error deleting from vector store by metadata: {e}")
            return 0
    
    def _init_pinecone(self) -> None:
        """
        Initialize the Pinecone client and create the index if it doesn't exist.
        """
        # Initialize Pinecone
        pinecone.init(
            api_key=self.api_key,
            environment=self.environment
        )
        
        # Create index if it doesn't exist
        if self.index_name not in pinecone.list_indexes():
            pinecone.create_index(
                name=self.index_name,
                dimension=1536,  # OpenAI's embedding dimension
                metric="cosine"
            )
    
    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        index_name: Optional[str] = None,
        **kwargs
    ) -> "VectorStore":
        """
        Create a VectorStore from a list of texts.
        
        Args:
            texts: List of texts to add to the vector store.
            metadatas: Optional list of metadata dicts to associate with the texts.
            index_name: The name of the Pinecone index.
            **kwargs: Additional arguments for the VectorStore constructor.
            
        Returns:
            A VectorStore instance with the texts added.
        """
        # Create a new VectorStore
        store = cls(index_name=index_name, **kwargs)
        
        # Add the texts
        metadatas = metadatas or [{}] * len(texts)
        ids = [str(uuid.uuid4()) for _ in range(len(texts))]
        
        # Add each text to the vector store
        for text, metadata, id in zip(texts, metadatas, ids):
            # Add ID to metadata
            metadata["id"] = id
            # Add text to vector store
            store.upsert_text(text, metadata)
        
        return store
