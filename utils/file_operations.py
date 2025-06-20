"""
File operations utility module for the MDX Generator.

This module provides functionality to handle files and directories.
"""

import os
import importlib.util
import inspect
import re
from typing import List, Dict, Any, Callable, Optional
import sys
import threading
import queue
import time

from utils.logging_utils import get_logger

# Initialize logger with module name
logger = get_logger(__name__)

def is_valid_directory(directory: str) -> bool:
    """
    Check if the directory exists and contains any MD/MDX files.
    
    Args:
        directory (str): Path to the directory
        
    Returns:
        bool: True if directory is valid, False otherwise
    """
    if not os.path.isdir(directory):
        return False
    
    # Check if there are any .md or .mdx files
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.md') or file.endswith('.mdx'):
                return True
    
    return False

def get_core_modules() -> List[Dict[str, Any]]:
    """
    Get list of available core processing modules.
    
    Returns:
        List[Dict[str, Any]]: List of module information dictionaries
    """
    modules = []
    
    # Define core module directory
    core_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "core")
    # Fallback to direct core directory if src/core doesn't exist
    if not os.path.exists(core_dir):
        core_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core")
    
    # Create core directory if it doesn't exist
    if not os.path.exists(core_dir):
        os.makedirs(core_dir)
        logger.warning(f"Created missing core directory: {core_dir}")
    
    # Look for actual modules in the core directory
    if os.path.isdir(core_dir):
        # Find all Python files in the core directory
        module_files = [f for f in os.listdir(core_dir) if f.endswith('.py')]
        
        # Filter and sort modules by their numeric prefix (e.g., 00_, 01_, etc.)
        for module_file in sorted(module_files):
            # Extract module number and name
            match = re.match(r'^(\d+)_(.+)\.py$', module_file)
            if match:
                order = int(match.group(1))
                name_part = match.group(2)
                
                # Convert snake_case to title case for display (e.g., normalize_filenames -> Normalize Filenames)
                display_name = ' '.join(word.capitalize() for word in name_part.split('_'))
                
                modules.append({
                    'name': name_part,
                    'display_name': display_name,
                    'path': os.path.join(core_dir, module_file),
                    'order': order,
                    'filename': module_file
                })
                logger.info(f"Detected core module: {display_name} (order: {order})")
            
        if not modules:
            logger.warning(f"No core modules found in {core_dir}")
    else:
        logger.error(f"Core directory not found at {core_dir}")
    
    return sorted(modules, key=lambda m: m['order'])

def adapt_core_module_for_gui(module_info: Dict[str, Any]) -> Optional[Callable]:
    """
    Adapt a core module for use in the GUI.
    
    This function dynamically imports the module and wraps its main function
    to provide progress updates to the GUI.
    
    Args:
        module_info (Dict): Information about the module
        
    Returns:
        Optional[Callable]: Wrapped function or None if module not found
    """
    module_path = module_info.get('path')
    if not module_path or not os.path.exists(module_path):
        logger.error(f"Module file not found: {module_path}")
        return None
    
    try:
        # Dynamically import the module
        module_name = os.path.basename(module_path).replace('.py', '')
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            logger.error(f"Failed to load module spec from {module_path}")
            return None
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Look for the main function in the module
        main_func = getattr(module, 'main', None) or getattr(module, 'process_directory', None) or getattr(module, 'generate_meta_json', None)
        if main_func is None:
            # Look for other candidate functions that might be the main entry point
            candidates = [name for name, func in inspect.getmembers(module, inspect.isfunction)
                         if name in ('generate_nav_links', 'validate_structure', 'generate_index_from_meta', 'fix_mdx_file')]
            if candidates:
                main_func = getattr(module, candidates[0])
            else:
                logger.error(f"No main function found in module {module_name}. Available functions: {[name for name, func in inspect.getmembers(module, inspect.isfunction)]}")
                return None
        
        # Create a wrapper function that provides progress updates
        def wrapper(directory, progress_callback=None, status_callback=None, stop_event=None):
            """Wrapper function for core module main function with progress reporting."""
            try:
                logger.info(f"Running module: {module_info['display_name']} on {directory}")
                
                # Update status
                if status_callback:
                    status_callback(f"Starting {module_info['display_name']}...")
                
                # Prepare arguments based on what the function accepts
                sig = inspect.signature(main_func)
                args = {}
                
                # Common argument names
                if 'directory' in sig.parameters:
                    args['directory'] = directory
                elif 'folder_path' in sig.parameters:
                    args['folder_path'] = directory
                elif 'folder_path_str' in sig.parameters:
                    args['folder_path_str'] = directory
                elif 'root_dir' in sig.parameters:
                    args['root_dir'] = directory
                # Add more parameter mappings as needed
                
                # Start the actual processing
                result = main_func(**args)
                
                # Update progress to 100%
                if progress_callback:
                    progress_callback(100)
                
                if status_callback:
                    status_callback("Completed")
                
                logger.info(f"Completed module: {module_info['display_name']}")
                return True
                
            except Exception as e:
                logger.error(f"Error in module {module_info['display_name']}: {str(e)}", exc_info=True)
                if status_callback:
                    status_callback(f"Error: {str(e)}")
                return False
        
        return wrapper
        
    except Exception as e:
        logger.error(f"Error adapting module {module_path}: {str(e)}", exc_info=True)
        return None

# Function to run a module in a separate thread with progress and status updates
def run_module_async(module_info, directory, progress_var=None, status_var=None):
    """
    Run a core module asynchronously with progress and status updates.
    
    Args:
        module_info (Dict): Module information dictionary
        directory (str): Target directory to process
        progress_var: tkinter variable for progress updates
        status_var: tkinter variable for status updates
        
    Returns:
        dict: Contains thread object and message queue for communication
    """
    # Create a stop event for cancellation
    stop_event = threading.Event()
    
    # Create a message queue for thread communication
    message_queue = queue.Queue()
    
    # Create wrapper function for the module
    module_func = adapt_core_module_for_gui(module_info)
    
    if not module_func:
        if status_var:
            status_var.set(f"Error: Module {module_info['display_name']} not found")
        return None
    
    # Create heartbeat mechanism
    last_heartbeat = [time.time()]
    
    # Create progress and status callback functions
    def update_progress(value):
        if progress_var and not stop_event.is_set():
            # Instead of directly updating, put in queue
            message_queue.put(('progress', value))
            # Update heartbeat
            last_heartbeat[0] = time.time()
    
    def update_status(message):
        if status_var and not stop_event.is_set():
            # Instead of directly updating, put in queue
            message_queue.put(('status', message))
            # Update heartbeat
            last_heartbeat[0] = time.time()
    
    # Create the actual thread function with exception handling
    def run_with_timeout():
        try:
            # Set initial status
            update_status("Initializing...")
            update_progress(5)  # Show some initial progress
            
            # Regular heartbeat updates even if module doesn't report progress
            while not stop_event.is_set():
                # Check if execution is still ongoing
                if not thread_active[0]:
                    break
                    
                # Send heartbeat every 1 second
                message_queue.put(('heartbeat', time.time()))
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Heartbeat error: {str(e)}", exc_info=True)
    
    # Create actual worker function
    def worker_function():
        try:
            # Mark thread as active
            thread_active[0] = True
            
            # Start execution
            result = module_func(directory, update_progress, update_status, stop_event)
            
            # Ensure final progress is at 100% if successful
            if result and not stop_event.is_set():
                update_progress(100)
                update_status("Completed")
            elif stop_event.is_set():
                update_status("Stopped by user")
            else:
                update_status("Failed")
                
        except Exception as e:
            logger.error(f"Error in module {module_info['display_name']}: {str(e)}", exc_info=True)
            if not stop_event.is_set():
                update_status(f"Error: {str(e)[:50]}...")
        finally:
            # Mark thread as inactive
            thread_active[0] = False
    
    # Thread active flag (in list to make it mutable from inner functions)
    thread_active = [False]
    
    # Create and start the worker thread
    worker_thread = threading.Thread(
        target=worker_function,
        daemon=True
    )
    
    # Create and start the heartbeat thread
    heartbeat_thread = threading.Thread(
        target=run_with_timeout,
        daemon=True
    )
    
    # Store thread info
    thread_info = {
        'worker_thread': worker_thread,
        'heartbeat_thread': heartbeat_thread,
        'stop_event': stop_event,
        'message_queue': message_queue,
        'last_heartbeat': last_heartbeat,
        'thread_active': thread_active,
        'module_info': module_info
    }
    
    # Start threads
    worker_thread.start()
    heartbeat_thread.start()
    
    return thread_info