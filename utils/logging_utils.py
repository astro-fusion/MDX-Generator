"""
Logging utilities for the MDX Generator tool.

This module provides logging configuration and helper functions.
"""

import logging
import os
import sys
from datetime import datetime

# Define log directory relative to the project root
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

# Create log directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Store reference to the GUI log function
gui_log_callback = None

class GuiLogHandler(logging.Handler):
    """Custom logging handler that redirects logs to the GUI."""
    
    def emit(self, record):
        """Send log record to GUI."""
        if gui_log_callback:
            # Format the record and call the GUI callback
            log_message = self.format(record)
            # Strip any ANSI color codes for GUI display
            import re
            log_message = re.sub(r'\033\[[0-9;]+m', '', log_message)
            gui_log_callback(log_message, record.levelname)

def setup_logger():
    """Setup and return the root logger."""
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"mdx_generator_{timestamp}.log")
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # File handler for detailed logs
    file_handler = logging.FileHandler(log_file)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console handler for basic info
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name):
    """Get a logger for a specific module."""
    logger = logging.getLogger(name)
    
    # Return the existing logger if already configured
    if logger.handlers:
        return logger
    
    # Set default level
    logger.setLevel(logging.INFO)
    
    return logger

def set_gui_log_callback(callback):
    """
    Set a callback function to receive logs in the GUI.
    
    Args:
        callback: Function that accepts (message, level)
    """
    global gui_log_callback
    gui_log_callback = callback
    
    # Add GUI handler to root logger
    root_logger = logging.getLogger()
    handler = GuiLogHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    root_logger.addHandler(handler)