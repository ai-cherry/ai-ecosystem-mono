#!/usr/bin/env python3
"""
Script to check for redundancies, circular references, and syntax errors in the codebase.
"""

import os
import sys
import importlib
import ast
import re
from collections import defaultdict, deque
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """Analyzes code for various issues."""
    
    def __init__(self, root_dir):
        """Initialize with the root directory to analyze."""
        self.root_dir = root_dir
        self.import_graph = defaultdict(set)
        self.all_modules = set()
        self.redundant_modules = []
        self.redundant_implementations = []
        self.syntax_errors = []
        self.circular_refs = []
        
    def find_python_files(self):
        """Find all Python files in the codebase."""
        python_files = []
        
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
                    
        return python_files
    
    def check_syntax(self, file_path):
        """Check if a Python file has syntax errors."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            ast.parse(content)
            return None
        except SyntaxError as e:
            return (file_path, e.lineno, e.msg)
        except Exception as e:
            return (file_path, 0, str(e))
    
    def analyze_imports(self, file_path):
        """Analyze imports in a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            module_path = os.path.relpath(file_path, self.root_dir)
            module_path = os.path.splitext(module_path)[0].replace('/', '.')
            self.all_modules.add(module_path)
            
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = node.module
                        if node.level > 0:  # Relative import
                            # Calculate the parent module
                            parts = module_path.split('.')
                            parent_parts = parts[:-node.level]
                            if not parent_parts:
                                # If parent_parts is empty, we're at the root
                                parent_module = ""
                            else:
                                parent_module = ".".join(parent_parts)
                                
                            if not module:  # from . import x
                                full_module = parent_module
                            else:  # from .submodule import x
                                full_module = f"{parent_module}.{module}" if parent_module else module
                                
                            imports.append(full_module)
                        else:
                            imports.append(module)
            
            for imported_module in imports:
                if imported_module and imported_module != module_path:
                    self.import_graph[module_path].add(imported_module)
                    
        except Exception as e:
            logger.error(f"Error analyzing imports in {file_path}: {e}")
    
    def find_circular_references(self):
        """Find circular references in the import graph."""
        visited = set()
        path = []
        
        def dfs(node):
            if node in path:
                cycle = path[path.index(node):] + [node]
                self.circular_refs.append(cycle)
                return
                
            if node in visited:
                return
                
            visited.add(node)
            path.append(node)
            
            for neighbor in self.import_graph.get(node, []):
                if neighbor in self.all_modules:  # Only check modules that exist
                    dfs(neighbor)
                    
            path.pop()
        
        for module in self.all_modules:
            dfs(module)
    
    def find_redundant_modules(self):
        """Find redundant module implementations."""
        module_names = defaultdict(list)
        
        for module in self.all_modules:
            parts = module.split('.')
            if len(parts) > 1:
                base_name = parts[-1]
                module_names[base_name].append(module)
        
        for name, modules in module_names.items():
            if len(modules) > 1 and not name.startswith('__'):
                if name in ['interfaces', 'models', 'config']:
                    # Common module names - only report if they're very similar
                    # Check for similarity in purpose
                    self.redundant_modules.append((name, modules))
                elif len(modules) > 1:
                    self.redundant_modules.append((name, modules))
    
    def find_redundant_implementations(self):
        """Find redundant implementations of similar functionality."""
        # Look for OpenAI service registrations
        llm_factory_paths = [m for m in self.all_modules if m.endswith('factory') and 'llm' in m]
        
        for factory_module in llm_factory_paths:
            try:
                module_path = factory_module.replace('.', '/')
                file_path = os.path.join(self.root_dir, f"{module_path}.py")
                
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                # Check for multiple registrations of the same service
                matches = re.findall(r'register_\w+\([\'"](\w+)[\'"]', content)
                
                # Find duplicates
                seen = set()
                duplicates = []
                
                for m in matches:
                    lower_m = m.lower()
                    if lower_m in seen:
                        duplicates.append(m)
                    seen.add(lower_m)
                
                if duplicates:
                    self.redundant_implementations.append((factory_module, duplicates))
            except Exception as e:
                logger.error(f"Error checking redundant implementations in {factory_module}: {e}")
    
    def run_analysis(self):
        """Run the full analysis."""
        python_files = self.find_python_files()
        logger.info(f"Found {len(python_files)} Python files to analyze")
        
        # Check syntax
        for file_path in python_files:
            error = self.check_syntax(file_path)
            if error:
                self.syntax_errors.append(error)
                
        logger.info(f"Found {len(self.syntax_errors)} files with syntax errors")
        
        # Analyze imports
        for file_path in python_files:
            self.analyze_imports(file_path)
            
        logger.info(f"Analyzed imports in {len(self.all_modules)} modules")
        
        # Find circular references
        self.find_circular_references()
        logger.info(f"Found {len(self.circular_refs)} circular references")
        
        # Find redundant modules
        self.find_redundant_modules()
        logger.info(f"Found {len(self.redundant_modules)} potentially redundant modules")
        
        # Find redundant implementations
        self.find_redundant_implementations()
        logger.info(f"Found {len(self.redundant_implementations)} redundant implementations")
        
    def generate_report(self):
        """Generate a detailed report of the analysis."""
        report = []
        report.append("# Code Analysis Report")
        report.append("\n## Summary")
        report.append(f"- Found {len(self.syntax_errors)} files with syntax errors")
        report.append(f"- Found {len(self.circular_refs)} circular references")
        report.append(f"- Found {len(self.redundant_modules)} potentially redundant modules")
        report.append(f"- Found {len(self.redundant_implementations)} redundant implementations")
        
        if self.syntax_errors:
            report.append("\n## Syntax Errors")
            for file_path, line_num, msg in self.syntax_errors:
                rel_path = os.path.relpath(file_path, self.root_dir)
                report.append(f"- {rel_path}, line {line_num}: {msg}")
        
        if self.circular_refs:
            report.append("\n## Circular References")
            for i, cycle in enumerate(self.circular_refs, 1):
                report.append(f"\n### Circular Reference {i}")
                report.append(" -> ".join(cycle))
        
        if self.redundant_modules:
            report.append("\n## Potentially Redundant Modules")
            for name, modules in self.redundant_modules:
                report.append(f"\n### Module: {name}")
                for module in modules:
                    report.append(f"- {module}")
        
        if self.redundant_implementations:
            report.append("\n## Redundant Implementations")
            for module, duplicates in self.redundant_implementations:
                report.append(f"\n### In {module}")
                for dup in duplicates:
                    report.append(f"- Duplicate registration: {dup}")
        
        return "\n".join(report)

def main():
    """Main entry point for the script."""
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = os.getcwd()
        
    analyzer = CodeAnalyzer(root_dir)
    analyzer.run_analysis()
    
    report = analyzer.generate_report()
    print(report)
    
    # Optionally write to file
    with open('code_analysis_report.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    # Return non-zero exit code if issues were found
    return 1 if (analyzer.syntax_errors or analyzer.circular_refs) else 0

if __name__ == "__main__":
    sys.exit(main())
