#!/usr/bin/env python3
"""
Generates _meta.json files recursively within a specified directory structure.

This script walks through a directory tree, identifies subdirectories containing
.md or .mdx files, and creates a _meta.json file in each of those subdirectories.
The _meta.json file contains a list of the markdown/mdx files, ordered numerically
based on a prefix in their filename (e.g., '01_introduction.md'), and includes
a cleaned-up title derived from the filename.

Usage:
    python 04_generate_all_meta_json.py [root_directory_to_scan] [options]

Examples:
    # Scan current directory
    python 04_generate_all_meta_json.py

    # Scan specific directory
    python 04_generate_all_meta_json.py ./content

    # Dry run to just see what would change
    python 04_generate_all_meta_json.py ./content --dry-run

    # Skip confirmation prompt
    python 04_generate_all_meta_json.py ./content --yes
"""
import os
import json
import re
import argparse
import sys
from pathlib import Path

def generate_meta_json(root_dir, dry_run=False, status_callback=None):
    """
    Scans the directory tree starting from root_dir and generates _meta.json files.

    For each subdirectory containing .md or .mdx files, it creates a _meta.json
    file listing those files, ordered and titled based on filename conventions.

    Args:
        root_dir (str): The path to the root directory to start scanning.
        dry_run (bool): If True, only analyze without making changes
        status_callback (callable, optional): Function to report status messages
        
    Returns:
        dict: Statistics about the processing
    """
    # --- Summary Counters ---
    stats = {
        "dirs_scanned": 0,
        "dirs_with_md_files": 0,
        "md_files_processed": 0,
        "meta_files_to_update": 0,
        "meta_files_created": 0,
        "meta_files_updated": 0,
        "errors": 0
    }
    # --- End Summary Counters ---

    # Ensure the provided root directory exists
    root_path = Path(root_dir).resolve()
    if not root_path.is_dir():
        if status_callback:
            status_callback(f"⛔ Error: Root directory '{root_path}' not found or is not a directory.")
        else:
            print(f"⛔ Error: Root directory '{root_path}' not found or is not a directory.")
        return stats

    if status_callback:
        status_callback(f"🔍 Scanning directory tree starting from: {root_path}")
    else:
        print(f"🔍 Scanning directory tree starting from: {root_path}")

    # Walk through the directory tree starting from root_dir
    for current_dir, dirs, files in os.walk(root_dir):
        stats["dirs_scanned"] += 1
        current_path = Path(current_dir)
        
        # Filter for files ending in .md OR .mdx
        md_files = [f for f in files if f.endswith('.md') or f.endswith('.mdx')]

        # Only proceed if there are markdown/mdx files in the current directory
        if md_files:
            stats["dirs_with_md_files"] += 1
            
            if status_callback:
                status_callback(f"\nProcessing directory: {current_path}")
                status_callback(f"Found {len(md_files)} markdown/mdx files")
            else:
                print(f"\nProcessing directory: {current_path}")
                print(f"Found {len(md_files)} markdown/mdx files")

            # Use the directory name as the section title, replacing underscores with spaces
            section_title = current_path.name.replace('_', ' ').strip()
            # If the current directory is the root, use '.' as the key, otherwise use the cleaned name
            json_key = section_title if current_path != root_path else "."

            items = [] # List to hold file metadata dictionaries

            # Process each markdown/mdx file found
            for md_file in md_files:
                stats["md_files_processed"] += 1 # Increment markdown file counter
                filename = md_file # Store the full filename

                # --- Extract order and title from filename ---
                match = re.match(r'^(\d+)_*(.+)\.(mdx?)$', md_file)
                if match:
                    order = int(match.group(1))
                    raw_title = match.group(2)
                else:
                    # Fallback if filename doesn't match the pattern
                    order = None
                    # Remove .md or .mdx extension for the raw title
                    if md_file.endswith('.mdx'):
                        raw_title = md_file[:-4] # Remove .mdx
                    else:
                        raw_title = md_file[:-3] # Remove .md

                # Clean up the title: replace underscores with spaces
                title = re.sub(r'_', ' ', raw_title).strip()

                # Append the extracted metadata to the items list
                item_data = {
                    "file": filename,
                    "title": title,
                    "order": order
                }
                items.append(item_data)
                
                if not status_callback:
                    print(f"  - Processed '{filename}': title='{title}', order={order}")

            # Sort items based on the extracted 'order' number
            items.sort(key=lambda x: x['order'] if x['order'] is not None else float('inf'))

            # Create the final dictionary structure for _meta.json
            meta = {
                section_title: items
            }

            # --- Check if _meta.json exists and if it's different ---
            meta_file_path = current_path / '_meta.json'
            needs_update = True
            
            if meta_file_path.exists():
                try:
                    with open(meta_file_path, 'r', encoding='utf-8') as f:
                        existing_meta = json.load(f)
                        
                    if existing_meta == meta:
                        needs_update = False
                        if status_callback:
                            status_callback(f"_meta.json already up-to-date in {current_path}")
                        else:
                            print(f"_meta.json already up-to-date in {current_path}")
                except Exception as e:
                    if status_callback:
                        status_callback(f"⚠️ Error reading existing _meta.json: {e}")
                    else:
                        print(f"⚠️ Error reading existing _meta.json: {e}")
            
            if needs_update:
                stats["meta_files_to_update"] += 1
                
                # In dry-run mode, don't write the file
                if dry_run:
                    action = "Would create" if not meta_file_path.exists() else "Would update"
                    if status_callback:
                        status_callback(f"🔍 {action}: {meta_file_path}")
                    else:
                        print(f"🔍 {action}: {meta_file_path}")
                    continue
                
                # --- Write _meta.json file ---
                try:
                    with open(meta_file_path, 'w', encoding='utf-8') as f:
                        json.dump(meta, f, indent=2)
                        
                    if meta_file_path.exists():
                        stats["meta_files_updated"] += 1
                        action = "Updated"
                    else:
                        stats["meta_files_created"] += 1
                        action = "Created"
                        
                    if status_callback:
                        status_callback(f"✅ {action}: {meta_file_path}")
                    else:
                        print(f"✅ {action}: {meta_file_path}")
                        
                except IOError as e:
                    stats["errors"] += 1
                    if status_callback:
                        status_callback(f"⛔ Error writing _meta.json to {meta_file_path}: {e}")
                    else:
                        print(f"⛔ Error writing _meta.json to {meta_file_path}: {e}")
                except Exception as e:
                    stats["errors"] += 1
                    if status_callback:
                        status_callback(f"⛔ An unexpected error occurred while writing _meta.json in {current_path}: {e}")
                    else:
                        print(f"⛔ An unexpected error occurred while writing _meta.json in {current_path}: {e}")

    return stats

def print_summary(stats, dry_run=False):
    """Print a summary of the processing statistics"""
    print("\n--- Processing Summary ---")
    print(f"Directories scanned: {stats['dirs_scanned']}")
    print(f"Directories with markdown files: {stats['dirs_with_md_files']}")
    print(f"Markdown/MDX files processed: {stats['md_files_processed']}")
    
    if dry_run:
        print(f"_meta.json files that would be created/updated: {stats['meta_files_to_update']}")
    else:
        print(f"_meta.json files created: {stats['meta_files_created']}")
        print(f"_meta.json files updated: {stats['meta_files_updated']}")
    
    print(f"Errors encountered: {stats['errors']}")
    print("--------------------------")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Generate _meta.json files for directories containing .md/.mdx files.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "root_dir",
        nargs='?',
        default='.',
        help="The root directory to start scanning (default: current directory)"
    )
    parser.add_argument(
        "--dry-run", "-d", 
        action="store_true",
        help="Only scan and report files that would be updated without actually modifying them"
    )
    parser.add_argument(
        "--yes", "-y", 
        action="store_true",
        help="Skip confirmation and proceed with updating"
    )
    
    args = parser.parse_args()
    
    # First do a dry run to gather statistics
    print(f"Analyzing directory structure in: {os.path.abspath(args.root_dir)}")
    stats = generate_meta_json(args.root_dir, dry_run=True)
    
    # Show the analysis results
    print_summary(stats, dry_run=True)
    
    # If it's just a dry run, we're done
    if args.dry_run:
        print("\n🔍 Dry run completed. No files were modified.")
        sys.exit(0)
    
    # If files need to be updated, get confirmation unless --yes flag is set
    if stats['meta_files_to_update'] > 0:
        if not args.yes:
            confirm = input(f"\n🔧 Ready to update {stats['meta_files_to_update']} _meta.json files. Proceed? [y/N]: ")
            if confirm.lower() not in ('y', 'yes'):
                print("❌ Operation cancelled.")
                sys.exit(0)
        
        # Proceed with actual processing
        print(f"\n🚀 Proceeding to update {stats['meta_files_to_update']} _meta.json files...")
        final_stats = generate_meta_json(args.root_dir, dry_run=False)
        
        # Display final statistics
        print_summary(final_stats)
    else:
        print("\n✅ All _meta.json files are already up-to-date!")

if __name__ == "__main__":
    main()
