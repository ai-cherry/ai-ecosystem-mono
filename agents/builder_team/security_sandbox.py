"""
Security Sandbox for BuilderAgent code generation and execution.

This module provides security controls and validation for code generated
by AI agents, preventing potentially harmful operations and enforcing
safety constraints.
"""

import ast
import logging
import os
import re
import time
import traceback
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from shared.config import builder_agent_settings

# Configure logger
logger = logging.getLogger(__name__)


class SecurityViolation(Exception):
    """Exception raised when a security violation is detected."""
    pass


class ImportValidator(ast.NodeVisitor):
    """AST visitor that validates import statements in Python code."""
    
    def __init__(self):
        """Initialize the validator with allowed and blocked patterns."""
        self.allowed_patterns = [
            re.compile(pattern) for pattern in builder_agent_settings.ALLOWED_IMPORT_PATTERNS
        ]
        self.blocked_patterns = [
            re.compile(pattern) for pattern in builder_agent_settings.BLOCKED_IMPORT_PATTERNS
        ]
        self.violations = []
    
    def visit_Import(self, node: ast.Import) -> None:
        """Visit Import nodes (e.g., 'import os')."""
        for name in node.names:
            self._check_import(name.name, node)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit ImportFrom nodes (e.g., 'from os import path')."""
        if node.module:
            module_name = node.module
            self._check_import(module_name, node)
        self.generic_visit(node)
    
    def _check_import(self, module_name: str, node: ast.AST) -> None:
        """Check if an import is allowed based on patterns."""
        # Check if explicitly blocked
        for pattern in self.blocked_patterns:
            if pattern.search(module_name):
                self.violations.append({
                    "type": "blocked_import",
                    "name": module_name,
                    "line": node.lineno,
                    "message": f"Import of '{module_name}' is blocked by policy"
                })
                return
        
        # If no allowed patterns defined, all non-blocked imports are allowed
        if not self.allowed_patterns:
            return
            
        # Check if explicitly allowed
        for pattern in self.allowed_patterns:
            if pattern.search(module_name):
                return
                
        # If we get here, import is not explicitly allowed
        self.violations.append({
            "type": "unauthorized_import",
            "name": module_name,
            "line": node.lineno,
            "message": f"Import of '{module_name}' is not in the allowed list"
        })


class FileAccessValidator(ast.NodeVisitor):
    """AST visitor that checks for file operations outside allowed paths."""
    
    def __init__(self):
        """Initialize the validator with allowed write paths."""
        self.allowed_paths = [
            os.path.abspath(path) for path in builder_agent_settings.ALLOWED_WRITE_PATHS
        ]
        self.violations = []
    
    def visit_Call(self, node: ast.Call) -> None:
        """Visit Call nodes to detect file operations."""
        # Check for open() calls with write modes
        if isinstance(node.func, ast.Name) and node.func.id == 'open' and len(node.args) >= 1:
            # Check the mode argument if present
            mode = "r"  # Default mode is read
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Str):
                mode = node.args[1].s
            
            # Only check write operations
            if 'w' in mode or 'a' in mode or '+' in mode:
                # Try to get the filename
                if isinstance(node.args[0], ast.Str):
                    filename = node.args[0].s
                    self._check_path(filename, node)
        
        # Check for other file manipulation functions
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            dangerous_funcs = {'write', 'writelines', 'truncate', 'unlink', 'remove', 'rmdir', 'rmtree'}
            
            if func_name in dangerous_funcs:
                self.violations.append({
                    "type": "file_operation",
                    "operation": func_name,
                    "line": node.lineno,
                    "message": f"Potentially unsafe file operation: {func_name}"
                })
        
        self.generic_visit(node)
    
    def _check_path(self, path: str, node: ast.AST) -> None:
        """Check if a file path is in the allowed list."""
        abs_path = os.path.abspath(path)
        
        # Check if path is within allowed paths
        for allowed_path in self.allowed_paths:
            if abs_path.startswith(allowed_path):
                return
        
        self.violations.append({
            "type": "unauthorized_path",
            "path": path,
            "line": node.lineno,
            "message": f"File operation on '{path}' is outside allowed paths"
        })


class CodeSandbox:
    """
    Sandbox for validating and executing generated code.
    
    This class provides a secure environment for validating and executing
    code generated by AI agents, with strict security controls.
    """
    
    def __init__(self):
        """Initialize the sandbox with security controls."""
        # Use configured settings or defaults
        self.enable_code_generation = builder_agent_settings.CODE_GENERATION_ENABLED
        self.timeout_seconds = builder_agent_settings.MAX_EXECUTION_TIME_SECONDS
    
    def validate_code(self, code: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate code for security violations.
        
        Args:
            code: Python code to validate
            
        Returns:
            Tuple of (is_valid, violations)
        """
        if not self.enable_code_generation:
            return False, [{
                "type": "disabled",
                "message": "Code generation is disabled in the current configuration"
            }]
        
        violations = []
        
        try:
            # Parse the code to an AST
            tree = ast.parse(code)
            
            # Check for import violations
            import_validator = ImportValidator()
            import_validator.visit(tree)
            violations.extend(import_validator.violations)
            
            # Check for file access violations
            file_validator = FileAccessValidator()
            file_validator.visit(tree)
            violations.extend(file_validator.violations)
            
            # Check for other dangerous patterns (could be expanded)
            # For example: eval, exec, os.system, subprocess, etc.
            
            # Add more validators as needed
            
            is_valid = len(violations) == 0
            return is_valid, violations
            
        except SyntaxError as e:
            return False, [{
                "type": "syntax_error",
                "line": e.lineno,
                "message": f"Syntax error: {str(e)}"
            }]
        except Exception as e:
            return False, [{
                "type": "validation_error",
                "message": f"Error validating code: {str(e)}"
            }]
    
    @contextmanager
    def timeout(self, seconds: int):
        """
        Context manager for timing out operations.
        
        Args:
            seconds: Timeout in seconds
        
        Raises:
            TimeoutError: If the operation takes longer than the specified timeout
        """
        def _handle_timeout(signum, frame):
            raise TimeoutError(f"Operation timed out after {seconds} seconds")
        
        # Set timeout only if the platform supports it
        try:
            import signal
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            
            try:
                yield
            finally:
                signal.alarm(0)  # Disable the alarm
                
        except (ImportError, AttributeError):
            # signal.SIGALRM not available on all platforms (e.g., Windows)
            # Fall back to a less reliable method
            start_time = time.time()
            yield
            if time.time() - start_time > seconds:
                logger.warning(f"Operation took longer than {seconds} seconds, but timeout couldn't be enforced on this platform")
    
    def execute_code(
        self, 
        code: str, 
        global_vars: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute code in a sandboxed environment.
        
        Args:
            code: Python code to execute
            global_vars: Optional global variables for execution context
            timeout_seconds: Optional custom timeout
            
        Returns:
            Dictionary with execution results and metadata
        """
        # First, validate the code
        is_valid, violations = self.validate_code(code)
        if not is_valid:
            return {
                "success": False,
                "error": "Code validation failed",
                "violations": violations,
                "result": None,
                "output": None
            }
        
        # Setup execution environment
        if global_vars is None:
            global_vars = {}
        
        # Create a restricted local environment
        local_vars = {}
        
        # Add a dict to capture stdout
        output_capture = []
        
        # Prepare the execution context
        restricted_builtins = {}
        for k in dir(__builtins__):
            if k not in {'eval', 'exec', 'compile', '__import__', 'open'}:
                try:
                    restricted_builtins[k] = getattr(__builtins__, k)
                except AttributeError:
                    pass
                    
        exec_globals = dict(global_vars)
        exec_globals["print"] = lambda *args, **kwargs: output_capture.append(" ".join(str(a) for a in args))
        exec_globals["__builtins__"] = restricted_builtins
        
        # Add a safe version of open that checks paths
        def safe_open(file, mode="r", *args, **kwargs):
            if 'w' in mode or 'a' in mode or '+' in mode:
                abs_path = os.path.abspath(file)
                allowed = False
                for allowed_path in [os.path.abspath(p) for p in builder_agent_settings.ALLOWED_WRITE_PATHS]:
                    if abs_path.startswith(allowed_path):
                        allowed = True
                        break
                
                if not allowed:
                    raise SecurityViolation(f"Attempt to write to unauthorized path: {file}")
            
            return open(file, mode, *args, **kwargs)
        
        exec_globals["open"] = safe_open
        
        # Execute the code with timeout
        timeout_secs = timeout_seconds or self.timeout_seconds
        result = None
        error = None
        
        try:
            with self.timeout(timeout_secs):
                # Execute the code
                exec(code, exec_globals, local_vars)
                
                # Get the result if defined
                result = local_vars.get('result', None)
        
        except TimeoutError as e:
            error = f"Execution timed out after {timeout_secs} seconds"
            logger.warning(error)
        
        except SecurityViolation as e:
            error = f"Security violation: {str(e)}"
            logger.error(error)
        
        except Exception as e:
            error = f"Execution error: {str(e)}\n{traceback.format_exc()}"
            logger.error(error)
        
        # Return the execution results
        return {
            "success": error is None,
            "error": error,
            "result": result,
            "output": "\n".join(output_capture),
            "local_vars": {k: v for k, v in local_vars.items() if not k.startswith("_")}
        }


def create_github_pr(code_files: Dict[str, str], pr_title: str, description: str) -> Dict[str, Any]:
    """
    Create a GitHub Pull Request for the generated code.
    
    This function is a placeholder for integrating with GitHub's API to create
    a pull request containing the generated code, which can then be reviewed
    by a human before being merged.
    
    Args:
        code_files: Dictionary mapping file paths to code content
        pr_title: Title for the Pull Request
        description: Description for the Pull Request
        
    Returns:
        Dictionary with the PR details (URL, ID, etc.)
    """
    # TODO: Implement GitHub API integration
    logger.info(f"Would create PR: {pr_title}")
    logger.info(f"Description: {description}")
    logger.info(f"Files: {list(code_files.keys())}")
    
    # Return mock PR info for now
    return {
        "url": "https://github.com/org/repo/pull/123",
        "id": "123",
        "status": "created",
        "requires_approval": builder_agent_settings.REQUIRE_PR_APPROVAL
    }
