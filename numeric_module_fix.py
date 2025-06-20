#!/usr/bin/env python3
"""
Fix for the invalid decimal literal error in __init__.py
"""

import os

def fix_init_file():
    """Fix the __init__.py file to properly handle numeric module names"""
    init_path = "src/core/__init__.py"
    
    print(f"Fixing numeric module import issue in {init_path}...")
    
    # Create a new __init__.py file that avoids direct imports of numeric modules
    new_content = '''"""
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
'''
    
    # Write the new content to the file
    with open(init_path, 'w') as f:
        f.write(new_content)
    
    print(f"Successfully fixed {init_path}")

def fix_main_module_import():
    """Fix the module import in main.py to use the new registry approach"""
    main_path = "main.py"
    
    print(f"Fixing module import in {main_path}...")
    
    with open(main_path, 'r') as f:
        content = f.read()
    
    # Find the try block where module import happens
    import_section = """                try:
                    # Import the file directly instead of through __init__.py
                    module_name = f"src.core.{selected_func}"
                    # As a fallback, try importing without the module prefix
                    if selected_func.startswith('0'):
                        try_module = selected_func
                    __import__(module_name)
                    module = sys.modules[module_name]"""
    
    # Replace it with a version that uses importlib directly
    new_import_section = """                try:
                    # Use direct file import for modules with numeric names
                    module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                             "src", "core", f"{selected_func}.py")
                    if not os.path.exists(module_path):
                        raise ImportError(f"Module file not found: {module_path}")
                        
                    # Import the module from file path using importlib
                    import importlib.util
                    module_spec = importlib.util.spec_from_file_location(selected_func, module_path)
                    if not module_spec:
                        raise ImportError(f"Failed to load spec for {module_path}")
                        
                    module = importlib.util.module_from_spec(module_spec)
                    module_spec.loader.exec_module(module)"""
                    
    fixed_content = content.replace(import_section, new_import_section)
    
    # Write the fixed content back
    with open(main_path, 'w') as f:
        f.write(fixed_content)
    
    print(f"Fixed module import in {main_path}")

if __name__ == "__main__":
    print("Starting numeric module name fix...")
    
    fix_init_file()
    fix_main_module_import()
    
    print("\nFixes complete! Please try running your application again:")
    print("  python main.py --safe-mode")
    print("\nIf problems persist, try using the direct_run.py script:")
    print("  python direct_run.py")