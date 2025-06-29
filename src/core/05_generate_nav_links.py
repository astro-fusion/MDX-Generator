#!/usr/bin/env python3
"""
MD/MDX Navigation Links Generator

This script automatically adds Previous/Next article navigation links to MD/MDX files
based on the order specified in a _meta.json file. Links point only to files within
the same folder.

Usage:
    python 05_generate_nav_links.py [folder_path] [options]

Examples:
    # Process folder
    python 05_generate_nav_links.py ./content/planets

    # Dry run to just see what would change
    python 05_generate_nav_links.py ./content/planets --dry-run

    # Skip confirmation prompt
    python 05_generate_nav_links.py ./content/planets --yes

Input Requirements:
    - Target folder containing:
        - MD/MDX files
        - _meta.json file with article ordering
    - _meta.json format:
        {
            "category_name": [
                {
                    "file": "filename.md",
                    "title": "Article Title",
                    "order": 1  // Optional ordering
                }
            ]
        }

Output:
    - Appends navigation links to each MD/MDX file in the format:
        ---
        ## Previous Article
        - [Title](previous-file.md)
        ---
        ## Next Article  
        - [Title](next-file.md)
        ---

Features:
    - Circular navigation (last article links to first and vice versa)
    - Automatic title fallback if not specified
    - Dry run mode to preview changes
    - Confirmation prompt before modifying files
"""

import os
import json
import argparse
import sys
from pathlib import Path

def generate_nav_links_for_folder(folder_path, dry_run=False, stats=None):
    """
    Generates and appends previous/next navigation links to MD/MDX files
    in a folder based on the order specified in a _meta.json file.
    Recursively processes subfolders.
    """
    if stats is None:
        stats = {
            "total_files_found": 0,
            "files_to_update": 0,
            "files_updated": 0,
            "skipped_files": 0,
            "errors": 0
        }

    folder_path = Path(folder_path)
    meta_file_path = folder_path / "_meta.json"
    base_folder_name = folder_path.name

    if not folder_path.is_dir():
        print(f"⛔ Error: Folder not found at '{folder_path}'")
        stats["errors"] += 1
        return stats

    # Recursively process subfolders first
    for child in folder_path.iterdir():
        if child.is_dir():
            generate_nav_links_for_folder(child, dry_run=dry_run, stats=stats)

    if not meta_file_path.is_file():
        # Not an error if subfolder doesn't have _meta.json, just skip
        return stats

    try:
        with open(meta_file_path, 'r', encoding='utf-8') as f:
            meta_data = json.load(f)

        if not meta_data or not isinstance(meta_data, dict):
            print(f"⛔ Error: Invalid format in '{meta_file_path}'. Expected a dictionary.")
            stats["errors"] += 1
            return stats

        file_list_key = next(iter(meta_data))
        files_info = meta_data[file_list_key]

        if not isinstance(files_info, list):
            print(f"⛔ Error: Invalid format in '{meta_file_path}'. Expected a list under the key '{file_list_key}'.")
            stats["errors"] += 1
            return stats

        # Sort files based on the 'order' key
        sorted_files = sorted(files_info, key=lambda x: x.get('order', float('inf')))
        num_files = len(sorted_files)

        stats["total_files_found"] += num_files

        if num_files == 0:
            print(f"ℹ️ No files found in the '_meta.json' list for '{base_folder_name}'.")
            return stats

        print(f"🔍 Found {num_files} files in '{base_folder_name}'...")

        for i, current_item in enumerate(sorted_files):
            current_file_name = current_item.get('file')
            current_file_path = folder_path / current_file_name

            if not current_file_name or not current_file_path.is_file():
                print(f"⚠️ Warning: Skipping invalid or missing file entry: {current_item}")
                stats["skipped_files"] += 1
                continue

            # Determine previous and next items (circular)
            prev_idx = (i - 1 + num_files) % num_files
            next_idx = (i + 1) % num_files

            prev_item = sorted_files[prev_idx]
            next_item = sorted_files[next_idx]

            prev_title = prev_item.get('title', 'Previous')
            prev_file_name = prev_item.get('file')
            next_title = next_item.get('title', 'Next')
            next_file_name = next_item.get('file')

            if not prev_file_name or not next_file_name:
                print(f"⚠️ Warning: Missing file name for prev/next links for '{current_file_name}'. Skipping.")
                stats["skipped_files"] += 1
                continue

            # Construct links - only using file names for same-folder linking
            prev_link = f"{prev_file_name}"
            next_link = f"{next_file_name}"

            # Construct Markdown snippet
            nav_snippet = f"""
---

## Previous Article
- [{prev_title}]({prev_link})

---

## Next Article
- [{next_title}]({next_link})

---
"""
            stats["files_to_update"] += 1

            # In dry run mode, don't modify files
            if dry_run:
                print(f"🔍 Would add navigation links to '{current_file_path}' (Previous: '{prev_file_name}', Next: '{next_file_name}')")
                continue

            # Remove any existing navigation snippet at the end before appending new one
            try:
                with open(current_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Remove previous nav snippet if present (very basic approach)
                content = content.rsplit('\n---\n## Previous Article', 1)[0].rstrip()
                with open(current_file_path, 'w', encoding='utf-8') as f:
                    f.write(content + nav_snippet)
                print(f"✅ Added navigation links to '{current_file_path}'")
                stats["files_updated"] += 1
            except IOError as e:
                print(f"⛔ Error writing to file '{current_file_path}': {e}")
                stats["errors"] += 1

        print(f"✅ Finished processing folder '{base_folder_name}'.")
        return stats

    except json.JSONDecodeError as e:
        print(f"⛔ Error parsing '{meta_file_path}': {e}")
        stats["errors"] += 1
    except KeyError as e:
        print(f"⛔ Error: Missing expected key '{e}' in '_meta.json' entries.")
        stats["errors"] += 1
    except Exception as e:
        print(f"⛔ An unexpected error occurred: {e}")
        stats["errors"] += 1

    return stats

def print_summary(stats, dry_run=False):
    """Print a summary of the processing statistics"""
    print("\n--- Processing Summary ---")
    print(f"Total files found in _meta.json: {stats['total_files_found']}")
    if dry_run:
        print(f"Files that would be updated: {stats['files_to_update']}")
    else:
        print(f"Files successfully updated: {stats['files_updated']}")
    print(f"Files skipped: {stats['skipped_files']}")
    print(f"Errors encountered: {stats['errors']}")
    print("--------------------------")

def main():
    parser = argparse.ArgumentParser(
        description="Append Previous/Next article links to MD/MDX files based on _meta.json (recursively for all subfolders).",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "folder_path",
        help="Path to the folder containing the MD/MDX files and _meta.json."
    )
    parser.add_argument(
        "--dry-run", "-d", 
        action="store_true",
        help="Only scan and report files that would be updated without actually modifying them"
    )
    parser.add_argument(
        "--yes", "-y", 
        action="store_true",
        help="Skip confirmation and proceed with adding navigation links"
    )
    args = parser.parse_args()

    # First do a dry run to gather statistics
    print(f"Analyzing folder: {os.path.abspath(args.folder_path)} (including subfolders)")
    stats = generate_nav_links_for_folder(args.folder_path, dry_run=True)
    
    # Show the analysis results
    print_summary(stats, dry_run=True)
    
    # If it's just a dry run, we're done
    if args.dry_run:
        print("\n🔍 Dry run completed. No files were modified.")
        sys.exit(0)
    
    # If files need to be updated, get confirmation unless --yes flag is set
    if stats['files_to_update'] > 0:
        if not args.yes:
            confirm = input(f"\n🔧 Ready to add navigation links to {stats['files_to_update']} files. Proceed? [y/N]: ")
            if confirm.lower() not in ('y', 'yes'):
                print("❌ Operation cancelled.")
                sys.exit(0)
        
        # Proceed with actual processing
        print(f"\n🚀 Proceeding to update {stats['files_to_update']} files...")
        final_stats = generate_nav_links_for_folder(args.folder_path, dry_run=False)
        
        # Display final statistics
        print_summary(final_stats)
    else:
        print("\n✅ No files to update.")

if __name__ == "__main__":
    main()