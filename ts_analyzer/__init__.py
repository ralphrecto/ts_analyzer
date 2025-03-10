"""
TypeScript Code Analyzer

A module for analyzing TypeScript codebases using TreeSitter.
Provides functionality to find imports, function calls, and other patterns.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Callable, Union, Generator, Set, Tuple, Optional
import json

try:
    from tree_sitter import Parser, Language
    # Import the TypeScript language from the installed Python bindings
    from tree_sitter_typescript import language_typescript
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure both tree-sitter and tree-sitter-typescript are installed.")
    print("Run: pip install tree-sitter tree-sitter-typescript")
    raise

# TreeSitter TypeScript language
TS_LANGUAGE = None

def initialize_ts_parser():
    """Initialize the TreeSitter TypeScript parser."""
    global TS_LANGUAGE
    
    # Check if the language is already loaded
    if TS_LANGUAGE is not None:
        return
    
    try:
        # Use the TypeScript language from the installed Python bindings
        # In newer versions of tree-sitter, we need to create a Language object from the language capsule
        TS_LANGUAGE = Language(language_typescript())
    except Exception as e:
        print(f"Error initializing TreeSitter: {e}")
        print("Make sure tree-sitter-typescript is installed correctly:")
        print("pip install tree-sitter-typescript")
        raise

class TypeScriptAnalyzer:
    """Analyzer for TypeScript code using TreeSitter."""
    
    def __init__(self, codebase_root: str):
        """
        Initialize the analyzer.
        
        Args:
            codebase_root: Root directory of the TypeScript codebase
        """
        self.codebase_root = Path(codebase_root).resolve()
        initialize_ts_parser()
        self.parser = Parser(TS_LANGUAGE)
        
        # Cache for parsed files
        self._parsed_files_cache = {}
    
    def find_ts_files(self, include_tsx: bool = True, exclude_node_modules: bool = True) -> List[Path]:
        """
        Find all TypeScript files in the codebase.
        
        Args:
            include_tsx: Whether to include .tsx files
            exclude_node_modules: Whether to exclude files in node_modules directories
        
        Returns:
            List of paths to TypeScript files
        """
        extensions = ['.ts']
        if include_tsx:
            extensions.append('.tsx')
            
        files = []
        for ext in extensions:
            found_files = list(self.codebase_root.glob(f"**/*{ext}"))
            
            if exclude_node_modules:
                # Filter out files from node_modules directories
                found_files = [f for f in found_files if "node_modules" not in f.parts]
                
            files.extend(found_files)
        
        return files
    
    def parse_file(self, file_path: Union[str, Path]) -> Any:
        """
        Parse a TypeScript file using TreeSitter.
        
        Args:
            file_path: Path to the file
            
        Returns:
            TreeSitter parse tree
        """
        file_path = Path(file_path)
        
        # Check cache first
        if str(file_path) in self._parsed_files_cache:
            return self._parsed_files_cache[str(file_path)]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = self.parser.parse(bytes(content, 'utf-8'))
            self._parsed_files_cache[str(file_path)] = tree
            return tree
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def clear_cache(self):
        """Clear the file parsing cache."""
        self._parsed_files_cache = {}
    
    def _traverse_tree(self, node, callback):
        """
        Recursively traverse the parse tree.
        
        Args:
            node: TreeSitter node
            callback: Function to call on each node
        """
        continue_traversal = callback(node)
        
        if continue_traversal is not False:  # Only stop if explicitly False
            for child in node.children:
                self._traverse_tree(child, callback)
    
    def find_imports(self, class_or_module_name: str) -> Dict[str, List[Dict]]:
        """
        Find all imports of a specific class or module.
        
        Args:
            class_or_module_name: Name of the class or module
            
        Returns:
            Dictionary mapping file paths to lists of import information
        """
        results = {}
        
        for file_path in self.find_ts_files():
            tree = self.parse_file(file_path)
            if not tree:
                continue
                
            file_imports = []
            
            def process_node(node):
                if node.type == 'import_statement' or node.type == 'import_declaration':
                    # Extract the import text
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        import_text = content[node.start_byte:node.end_byte]
                        
                    if class_or_module_name in import_text:
                        file_imports.append({
                            'line': node.start_point[0] + 1,
                            'text': import_text.strip(),
                            'import_type': node.type
                        })
            
            self._traverse_tree(tree.root_node, process_node)
            
            if file_imports:
                results[str(file_path)] = file_imports
                
        return results
    
    def find_function_calls(self, function_name: str, extract_first_arg: bool = False) -> Dict[str, List[Dict]]:
        """
        Find all calls to a specific function.
        
        Args:
            function_name: Name of the function
            extract_first_arg: Whether to extract the first argument of each call
            
        Returns:
            Dictionary mapping file paths to lists of function call information
        """
        results = {}
        
        for file_path in self.find_ts_files():
            tree = self.parse_file(file_path)
            if not tree:
                continue
                
            function_calls = []
            
            def process_node(node):
                # Look for call_expression nodes
                if node.type == 'call_expression':
                    # The first child should be the function identifier
                    if node.children and len(node.children) > 0:
                        function_node = node.children[0]
                        
                        # Get the function name
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            found_name = content[function_node.start_byte:function_node.end_byte]
                            
                            # If the function name matches what we're looking for
                            if found_name == function_name or found_name.endswith('.' + function_name):
                                call_info = {
                                    'line': node.start_point[0] + 1,
                                    'column': node.start_point[1],
                                    'text': content[node.start_byte:node.end_byte].strip()
                                }
                                
                                # Extract first argument if requested
                                if extract_first_arg and len(node.children) > 1:
                                    # The arguments are usually in the second child (arguments node)
                                    args_node = node.children[1]
                                    if args_node.type == 'arguments' and args_node.children and len(args_node.children) > 0:
                                        first_arg = args_node.children[0]
                                        call_info['first_arg'] = content[first_arg.start_byte:first_arg.end_byte].strip()
                                
                                function_calls.append(call_info)
            
            self._traverse_tree(tree.root_node, process_node)
            
            if function_calls:
                results[str(file_path)] = function_calls
                
        return results
    
    def find_class_definitions(self, class_name: str = None) -> Dict[str, List[Dict]]:
        """
        Find all class definitions, optionally filtering by name.
        
        Args:
            class_name: Optional name of the class to filter by
            
        Returns:
            Dictionary mapping file paths to lists of class information
        """
        results = {}
        
        for file_path in self.find_ts_files():
            tree = self.parse_file(file_path)
            if not tree:
                continue
                
            classes = []
            
            def process_node(node):
                if node.type == 'class_declaration':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Find the class name
                        class_name_node = None
                        for child in node.children:
                            if child.type == 'type_identifier':
                                class_name_node = child
                                break
                        
                        if class_name_node:
                            found_class_name = content[class_name_node.start_byte:class_name_node.end_byte]
                            
                            # If no specific class name is provided or it matches
                            if class_name is None or found_class_name == class_name:
                                classes.append({
                                    'name': found_class_name,
                                    'line': node.start_point[0] + 1,
                                    'column': node.start_point[1],
                                    'text': content[node.start_byte:node.end_byte]
                                })
            
            self._traverse_tree(tree.root_node, process_node)
            
            if classes:
                results[str(file_path)] = classes
                
        return results
    
    def custom_query(self, query_string: str) -> Dict[str, List[Dict]]:
        """
        Execute a custom TreeSitter query on the codebase.
        
        Args:
            query_string: TreeSitter query string
            
        Returns:
            Dictionary mapping file paths to lists of query results
        """
        results = {}
        
        try:
            query = TS_LANGUAGE.query(query_string)
        except Exception as e:
            print(f"Error creating query: {e}")
            return results
        
        for file_path in self.find_ts_files():
            tree = self.parse_file(file_path)
            if not tree:
                continue
                
            file_results = []
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    content_bytes = bytes(content, 'utf-8')
                
                # Get all captures from the query
                captures = query.captures(tree.root_node)
                
                # Process the captures, handling different structures from different TreeSitter versions
                for item in captures:
                    # Handle tuple format (could be 2-tuple or 3-tuple depending on TreeSitter version)
                    if isinstance(item, tuple):
                        # We need at least a node and a capture name
                        if len(item) >= 2:
                            # First element is always the node
                            node = item[0]
                            
                            # Second element is often the capture name in older versions
                            # In newer versions, it might be the capture index, and the name is third
                            if isinstance(item[1], str):
                                capture_name = item[1]
                            elif len(item) >= 3 and isinstance(item[2], str):
                                capture_name = item[2]
                            else:
                                # Default if we can't find a string capture name
                                capture_name = "unknown"
                            
                            file_results.append({
                                'capture': capture_name,
                                'line': node.start_point[0] + 1,
                                'column': node.start_point[1],
                                'text': content[node.start_byte:node.end_byte]
                            })
                    else:
                        # Skip if it's not a tuple - likely a string or other unexpected format
                        continue
                        
            except Exception as e:
                print(f"Error querying {file_path}: {e}")
                continue
            
            if file_results:
                results[str(file_path)] = file_results
                
        return results

    def generate_stats(self) -> Dict[str, Any]:
        """
        Generate statistics about the codebase.
        
        Returns:
            Dictionary of statistics
        """
        stats = {
            'total_files': 0,  # Renamed from file_count to match notebook expectations
            'total_lines': 0,
            'imports': 0,
            'exports': 0,
            'classes': 0,
            'interfaces': 0,
            'functions': 0,
            'type_aliases': 0,
            'file_sizes': {}  # Added to store file sizes for the notebook
        }
        
        for file_path in self.find_ts_files():
            stats['total_files'] += 1
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.readlines()
                    line_count = len(content)
                    stats['total_lines'] += line_count
                    stats['file_sizes'][str(file_path)] = line_count
            except Exception:
                continue
            
            tree = self.parse_file(file_path)
            if not tree:
                continue
            
            def process_node(node):
                if node.type == 'import_statement':
                    stats['imports'] += 1
                elif node.type == 'export_statement':
                    stats['exports'] += 1
                elif node.type == 'class_declaration':
                    stats['classes'] += 1
                elif node.type == 'interface_declaration':
                    stats['interfaces'] += 1
                elif node.type == 'function_declaration':
                    stats['functions'] += 1
                elif node.type == 'type_alias_declaration':
                    stats['type_aliases'] += 1
            
            self._traverse_tree(tree.root_node, process_node)
        
        # Calculate average lines per file
        if stats['total_files'] > 0:
            stats['avg_lines_per_file'] = stats['total_lines'] / stats['total_files']
        else:
            stats['avg_lines_per_file'] = 0
            
        return stats 