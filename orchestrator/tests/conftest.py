"""
Configuration file for pytest.

This module ensures proper import paths are set up for the tests.
"""

import os
import sys
from pathlib import Path

# Add the appropriate directories to Python path to enable imports
project_root = str(Path(__file__).parent.parent.parent)  # Root of the whole project
orchestrator_dir = str(Path(__file__).parent.parent)     # Orchestrator directory

# Add paths to sys.path if they're not already there
for path in [project_root, orchestrator_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Create a symbolic link to make orchestrator imports work
import pytest

@pytest.fixture(scope="session", autouse=True)
def patch_imports():
    """
    Patch import system to handle both relative and absolute imports.
    This allows tests to use either 'from app.xyz import abc' or 
    'from orchestrator.app.xyz import abc' syntax.
    """
    import builtins
    original_import = builtins.__import__
    
    def patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        # Try normal import first
        try:
            return original_import(name, globals, locals, fromlist, level)
        except ImportError as e:
            # If importing from orchestrator.app.*, try importing from app.* instead
            if name.startswith('orchestrator.app.'):
                new_name = name[len('orchestrator.'):]
                try:
                    return original_import(new_name, globals, locals, fromlist, level)
                except ImportError:
                    # Re-raise the original error if the modified import also fails
                    raise e
            # If the original error was for a non-orchestrator import, re-raise it
            raise
    
    builtins.__import__ = patched_import
    yield
    builtins.__import__ = original_import
