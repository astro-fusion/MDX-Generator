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
    Convert a filename to URL-friendly format without changing case.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Normalized filename
    """
    # Remove file extension for processing
    name_parts = os.path.splitext(filename)
    name = name_parts[0]
    extension = name_parts[1] if len(name_parts) > 1 else ""
    
    # Replace spaces with hyphens (preserve case)
    name = name.replace(" ", "-")
    
    # Remove special characters while preserving case
    name = re.sub(r'[^a-zA-Z0-9\-_]', '', name)
    
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
        # Report start
        if status_callback:
            status_callback("Starting file normalization...")
            
        if progress_callback:
            progress_callback(1)  # Show initial progress
            
        # Validate directory
        if not os.path.isdir(directory):
            msg = f"Invalid directory: {directory}"
            logger.error(msg)
            if status_callback:
                status_callback(f"Error: {msg}")
            return False
            
        # Initial progress update
        if status_callback:
            status_callback("Scanning for files...")
            
        # Get list of all files (with periodic status updates)
        all_files = []
        file_count = 0
        last_update = time.time()
        
        for root, _, files in os.walk(directory):
            # Check for stop flag periodically
            if stop_event and stop_event.is_set():
                logger.info("File scan stopped by user")
                return False
                
            # Periodic status updates during scanning
            current_time = time.time()
            if current_time - last_update > 0.5:  # Update every 0.5 seconds
                if status_callback:
                    status_callback(f"Scanning files... Found {file_count} so far")
                if progress_callback:
                    progress_callback(2)  # Keep showing some progress during scan
                last_update = current_time
                
            for file in files:
                # Skip hidden files and system files
                if file.startswith('.') or file.startswith('_'):
                    continue
                    
                # Add file to processing list
                all_files.append(os.path.join(root, file))
                file_count += 1
                
        # No files to process
        if not all_files:
            msg = "No files found to normalize"
            logger.warning(msg)
            if status_callback:
                status_callback(msg)
            if progress_callback:
                progress_callback(100)  # Complete the progress
            return True
            
        # Report initial status
        if status_callback:
            status_callback(f"Processing {len(all_files)} files...")
        if progress_callback:
            progress_callback(5)  # Move to 5% after scan
            
        # Process in smaller batches for better UI responsiveness
        batch_size = 20
        batches = [all_files[i:i + batch_size] for i in range(0, len(all_files), batch_size)]
        
        processed_count = 0
        renamed_count = 0
        error_count = 0
        
        for batch_index, batch in enumerate(batches):
            # Check if stop requested
            if stop_event and stop_event.is_set():
                logger.info("File normalization stopped by user")
                if status_callback:
                    status_callback(f"Stopped. Processed {processed_count} files, renamed {renamed_count}.")
                return False
                
            # Process batch
            for filepath in batch:
                # Get relative path for logging
                rel_path = os.path.relpath(filepath, directory)
                
                try:
                    # Extract directory and filename
                    dirpath, filename = os.path.split(filepath)
                    
                    # Normalize filename
                    normalized = normalize_filename(filename)
                    
                    # Skip if filename is already normalized
                    if normalized == filename:
                        processed_count += 1
                        continue
                        
                    # Create new path
                    new_filepath = os.path.join(dirpath, normalized)
                    
                    # Skip if target file already exists
                    if os.path.exists(new_filepath):
                        logger.warning(f"Cannot rename {rel_path} to {normalized} - file already exists")
                        processed_count += 1
                        continue
                        
                    # Rename the file
                    os.rename(filepath, new_filepath)
                    logger.info(f"Renamed {rel_path} to {normalized}")
                    renamed_count += 1
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error normalizing {rel_path}: {str(e)}")
                    error_count += 1
                    processed_count += 1
                    # Continue with other files
            
            # Update progress after each batch
            if progress_callback:
                # Calculate progress: 5-95% range
                progress = int(5 + (90 * (batch_index + 1) / len(batches)))
                progress_callback(progress)
                
            # Update status message periodically
            if status_callback and (batch_index % 5 == 0 or batch_index == len(batches) - 1):
                status_callback(f"Processed {processed_count}/{len(all_files)} files. Renamed: {renamed_count}")
                
            # Brief pause between batches to allow UI to update
            time.sleep(0.01)
        
        # Final progress update
        if progress_callback:
            progress_callback(100)
            
        # Report completion
        if status_callback:
            status_callback(f"Completed. Processed {len(all_files)} files, renamed {renamed_count}.")
            
        return True
        
    except Exception as e:
        logger.error(f"Error in normalize_filenames: {str(e)}", exc_info=True)
        if status_callback:
            status_callback(f"Error: {str(e)}")
        if progress_callback:
            progress_callback(100)  # Ensure progress bar completes
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