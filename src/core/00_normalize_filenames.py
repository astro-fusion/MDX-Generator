#!/usr/bin/env python3
"""
Normalizes filenames in a directory by removing special characters and spaces.

This module processes files in a directory, converting filenames to a URL-friendly format
by replacing spaces with hyphens, removing special characters, and ensuring consistent
lowercase naming.
"""

import os
import re
import logging
import time
from pathlib import Path

# Get logger for this module
logger = logging.getLogger(__name__)

def normalize_filename(filename):
    """
    Convert a filename to URL-friendly format.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Normalized filename
    """
    # Remove file extension for processing
    name_parts = os.path.splitext(filename)
    name = name_parts[0]
    extension = name_parts[1] if len(name_parts) > 1 else ""
    
    # Convert to lowercase
    name = name.lower()
    
    # Replace spaces with hyphens
    name = name.replace(" ", "-")
    
    # Remove special characters
    name = re.sub(r'[^a-z0-9\-_]', '', name)
    
    # Replace multiple hyphens with single hyphen
    name = re.sub(r'-+', '-', name)
    
    # Remove leading/trailing hyphens
    name = name.strip('-')
    
    # Rebuild filename with extension
    return name + extension

def process_directory(directory, progress_callback=None, status_callback=None, stop_event=None):
    """
    Process files in a directory and normalize their filenames.
    
    Args:
        directory (str): Path to the directory
        progress_callback (callable, optional): Function to report progress (0-100)
        status_callback (callable, optional): Function to report status messages
        stop_event (threading.Event, optional): Event to signal stopping
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Validate directory
        if not os.path.isdir(directory):
            msg = f"Invalid directory: {directory}"
            logger.error(msg)
            if status_callback:
                status_callback(f"Error: {msg}")
            return False
            
        # Get list of all files
        all_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                # Skip hidden files and system files
                if file.startswith('.') or file.startswith('_'):
                    continue
                    
                # Skip non-md/mdx files if you want to focus only on those
                # if not (file.endswith('.md') or file.endswith('.mdx')):
                #     continue
                    
                all_files.append(os.path.join(root, file))
                
        # No files to process
        if not all_files:
            msg = "No files found to normalize"
            logger.warning(msg)
            if status_callback:
                status_callback(msg)
            return True
            
        # Report initial status
        if status_callback:
            status_callback(f"Processing {len(all_files)} files...")
            
        # Process each file
        for i, filepath in enumerate(all_files):
            # Check if stop requested
            if stop_event and stop_event.is_set():
                logger.info("File normalization stopped by user")
                return False
                
            # Get relative path for logging
            rel_path = os.path.relpath(filepath, directory)
            
            try:
                # Extract directory and filename
                dirpath, filename = os.path.split(filepath)
                
                # Normalize filename
                normalized = normalize_filename(filename)
                
                # Skip if filename is already normalized
                if normalized == filename:
                    continue
                    
                # Create new path
                new_filepath = os.path.join(dirpath, normalized)
                
                # Skip if target file already exists
                if os.path.exists(new_filepath):
                    logger.warning(f"Cannot rename {rel_path} to {normalized} - file already exists")
                    continue
                    
                # Rename the file
                os.rename(filepath, new_filepath)
                logger.info(f"Renamed {rel_path} to {normalized}")
                
                # Simulate some work to avoid UI freezing
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error normalizing {rel_path}: {str(e)}")
                # Continue with other files
                
            # Update progress
            if progress_callback:
                progress = int((i + 1) / len(all_files) * 100)
                progress_callback(progress)
        
        # Report completion
        if status_callback:
            status_callback("Completed normalizing filenames")
            
        return True
        
    except Exception as e:
        logger.error(f"Error in normalize_filenames: {str(e)}", exc_info=True)
        if status_callback:
            status_callback(f"Error: {str(e)}")
        return False

# For backwards compatibility and CLI usage
main = process_directory

# Command-line execution
if __name__ == "__main__":
    import sys
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get directory from command line or use current directory
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    process_directory(directory)