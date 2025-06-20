#!/usr/bin/env python3
"""
Hotfix for circular import issue in core/__init__.py
"""

import os
from pathlib import Path

def fix_core_init_file():
    """Fix the circular import issue in src/core/__init__.py"""
    core_init_path = Path("src/core/__init__.py")
    
    if not core_init_path.exists():
        print(f"Error: {core_init_path} not found!")
        return False
    
    print(f"Fixing circular import in {core_init_path}...")
    
    # Create a new, simpler __init__.py file that avoids circular imports
    new_content = '''"""
Core processing modules for the MDX Generator Tool.

This package contains modules that perform different steps in the MDX file
processing pipeline, from normalizing filenames to generating navigation links.
"""

# Import specific functions directly to avoid circular imports
# These are the main entry points for each module

try:
    from .00_normalize_filenames import process_directory, normalize_filename
except ImportError:
    print("Warning: Could not import normalize_filenames module")

try:
    from .01a_fix_mdx_frontmatter import process_mdx_file, fix_yaml_line_for_quotes
except ImportError:
    print("Warning: Could not import fix_mdx_frontmatter module")
    
try:
    from .01b_generate_root_meta_json import generate_meta_json as generate_root_meta_json
except ImportError:
    print("Warning: Could not import generate_root_meta_json module")
    
try:
    from .02_generate_index import generate_index_from_meta
except ImportError:
    print("Warning: Could not import generate_index module")
    
try:
    from .03_generate_all_meta_json import generate_meta_json
except ImportError:
    print("Warning: Could not import generate_all_meta_json module")
    
try:
    from .04_validate_meta_json import main as validate_meta_json
except ImportError:
    print("Warning: Could not import validate_meta_json module")
    
try:
    from .05_generate_nav_links import generate_nav_links
except ImportError:
    print("Warning: Could not import generate_nav_links module")
'''
    
    # Write the new content to the file
    with open(core_init_path, 'w') as f:
        f.write(new_content)
    
    print(f"Successfully fixed {core_init_path}")
    return True

def fix_module_imports():
    """Fix direct module imports in main.py"""
    main_path = Path("main.py")
    
    if not main_path.exists():
        print(f"Error: {main_path} not found!")
        return False
    
    print(f"Fixing module imports in {main_path}...")
    
    with open(main_path, 'r') as f:
        content = f.read()
    
    # Modify the module import line to directly import functions
    fixed_content = content.replace(
        "module_name = f\"src.core.{selected_func}\"",
        "# Import the file directly instead of through __init__.py\n                    module_name = f\"src.core.{selected_func}\"\n                    # As a fallback, try importing without the module prefix\n                    if selected_func.startswith('0'):\n                        try_module = selected_func"
    )
    
    # Also fix the module usage part
    fixed_content = fixed_content.replace(
        "# Find the main function",
        "# Find the main function - try multiple possible entry point names"
    )
    
    fixed_content = fixed_content.replace(
        "main_func = getattr(module, 'main', None) or getattr(module, 'process_directory', None)",
        "main_func = getattr(module, 'main', None) or getattr(module, 'process_directory', None) or getattr(module, 'generate_meta_json', None) or getattr(module, 'generate_index_from_meta', None) or getattr(module, 'generate_nav_links', None)"
    )
    
    # Write the fixed content back
    with open(main_path, 'w') as f:
        f.write(fixed_content)
    
    print(f"Fixed module imports in {main_path}")
    return True

def create_direct_import_script():
    """Create a script for directly importing modules without __init__.py"""
    script_path = Path("direct_run.py")
    
    print(f"Creating {script_path} for direct module imports...")
    
    content = '''#!/usr/bin/env python3
"""
Direct module execution script to bypass circular import issues
"""

import os
import sys
import importlib.util
import tkinter as tk
from tkinter import filedialog, messagebox

def import_module_from_path(module_path):
    """Import a module directly from its file path"""
    module_name = os.path.basename(module_path).replace('.py', '')
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if not spec or not spec.loader:
        raise ImportError(f"Could not load spec for {module_path}")
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_module():
    """Run a specific module function on a directory"""
    # Create simple UI
    root = tk.Tk()
    root.title("MDX Generator - Direct Module Runner")
    root.geometry("500x400")
    
    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)
    
    # Header
    tk.Label(frame, text="MDX Generator Direct Module Runner", font=("Arial", 14, "bold")).pack(pady=10)
    
    # Directory selection
    dir_frame = tk.Frame(frame)
    dir_frame.pack(fill="x", pady=10)
    
    tk.Label(dir_frame, text="Directory:").pack(side="left")
    dir_var = tk.StringVar()
    dir_entry = tk.Entry(dir_frame, textvariable=dir_var)
    dir_entry.pack(side="left", fill="x", expand=True, padx=5)
    
    def browse():
        directory = filedialog.askdirectory()
        if directory:
            dir_var.set(directory)
    
    tk.Button(dir_frame, text="Browse", command=browse).pack(side="left")
    
    # Module selection
    module_frame = tk.Frame(frame)
    module_frame.pack(fill="x", pady=10)
    
    tk.Label(module_frame, text="Module:").pack(side="left")
    
    # Find available modules
    src_core_dir = os.path.join("src", "core")
    if not os.path.exists(src_core_dir):
        src_core_dir = "core"
    
    modules = [f for f in os.listdir(src_core_dir) if f.endswith('.py') and not f.startswith('__')]
    
    module_var = tk.StringVar()
    if modules:
        module_var.set(modules[0])
    
    module_menu = tk.OptionMenu(module_frame, module_var, *modules)
    module_menu.pack(side="left", fill="x", expand=True, padx=5)
    
    # Log area
    log_frame = tk.LabelFrame(frame, text="Log")
    log_frame.pack(fill="both", expand=True, pady=10)
    
    log_text = tk.Text(log_frame, height=10)
    log_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    # Scrollbar
    scrollbar = tk.Scrollbar(log_text)
    scrollbar.pack(side="right", fill="y")
    log_text.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=log_text.yview)
    
    def log(msg):
        log_text.insert("end", f"{msg}\\n")
        log_text.see("end")
    
    # Function to run the module
    def run():
        directory = dir_var.get()
        module_file = module_var.get()
        
        if not directory:
            messagebox.showerror("Error", "Please select a directory")
            return
        
        if not os.path.isdir(directory):
            messagebox.showerror("Error", "Selected directory does not exist")
            return
        
        log(f"Running {module_file} on {directory}...")
        
        try:
            # Import the module directly from its file
            module_path = os.path.join(src_core_dir, module_file)
            module = import_module_from_path(module_path)
            
            # Try to find the main function
            main_func = None
            for func_name in ['main', 'process_directory', 'generate_meta_json', 
                            'generate_index_from_meta', 'generate_nav_links',
                            'fix_mdx_frontmatter']:
                if hasattr(module, func_name):
                    main_func = getattr(module, func_name)
                    break
            
            if main_func:
                log(f"Found function: {main_func.__name__}")
                result = main_func(directory)
                log(f"Result: {result}")
            else:
                log(f"No suitable function found in {module_file}")
                
        except Exception as e:
            log(f"Error: {str(e)}")
            import traceback
            log(traceback.format_exc())
    
    # Run button
    tk.Button(frame, text="Run Module", command=run).pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    run_module()
'''
    
    with open(script_path, 'w') as f:
        f.write(content)
    
    # Make the script executable
    os.chmod(script_path, 0o755)
    
    print(f"Created {script_path} - you can run this script directly to bypass import issues")
    return True

if __name__ == "__main__":
    print("Starting circular import hotfix...")
    
    fixed_init = fix_core_init_file()
    fixed_imports = fix_module_imports()
    created_script = create_direct_import_script()
    
    if fixed_init and fixed_imports and created_script:
        print("\nFixes complete! Please try running your application again.")
        print("If problems persist, try running the direct_run.py script:")
        print("  python direct_run.py")
    else:
        print("\nSome fixes could not be applied. Please check the errors above.")