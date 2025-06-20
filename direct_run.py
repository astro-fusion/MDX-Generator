#!/usr/bin/env python3
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
        log_text.insert("end", f"{msg}\n")
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
