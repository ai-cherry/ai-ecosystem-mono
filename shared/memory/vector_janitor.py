"""
VectorJanitor for maintaining vector database health.

This module provides utilities for detecting and removing duplicate and orphaned
vectors from our vector databases, ensuring optimal performance and storage efficiency.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from shared.memory.memory_manager import MemoryManager
from shared.memory.vectorstore import VectorStore
from shared.memory.firestore import FirestoreMemory

# Initialize logger
logger = logging.getLogger(__name__)

class VectorJanitor:
    """
    Maintains the health and efficiency of vector databases.
    
    This class provides methods to:
    - Identify and remove duplicate vectors (with high similarity)
    - Detect and clean orphaned vectors (no corresponding document in Firestore)
    - Calculate storage stats and savings from cleanup operations
    - Send notifications about cleanup results
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        firestore: FirestoreMemory,
        similarity_threshold: float = 0.98,
        max_deletion_percentage: float = 5.0,  # Safety threshold: max % of vectors to delete
        dry_run: bool = False  # When True, detect but don't delete
    ):
        """
        Initialize the vector janitor.
        
        Args:
            vector_store: Vector store client for operations
            firestore: Firestore client for document verification
            similarity_threshold: Vectors with similarity >= this are considered duplicates
            max_deletion_percentage: Safety threshold percentage of total vectors
            dry_run: When True, detect but don't actually delete vectors
        """
        self.vector_store = vector_store
        self.firestore = firestore
        self.similarity_threshold = similarity_threshold
        self.max_deletion_percentage = max_deletion_percentage
        self.dry_run = dry_run
        
        # Stats tracking
        self.stats = {
            "total_vectors": 0,
            "duplicates_found": 0,
            "duplicates_removed": 0,
            "orphans_found": 0,
            "orphans_removed": 0,
            "bytes_saved": 0,
            "operation_time_seconds": 0,
            "start_time": None,
            "end_time": None
        }
    
    async def analyze(self) -> Dict[str, Any]:
        """
        Analyze vector store to find duplicates and orphans.
        
        Returns:
            Dictionary with analysis results
        """
        self.stats["start_time"] = datetime.utcnow().isoformat()
        start_time = time.time()
        
        # Get total vector count
        self.stats["total_vectors"] = await self.vector_store.count_vectors()
        
        # Find duplicates
        duplicates = await self._find_duplicates()
        self.stats["duplicates_found"] = len(duplicates)
        
        # Find orphans
        orphans = await self._find_orphans()
        self.stats["orphans_found"] = len(orphans)
        
        # Calculate operation time
        self.stats["operation_time_seconds"] = time.time() - start_time
        self.stats["end_time"] = datetime.utcnow().isoformat()
        
        # Return analysis results
        return {
            "total_vectors": self.stats["total_vectors"],
            "duplicates": duplicates,
            "orphans": orphans,
            "analysis_time_seconds": self.stats["operation_time_seconds"],
            "deletion_candidates": len(duplicates) + len(orphans),
            "estimated_space_saving_bytes": self._estimate_space_saving(len(duplicates) + len(orphans))
        }
    
    async def cleanup(self, deletion_candidates: Optional[Dict[str, List[str]]] = None) -> Dict[str, Any]:
        """
        Perform cleanup by removing duplicates and orphans.
        
        Args:
            deletion_candidates: Optional pre-analyzed candidates to delete
                                (if not provided, analyze() will be called)
        
        Returns:
            Dictionary with cleanup results
        """
        self.stats["start_time"] = datetime.utcnow().isoformat()
        start_time = time.time()
        
        # If no candidates provided, analyze first
        if deletion_candidates is None:
            analysis = await self.analyze()
            duplicates = analysis["duplicates"]
            orphans = analysis["orphans"]
        else:
            duplicates = deletion_candidates.get("duplicates", [])
            orphans = deletion_candidates.get("orphans", [])
        
        # Check safety threshold
        total_deletions = len(duplicates) + len(orphans)
        if self.stats["total_vectors"] > 0:
            deletion_percentage = (total_deletions / self.stats["total_vectors"]) * 100
            if deletion_percentage > self.max_deletion_percentage:
                logger.warning(
                    f"Safety threshold exceeded: {deletion_percentage:.2f}% of vectors would be deleted "
                    f"(max allowed: {self.max_deletion_percentage}%)"
                )
                return {
                    "success": False,
                    "error": "safety_threshold_exceeded",
                    "stats": self.stats,
                    "deletion_percentage": deletion_percentage,
                    "max_allowed_percentage": self.max_deletion_percentage
                }
        
        # Delete vectors if not in dry run mode
        if not self.dry_run:
            # Delete duplicates
            for vector_id in duplicates:
                try:
                    await self.vector_store.delete(vector_id)
                    self.stats["duplicates_removed"] += 1
                except Exception as e:
                    logger.error(f"Error deleting duplicate vector {vector_id}: {str(e)}")
            
            # Delete orphans
            for vector_id in orphans:
                try:
                    await self.vector_store.delete(vector_id)
                    self.stats["orphans_removed"] += 1
                except Exception as e:
                    logger.error(f"Error deleting orphan vector {vector_id}: {str(e)}")
        
        # Calculate space saved
        self.stats["bytes_saved"] = self._estimate_space_saving(
            self.stats["duplicates_removed"] + self.stats["orphans_removed"]
        )
        
        # Calculate operation time
        self.stats["operation_time_seconds"] = time.time() - start_time
        self.stats["end_time"] = datetime.utcnow().isoformat()
        
        # Return cleanup results
        return {
            "success": True,
            "stats": self.stats,
            "dry_run": self.dry_run
        }
    
    async def _find_duplicates(self) -> List[str]:
        """
        Find duplicate vectors based on similarity threshold.
        
        Returns:
            List of vector IDs that are duplicates
        """
        # This is a simplified approach - in a real implementation, we would need
        # to compare all vectors against each other efficiently, which requires
        # batching and possibly using approximate nearest neighbors
        
        # Sample approach: get all vectors and compare in batches
        # Note: This is not scalable for large vector stores and should be improved
        
        # Get all vectors (in a real implementation, we would batch this)
        try:
            all_vectors = await self.vector_store.get_all_vectors()
            
            # Check if we have vectors to process
            if not all_vectors:
                return []
            
            # Create a set to track duplicates
            duplicates = set()
            
            # Compare vectors
            for i, vec1 in enumerate(all_vectors[:-1]):
                for j, vec2 in enumerate(all_vectors[i+1:], i+1):
                    # Calculate similarity (cosine similarity)
                    similarity = self._calculate_similarity(vec1["embedding"], vec2["embedding"])
                    
                    # If similarity exceeds threshold, mark one as duplicate
                    if similarity >= self.similarity_threshold:
                        # Keep the older one (assuming it has more context/usage)
                        if vec1["metadata"].get("created_at", "") > vec2["metadata"].get("created_at", ""):
                            duplicates.add(vec1["id"])
                        else:
                            duplicates.add(vec2["id"])
            
            return list(duplicates)
            
        except Exception as e:
            logger.error(f"Error finding duplicates: {str(e)}")
            return []
    
    async def _find_orphans(self) -> List[str]:
        """
        Find orphaned vectors (no corresponding document in Firestore).
        
        Returns:
            List of vector IDs that are orphans
        """
        try:
            # Get all vector IDs
            vectors = await self.vector_store.get_all_vectors()
            vector_ids = [v["id"] for v in vectors]
            
            # Check each vector for corresponding Firestore document
            orphans = []
            for vector_id in vector_ids:
                firestore_key = f"memories/{vector_id}"
                document = await self.firestore.get(firestore_key)
                
                # If no document exists, it's an orphan
                if document is None:
                    orphans.append(vector_id)
            
            return orphans
            
        except Exception as e:
            logger.error(f"Error finding orphans: {str(e)}")
            return []
    
    def _calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity value (-1 to 1)
        """
        # Convert to numpy arrays for easier calculation
        a = np.array(vec1)
        b = np.array(vec2)
        
        # Compute cosine similarity
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def _estimate_space_saving(self, num_vectors: int) -> int:
        """
        Estimate space saved by removing vectors.
        
        Args:
            num_vectors: Number of vectors removed
            
        Returns:
            Estimated bytes saved
        """
        # Assuming 1KB per vector - adjust based on your actual vector size
        vector_size_bytes = 1024
        return num_vectors * vector_size_bytes
    
    async def generate_report(self) -> Dict[str, Any]:
        """
        Generate a human-readable report of the janitor operations.
        
        Returns:
            Dictionary with report details
        """
        kb_saved = self.stats["bytes_saved"] / 1024
        
        report = {
            "summary": (
                f"VectorJanitor completed: "
                f"{self.stats['duplicates_removed']} duplicates and "
                f"{self.stats['orphans_removed']} orphans purged "
                f"({kb_saved:.2f} KB)"
            ),
            "details": {
                "total_vectors": self.stats["total_vectors"],
                "duplicates_found": self.stats["duplicates_found"],
                "duplicates_removed": self.stats["duplicates_removed"],
                "orphans_found": self.stats["orphans_found"],
                "orphans_removed": self.stats["orphans_removed"],
                "space_saved_kb": kb_saved,
                "operation_time_seconds": self.stats["operation_time_seconds"],
                "start_time": self.stats["start_time"],
                "end_time": self.stats["end_time"],
                "dry_run": self.dry_run
            }
        }
        
        return report
