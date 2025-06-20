#!/usr/bin/env python3
"""
MDX Generator Tool

A GUI application for processing and fixing MDX files generated from AI outputs.
"""

import os
import sys
from utils.logging_utils import setup_logger, set_gui_log_callback

def main():
    """Main entry point for the MDX Generator application."""
    # Set up logging
    logger = setup_logger()
    logger.info("Starting MDX Generator Tool")
    
    # Use standard tkinter without trying tkinterdnd2 first
    import tkinter as tk
    root = tk.Tk()
    
    try:
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
    sys.exit(main())