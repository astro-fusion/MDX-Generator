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

def process_directory(directory, progress_callback=None, status_callback=None, stop_event=None, dry_run=False):
    """
    Process files in a directory and normalize their filenames.
    
    Args:
        directory (str): Path to the directory
        progress_callback (callable, optional): Function to report progress (0-100)
        status_callback (callable, optional): Function to report status messages
        stop_event (threading.Event, optional): Event to signal stopping
        dry_run (bool, optional): If True, only scan and report without renaming
        
    Returns:
        tuple: (success, stats) where success is a boolean and stats is a dict with file counts
    """
    try:
        stats = {
            "total_files": 0,
            "to_rename": 0,
            "skipped": 0,
            "renamed": 0,
            "errors": 0,
            "already_normalized": 0
        }
        
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
            return False, stats
            
        # Initial progress update
        if status_callback:
            status_callback("Scanning for files...")
            
        # Get list of all files (with periodic status updates)
        all_files = []
        last_update = time.time()
        
        for root, _, files in os.walk(directory):
            # Check for stop flag periodically
            if stop_event and stop_event.is_set():
                logger.info("File scan stopped by user")
                return False, stats
                
            # Periodic status updates during scanning
            current_time = time.time()
            if current_time - last_update > 0.5:  # Update every 0.5 seconds
                if status_callback:
                    status_callback(f"Scanning files... Found {stats['total_files']} so far")
                if progress_callback:
                    progress_callback(2)  # Keep showing some progress during scan
                last_update = current_time
                
            for file in files:
                # Skip hidden files and system files
                if file.startswith('.') or file.startswith('_'):
                    continue
                    
                # Add file to processing list
                all_files.append(os.path.join(root, file))
                stats['total_files'] += 1
                
        # No files to process
        if not all_files:
            msg = "No files found to normalize"
            logger.warning(msg)
            if status_callback:
                status_callback(msg)
            if progress_callback:
                progress_callback(100)  # Complete the progress
            return True, stats
            
        # First pass: analyze which files need renaming (without actual renaming)
        files_to_rename = []
        
        for filepath in all_files:
            # Extract directory and filename
            dirpath, filename = os.path.split(filepath)
            
            # Normalize filename
            normalized = normalize_filename(filename)
            
            # Skip if filename is already normalized
            if normalized == filename:
                stats['already_normalized'] += 1
                continue
                
            # Create new path
            new_filepath = os.path.join(dirpath, normalized)
            
            # Skip if target file already exists
            if os.path.exists(new_filepath):
                logger.warning(f"Cannot rename {os.path.relpath(filepath, directory)} to {normalized} - file already exists")
                stats['skipped'] += 1
                continue
                
            # Add to rename list
            files_to_rename.append((filepath, new_filepath))
            stats['to_rename'] += 1
        
        # Report stats
        if status_callback:
            stats_msg = (f"Found {stats['total_files']} files: "
                      f"{stats['to_rename']} need renaming, "
                      f"{stats['already_normalized']} already normalized, "
                      f"{stats['skipped']} will be skipped")
            status_callback(stats_msg)
        
        # Exit if dry run or no files to rename
        if dry_run or stats['to_rename'] == 0:
            if progress_callback:
                progress_callback(100)
            return True, stats
            
        # Process in smaller batches for better UI responsiveness
        batch_size = 20
        batches = [files_to_rename[i:i + batch_size] for i in range(0, len(files_to_rename), batch_size)]
        
        for batch_index, batch in enumerate(batches):
            # Check if stop requested
            if stop_event and stop_event.is_set():
                logger.info("File normalization stopped by user")
                if status_callback:
                    status_callback(f"Stopped. Renamed {stats['renamed']}/{stats['to_rename']} files.")
                return False, stats
                
            # Process batch
            for filepath, new_filepath in batch:
                # Get relative path for logging
                rel_path = os.path.relpath(filepath, directory)
                new_name = os.path.basename(new_filepath)
                
                try:
                    # Rename the file
                    os.rename(filepath, new_filepath)
                    logger.info(f"Renamed {rel_path} to {new_name}")
                    stats['renamed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error normalizing {rel_path}: {str(e)}")
                    stats['errors'] += 1
            
            # Update progress after each batch
            if progress_callback:
                # Calculate progress: 5-95% range
                progress = int(5 + (90 * (batch_index + 1) / len(batches)))
                progress_callback(progress)
                
            # Update status message periodically
            if status_callback and (batch_index % 5 == 0 or batch_index == len(batches) - 1):
                status_callback(f"Renamed {stats['renamed']}/{stats['to_rename']} files. Errors: {stats['errors']}")
                
            # Brief pause between batches to allow UI to update
            time.sleep(0.01)
        
        # Final progress update
        if progress_callback:
            progress_callback(100)
            
        # Report completion
        if status_callback:
            status_callback(f"Completed. Renamed {stats['renamed']}/{stats['to_rename']} files. Errors: {stats['errors']}")
            
        return True, stats
        
    except Exception as e:
        logger.error(f"Error in normalize_filenames: {str(e)}", exc_info=True)
        if status_callback:
            status_callback(f"Error: {str(e)}")
        if progress_callback:
            progress_callback(100)  # Ensure progress bar completes
        return False, stats

# For backwards compatibility and CLI usage
main = process_directory

# Command-line execution
if __name__ == "__main__":
    import sys
    import argparse
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Normalize filenames in a directory by removing special characters and spaces"
    )
    parser.add_argument(
        "directory", 
        nargs="?", 
        default=".",
        help="Directory to scan (defaults to current directory)"
    )
    parser.add_argument(
        "--dry-run", "-d", 
        action="store_true",
        help="Only scan and report files that would be renamed without actually renaming them"
    )
    parser.add_argument(
        "--yes", "-y", 
        action="store_true",
        help="Skip confirmation and proceed with renaming"
    )
    
    args = parser.parse_args()
    
    # Status callback function for CLI
    def cli_status_callback(message):
        print(message)
    
    # Run scan to get statistics
    print(f"Scanning directory: {os.path.abspath(args.directory)}")
    success, stats = process_directory(
        args.directory, 
        status_callback=cli_status_callback,
        dry_run=True
    )
    
    if not success:
        sys.exit(1)
    
    # If it's just a dry run, we're done
    if args.dry_run:
        print("\nDry run completed. No files were renamed.")
        sys.exit(0)
    
    # If files need to be renamed, get confirmation unless --yes flag is set
    if stats['to_rename'] > 0 and not args.yes:
        confirm = input(f"\nReady to rename {stats['to_rename']} files. Proceed? [y/N]: ")
        if confirm.lower() not in ('y', 'yes'):
            print("Operation cancelled.")
            sys.exit(0)
    
    # Proceed with actual renaming
    if stats['to_rename'] > 0:
        print(f"\nProceeding to rename {stats['to_rename']} files...")
        success, final_stats = process_directory(
            args.directory, 
            status_callback=cli_status_callback,
            dry_run=False
        )
        
        if success:
            print(f"\nSummary:")
            print(f"- Total files scanned: {final_stats['total_files']}")
            print(f"- Files renamed: {final_stats['renamed']}")
            print(f"- Files skipped: {final_stats['skipped']}")
            print(f"- Errors: {final_stats['errors']}")
    else:
        print("No files need renaming.")
