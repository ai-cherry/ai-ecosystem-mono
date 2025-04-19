#!/usr/bin/env python
"""
Auto-Index Changed Files for Embeddings

This script is intended to be used as a pre-commit hook to automatically
index new or changed files into the vector store. This ensures that the
AI agents always have access to the latest code and documentation.

Usage:
    Automatically through pre-commit
    Or manually: python scripts/index_changed_files.py [files...]
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path to allow imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Try imports, but handle gracefully if dependencies aren't available
try:
    from shared.memory.vectorstore import VectorStore
except ImportError:
    logger.warning("Could not import VectorStore. Make sure shared module is in PYTHONPATH.")
    
    class DummyVectorStore:
        """Dummy class for when VectorStore is not available."""
        def upsert_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
            logger.info(f"Would index text with metadata: {metadata}")
            return "dummy-id"
    
    VectorStore = DummyVectorStore

# File extensions and paths to include/exclude
INCLUDED_EXTENSIONS = {'.py', '.md', '.txt', '.js', '.ts', '.jsx', '.tsx'}
EXCLUDED_PATHS = {
    'venv', '.venv', '.git', '__pycache__', 'node_modules', 
    '.pytest_cache', '.ruff_cache', '.mypy_cache'
}

def should_index_file(file_path: str) -> bool:
    """
    Determine if a file should be indexed based on extension and path.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file should be indexed, False otherwise
    """
    path = Path(file_path)
    
    # Check if file exists
    if not path.exists() or not path.is_file():
        return False
    
    # Check if file extension is included
    if path.suffix not in INCLUDED_EXTENSIONS:
        return False
    
    # Check if file is in an excluded path
    for excluded in EXCLUDED_PATHS:
        if excluded in str(path):
            return False
    
    return True

def get_file_metadata(file_path: str) -> Dict[str, Any]:
    """
    Generate metadata for a file to be indexed.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dictionary of metadata
    """
    path = Path(file_path)
    return {
        "file_path": str(path),
        "file_name": path.name,
        "file_type": path.suffix.lstrip('.'),
        "directory": str(path.parent),
        "id": f"file:{str(path)}",
        "doc_type": "code_file",
        "indexed_at": None  # Will be filled in by the vector store
    }

def index_file(file_path: str, vector_store: Any) -> bool:
    """
    Index a file into the vector store.
    
    Args:
        file_path: Path to the file
        vector_store: Vector store instance
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip empty files
        if not content.strip():
            logger.info(f"Skipping empty file: {file_path}")
            return True
        
        # Get metadata
        metadata = get_file_metadata(file_path)
        
        # Index content into vector store
        vector_id = vector_store.upsert_text(content, metadata)
        logger.info(f"Indexed {file_path} with ID {vector_id}")
        
        return True
    except Exception as e:
        logger.error(f"Error indexing {file_path}: {e}")
        return False

def index_files(file_paths: List[str]) -> int:
    """
    Index multiple files into the vector store.
    
    Args:
        file_paths: List of file paths to index
        
    Returns:
        Number of files successfully indexed
    """
    # Initialize vector store
    try:
        vector_store = VectorStore()
    except Exception as e:
        logger.error(f"Could not initialize vector store: {e}")
        return 0
    
    successful = 0
    
    for file_path in file_paths:
        if should_index_file(file_path):
            if index_file(file_path, vector_store):
                successful += 1
        else:
            logger.debug(f"Skipping file: {file_path}")
    
    return successful

def main():
    """Main entry point."""
    # Get changed files from command line arguments
    files = sys.argv[1:]
    
    if not files:
        logger.info("No files provided. Exiting.")
        return 0
    
    logger.info(f"Processing {len(files)} files...")
    indexed_count = index_files(files)
    logger.info(f"Successfully indexed {indexed_count} files.")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
