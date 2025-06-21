#!/usr/bin/env python3
"""
MDX Generator Tool

A GUI application for processing and fixing MDX files generated from AI outputs.
"""

import os
import sys
from utils.logging_utils import setup_logger, set_gui_log_callback
from utils.settings import update_last_directory, get_last_directory

def setup_emergency_exit():
    """Set up emergency exit after 10 minutes to prevent zombies."""
    import threading
    import time
    import os
    import signal
    
    def emergency_exit():
        time.sleep(600)  # 10 minutes
        print("EMERGENCY EXIT: Application running too long, forcing exit...")
        os.kill(os.getpid(), signal.SIGKILL)
    
    emergency_thread = threading.Thread(target=emergency_exit, daemon=True)
    emergency_thread.start()

def main():
    """Main entry point for the MDX Generator application."""
    # Check for safe mode flag
    safe_mode = "--safe-mode" in sys.argv
    
    # Set up logging
    logger = setup_logger()
    logger.info(f"Starting MDX Generator Tool{' (SAFE MODE)' if safe_mode else ''}")
    
    # Use standard tkinter without trying tkinterdnd2 first
    import tkinter as tk
    root = tk.Tk()
    
    try:
        # If in safe mode, create a more reliable UI
        if safe_mode:
            logger.info("Running in safe mode with limited functionality")
            root.title("MDX Generator Tool (Safe Mode)")
            
            # Simple frame with a message
            frame = tk.Frame(root, padx=20, pady=20)
            frame.pack(fill=tk.BOTH, expand=True)
            
            tk.Label(frame, text="MDX Generator Tool", font=("Arial", 16, "bold")).pack(pady=10)
            tk.Label(frame, text="Running in Safe Mode with limited functionality").pack()
            tk.Label(frame, text="This mode is for troubleshooting app crashes").pack()
            
            # Directory selection
            tk.Label(frame, text="\nSelect a directory to process:", anchor="w").pack(fill="x", pady=(20, 5))
            dir_frame = tk.Frame(frame)
            dir_frame.pack(fill="x")
            
            dir_var = tk.StringVar()
            dir_entry = tk.Entry(dir_frame, textvariable=dir_var)
            dir_entry.pack(side="left", fill="x", expand=True)
            
            # Add a "Load Last Directory" button
            last_dir = get_last_directory()
            
            def load_last_directory():
                last_dir = get_last_directory()
                if last_dir:
                    dir_var.set(last_dir)
                    log_message(f"Loaded last directory: {last_dir}")
                else:
                    log_message("No previous directory found")
            
            def browse():
                from tkinter import filedialog
                directory = filedialog.askdirectory()
                if directory:
                    dir_var.set(directory)
                    update_last_directory(directory)
            
            button_frame = tk.Frame(dir_frame)
            button_frame.pack(side="left")
            
            tk.Button(button_frame, text="Browse", command=browse).pack(side="left", padx=5)
            
            # Only show the "Last Dir" button if a last directory exists
            if last_dir:
                tk.Button(button_frame, text="Last Dir", command=load_last_directory).pack(side="left")
            
            # Function selection
            tk.Label(frame, text="\nSelect function to execute:", anchor="w").pack(fill="x", pady=(20, 5))
            
            function_var = tk.StringVar()
            functions = ["00_normalize_filenames", "01_fix_mdx_frontmatter", "02_generate_index"]
            
            for func in functions:
                tk.Radiobutton(frame, text=func, variable=function_var, value=func).pack(anchor="w")
            
            # Log frame
            log_frame = tk.LabelFrame(frame, text="Log")
            log_frame.pack(fill="both", expand=True, pady=10)
            
            log_text = tk.Text(log_frame, height=10, width=60)
            log_text.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Function to log messages to the text widget
            def log_message(msg):
                log_text.config(state="normal")
                log_text.insert("end", f"{msg}\n")
                log_text.see("end")
                log_text.config(state="disabled")
            
            # Run button function
            def run_function():
                selected_func = function_var.get()
                directory = dir_var.get()
                
                if not selected_func:
                    log_message("Error: No function selected")
                    return
                
                if not directory or not os.path.isdir(directory):
                    log_message("Error: Invalid directory")
                    return
                
                # Save the directory as the last used directory
                update_last_directory(directory)
                
                log_message(f"Running {selected_func} on {directory}...")
                
                try:
                    # Import the module directly
                    # Import the file directly instead of through __init__.py
                    module_name = f"src.core.{selected_func}"
                    # As a fallback, try importing without the module prefix
                    if selected_func.startswith('0'):
                        try_module = selected_func
                    __import__(module_name)
                    module = sys.modules[module_name]
                    
                    # Find the main function - try multiple possible entry point names
                    main_func = getattr(module, 'main', None) or getattr(module, 'process_directory', None) or getattr(module, 'generate_meta_json', None) or getattr(module, 'generate_index_from_meta', None) or getattr(module, 'generate_nav_links', None)
                    
                    if main_func:
                        # Run the function and capture the result
                        result = main_func(directory)
                        log_message(f"Function completed with result: {result}")
                    else:
                        log_message(f"Error: No main function found in {selected_func}")
                except Exception as e:
                    log_message(f"Error: {str(e)}")
                    logger.error(f"Error running {selected_func}: {str(e)}", exc_info=True)
            
            # Run button
            tk.Button(frame, text="Run Function", command=run_function).pack(pady=10)
            
            # For logging to the text widget
            def log_to_gui(message, level):
                log_message(f"[{level}] {message}")
            
            set_gui_log_callback(log_to_gui)
            
            # If last directory exists, set it in the entry
            if last_dir:
                dir_var.set(last_dir)
                log_message(f"Loaded last directory: {last_dir}")
        else:
            # Import MainWindow after root is created
            from gui.main_window import MainWindow
            
            # Create and start the GUI application
            root.title("MDX Generator Tool")
            app = MainWindow(root)
            
            # Connect the logger to the GUI
            def log_to_gui(message, level):
                if hasattr(app, 'log_viewer'):
                    app.log_viewer.append_log(message, level)
            
            set_gui_log_callback(log_to_gui)
        
        root.mainloop()
    except Exception as e:
        # Import here to avoid circular imports
        from tkinter import messagebox
        messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
        logger.error(f"Application error: {str(e)}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    setup_emergency_exit()
    sys.exit(main())