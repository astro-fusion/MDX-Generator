"""
Core processing modules for the MDX Generator Tool.

This package contains modules that perform different steps in the MDX file
processing pipeline, from normalizing filenames to generating navigation links.
"""

# We can't directly import modules with numeric prefixes using dot notation
# Instead, we'll use importlib to dynamically import them when needed

import os
import importlib.util
import sys
from pathlib import Path

# Define available modules and their main functions
MODULE_REGISTRY = {
    "normalize_filenames": {
        "file": "00_normalize_filenames.py",
        "functions": ["process_directory", "normalize_filename"]
    },
    "fix_mdx_frontmatter": {
        "file": "01a_fix_mdx_frontmatter.py", 
        "functions": ["process_mdx_file", "fix_yaml_line_for_quotes"]
    },
    "generate_root_meta_json": {
        "file": "01b_generate_root_meta_json.py",
        "functions": ["generate_meta_json"]
    },
    "generate_index": {
        "file": "02_generate_index.py",
        "functions": ["generate_index_from_meta"]
    },
    "generate_all_meta_json": {
        "file": "03_generate_all_meta_json.py",
        "functions": ["generate_meta_json"]
    },
    "validate_meta_json": {
        "file": "04_validate_meta_json.py",
        "functions": ["main"]
    },
    "generate_nav_links": {
        "file": "05_generate_nav_links.py",
        "functions": ["generate_nav_links"]
    }
}

def get_module(module_name):
    """Get a module by its logical name (without the numeric prefix)"""
    if module_name not in MODULE_REGISTRY:
        raise ImportError(f"Module {module_name} not found in registry")
        
    module_info = MODULE_REGISTRY[module_name]
    module_path = os.path.join(os.path.dirname(__file__), module_info["file"])
    
    if not os.path.exists(module_path):
        raise ImportError(f"Module file not found: {module_path}")
    
    # Import the module from file path
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if not module_spec:
        raise ImportError(f"Failed to load spec for {module_path}")
        
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    
    return module

# Expose the get_module function as the primary API for this package
__all__ = ["get_module", "MODULE_REGISTRY"]
