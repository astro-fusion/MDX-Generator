#!/usr/bin/env python3
"""
Root Metadata Generator Utility

This script generates a structured _meta.json file by scanning the directory structure
and extracting frontmatter from markdown files for documentation websites.

Usage:
    python 06_generate_root_meta_json.py [root_directory] [options]

Examples:
    # Scan current directory
    python 06_generate_root_meta_json.py

    # Scan specific directory
    python 06_generate_root_meta_json.py ./content

    # Dry run to just see what would change
    python 06_generate_root_meta_json.py ./content --dry-run

    # Skip confirmation prompt
    python 06_generate_root_meta_json.py ./content --yes
    
    # Custom output file
    python 06_generate_root_meta_json.py ./content --output ./custom_meta.json

Input:
    - Directory structure containing markdown files with YAML frontmatter
    - Each markdown file should have optional frontmatter with 'title' field
    - Directory names are automatically converted to titles (see format_title())

Output:
    - _meta.json: Contains hierarchical structure of all content
    Format:
    {
        "Main Category": [
            {
                "title": "Category Name",
                "folder": "relative-path",
                "children": [
                    {
                        "title": "Subcategory/Page Name",
                        "path": "relative-path.md",
                        "children": [...]  # Optional nested structure
                    }
                ]
            }
        ]
    }

Functions:
    - generate_meta_json(): Main function that orchestrates the generation process
    - process_directory(): Recursively scans directories and builds the structure
    - extract_frontmatter(): Parses YAML frontmatter from markdown files
    - format_title(): Converts filenames to human-readable titles

Customization:
    1. Add 'title' field in frontmatter to override automatic title generation
    2. Modify format_title() to change how filenames are converted to titles
    3. Change output file name using the --output flag
"""

import os
import json
import re
import yaml
import sys
import argparse
from pathlib import Path

# --- Modified function signature to accept file_path ---
def extract_frontmatter(content, file_path="<unknown file>"):
    """Extract frontmatter from markdown content."""
    frontmatter_match = re.match(r'^---\s*(.*?)\s*---', content, re.DOTALL)
    if frontmatter_match:
        try:
            # Add safe handling for multi-line strings
            return yaml.safe_load(frontmatter_match.group(1).replace('\t', '  '))
        except yaml.YAMLError as e:
            # --- Modified error message to include file_path ---
            print(f"⚠️ Error parsing frontmatter in file '{file_path}': {e}")
            return {'title': 'INVALID FRONTMATTER'}  # Add fallback
    return {}

def process_directory(directory, root_path, stats):
    """Recursively process directories and build meta structure"""
    entries = []

    for item in sorted(os.listdir(directory)):
        item_path = Path(directory) / item
        rel_path = item_path.relative_to(root_path)

        if item.startswith('.'):
            continue

        if item_path.is_dir():
            # Process directory
            stats['dirs_scanned'] += 1
            children = process_directory(item_path, root_path, stats)
            
            # Only include directories that have content
            if children:
                dir_entry = {
                    "title": format_title(item),
                    "folder": str(rel_path),
                    "children": children
                }
                entries.append(dir_entry)
        # --- Modified line: Check for .md OR .mdx ---
        elif item.endswith(('.md', '.mdx')):
            # Process markdown file
            stats['files_found'] += 1
            try:
                content = item_path.read_text(encoding='utf-8')
            except Exception as e:
                print(f"⛔ Error reading {rel_path}: {e}")
                stats['errors'] += 1
                continue

            # --- Modified call: Pass rel_path to extract_frontmatter ---
            frontmatter = extract_frontmatter(content, file_path=rel_path)
            entries.append({
                "name": item,
                "title": frontmatter.get('title', format_title(item)),
                "path": str(rel_path)
            })
            stats['files_processed'] += 1

    return entries

def format_title(filename):
    """Convert filename to human-readable title"""
    # Remove numeric prefixes and extensions (.md or .mdx)
    # --- Modified line: Remove .md OR .mdx extension ---
    name = re.sub(r'^\d+_', '', filename).replace('.mdx', '').replace('.md', '')
    # Convert underscores and hyphens to spaces, then title case
    return ' '.join([word.capitalize() for word in re.split(r'[_-]+', name)])

# Helper function to calculate stats from the generated structure
def calculate_stats_recursive(items):
    """Recursively count files and directories in a list of items."""
    file_count = 0
    dir_count = 0
    for item in items:
        if "path" in item: # It's a file entry
            file_count += 1
        elif "children" in item: # It's a directory entry
            dir_count += 1
            # Recursively count within the subdirectory
            f_count, d_count = calculate_stats_recursive(item["children"])
            file_count += f_count
            dir_count += d_count
    return file_count, dir_count

def calculate_stats(structure):
    """Calculate overall stats from the meta structure."""
    total_files = 0
    total_dirs = 0
    # Assuming the top level key might change, get it dynamically
    top_level_key = next(iter(structure)) # Gets the first key
    categories = structure.get(top_level_key, [])
    num_categories = len(categories)

    for category in categories:
        total_dirs += 1 # Count the top-level category directory itself
        f_count, d_count = calculate_stats_recursive(category.get("children", []))
        total_files += f_count
        total_dirs += d_count

    return total_files, total_dirs, num_categories

def generate_meta_json(root_dir='.', output_file='_meta.json', dry_run=False, top_level_name="Documentation"):
    """Generate _meta.json file with proper hierarchy and display stats"""
    # Initialize statistics
    stats = {
        'dirs_scanned': 0,
        'files_found': 0,
        'files_processed': 0,
        'errors': 0
    }
    
    root_path = Path(root_dir).resolve()
    if not root_path.is_dir():
        print(f"⛔ Error: '{root_path}' is not a valid directory.")
        return None, stats

    # Create a structure with a configurable top level key
    meta_structure = {top_level_name: []}

    # Process each main category directory (sorted alphabetically)
    for item in sorted(os.listdir(root_path)):
        item_path = root_path / item
        # Skip hidden files/dirs and non-directories at the root level
        if item.startswith('.') or not item_path.is_dir():
            continue

        stats['dirs_scanned'] += 1
        children = process_directory(item_path, root_path, stats)
        
        # Only include directories that have content
        if children:
            category_entry = {
                "title": format_title(item),
                "folder": item, # Keep folder relative to root_dir for structure
                "children": children
            }
            meta_structure[top_level_name].append(category_entry)

    # Calculate statistics from the structure
    total_files, total_dirs, num_categories = calculate_stats(meta_structure)

    # If no valid content was found
    if num_categories == 0:
        print(f"⚠️ Warning: No valid content directories found in {root_path}")
    
    # In dry-run mode, don't save the file
    if dry_run:
        output_path = Path(output_file)
        print(f"\n🔍 Would generate: {output_path.resolve()}")
    else:
        # Save to file
        output_path = Path(output_file)
        
        try:
            # The 'w' mode here ensures the file is overwritten if it exists
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(meta_structure, f, indent=2, ensure_ascii=False)
            print(f"\n✅ Successfully generated: {output_path.resolve()}")
        except Exception as e:
            print(f"⛔ Error writing to {output_path}: {e}")
            stats['errors'] += 1
            return None, stats

    return meta_structure, stats

def print_summary(meta_structure, stats, dry_run=False):
    """Print a summary of the generation process"""
    if meta_structure is None:
        print("\n--- Generation Failed ---")
        print(f"Directories scanned: {stats['dirs_scanned']}")
        print(f"Files found: {stats['files_found']}")
        print(f"Files processed: {stats['files_processed']}")
        print(f"Errors encountered: {stats['errors']}")
        return
    
    # Calculate the detailed statistics
    total_files, total_dirs, num_categories = calculate_stats(meta_structure)
    
    print("\n--- Generation Summary ---")
    print(f"Root directory scanned: {stats['dirs_scanned']} directories")
    print(f"Total markdown files found: {stats['files_found']}")
    print(f"Files successfully processed: {stats['files_processed']}")
    print(f"Top-level categories found: {num_categories}")
    
    if dry_run:
        print(f"Files that would be included: {total_files}")
        print(f"Directories that would be included: {total_dirs}")
    else:
        print(f"Files included in metadata: {total_files}")
        print(f"Directories included in metadata: {total_dirs}")
    
    print(f"Errors encountered: {stats['errors']}")
    print("--------------------------")

def main():
    parser = argparse.ArgumentParser(
        description="Generate a root _meta.json file for documentation structure.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'root_dir',
        nargs='?',
        default='.',
        help='The root directory to scan (default: current directory)'
    )
    parser.add_argument(
        "--output", "-o",
        default="_meta.json",
        help="Output file name (default: _meta.json)"
    )
    parser.add_argument(
        "--dry-run", "-d", 
        action="store_true",
        help="Only scan and analyze without creating any files"
    )
    parser.add_argument(
        "--yes", "-y", 
        action="store_true",
        help="Skip confirmation and proceed with generating the file"
    )
    parser.add_argument(
        "--top-level-name", "-t",
        default="Documentation",
        help="Name for the top-level category in the metadata (default: Documentation)"
    )
    
    args = parser.parse_args()

    # First do a dry run to gather statistics
    print(f"Analyzing directory structure in: {os.path.abspath(args.root_dir)}")
    meta_structure, stats = generate_meta_json(
        args.root_dir, 
        args.output, 
        dry_run=True, 
        top_level_name=args.top_level_name
    )
    
    # Show the analysis results
    print_summary(meta_structure, stats, dry_run=True)
    
    # If it's just a dry run, we're done
    if args.dry_run:
        print("\n🔍 Dry run completed. No files were created.")
        sys.exit(0)
    
    # If we have valid content to generate and need confirmation
    if meta_structure and not args.yes:
        confirm = input(f"\n🔧 Ready to create {args.output} with metadata for {stats['files_processed']} files. Proceed? [y/N]: ")
        if confirm.lower() not in ('y', 'yes'):
            print("❌ Operation cancelled.")
            sys.exit(0)
    
    # Proceed with actual generation
    print(f"\n🚀 Generating {args.output}...")
    final_meta_structure, final_stats = generate_meta_json(
        args.root_dir, 
        args.output, 
        dry_run=False, 
        top_level_name=args.top_level_name
    )
    
    # Display final statistics
    print_summary(final_meta_structure, final_stats)

if __name__ == "__main__":
    main()
