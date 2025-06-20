#!/usr/bin/env python3
"""
Astro-Blogs Metadata Generator Utility

This script generates a structured _meta.json file by scanning the directory structure
and extracting frontmatter from markdown files for the Astro-Blogs Vedic Astrology documentation.

Usage:
    python generate_root_meta_json.py [root_directory]

Input:
    - Directory structure containing markdown files with YAML frontmatter
    - Each markdown file should have optional frontmatter with 'title' field
    - Directory names are automatically converted to titles (see format_title())

Output:
    - _meta.json: Contains hierarchical structure of all content
    Format:
    {
        "Vedic Astrology": [
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
    3. Change output file name by editing the script

Example:
    python generate_meta_json.py ./content  # Scan from ./content directory
"""

import os
import json
import re
import yaml
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
            print(f"⛔ Error parsing frontmatter in file '{file_path}': {e}")
            return {'title': 'INVALID FRONTMATTER'}  # Add fallback
    return {}

def process_directory(directory, root_path):
    """Recursively process directories and build meta structure"""
    entries = []

    for item in sorted(os.listdir(directory)):
        item_path = Path(directory) / item
        rel_path = item_path.relative_to(root_path)

        if item.startswith('.'):
            continue

        if item_path.is_dir():
            # Process directory
            dir_entry = {
                "title": format_title(item),
                "folder": str(rel_path),
                "children": process_directory(item_path, root_path)
            }
            entries.append(dir_entry)
        # --- Modified line: Check for .md OR .mdx ---
        elif item.endswith(('.md', '.mdx')):
            # Process markdown file
            try:
                content = item_path.read_text(encoding='utf-8')
            except Exception as e:
                print(f"⛔ Error reading {rel_path}: {e}")
                continue

            # --- Modified call: Pass rel_path to extract_frontmatter ---
            frontmatter = extract_frontmatter(content, file_path=rel_path)
            entries.append({
                "name": item,
                "title": frontmatter.get('title', format_title(item)),
                "path": str(rel_path)
            })

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
    # Assuming the top level key might change, get it dynamically or use the known one
    top_level_key = next(iter(structure)) # Gets the first key, e.g., "Vedic Astrology"
    categories = structure.get(top_level_key, [])
    num_categories = len(categories)

    for category in categories:
        total_dirs += 1 # Count the top-level category directory itself
        f_count, d_count = calculate_stats_recursive(category.get("children", []))
        total_files += f_count
        total_dirs += d_count

    return total_files, total_dirs, num_categories

def generate_meta_json(root_dir='.'):
    """Generate _meta.json file with proper hierarchy and display stats"""
    root_path = Path(root_dir).resolve()
    # Assuming the main key is always "Vedic Astrology" based on current logic
    meta_structure = {"Vedic Astrology": []}

    # Process each main category directory (sorted alphabetically)
    for item in sorted(os.listdir(root_path)):
        item_path = root_path / item
        # Skip hidden files/dirs and non-directories at the root level
        if item.startswith('.') or not item_path.is_dir():
            continue

        category_entry = {
            "title": format_title(item),
            "folder": item, # Keep folder relative to root_dir for structure
            "children": process_directory(item_path, root_path) # Pass root_path for relative paths
        }
        meta_structure["Vedic Astrology"].append(category_entry)

    # Save to file
    output_filename = '_meta.json' # Consistent with existing code logic
    output_filepath = Path(output_filename) # Output in the script's execution directory
    # The 'w' mode here ensures the file is overwritten if it exists
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(meta_structure, f, indent=2, ensure_ascii=False)

    # Calculate and print summary statistics
    total_files, total_dirs, num_categories = calculate_stats(meta_structure)
    total_items = total_files + total_dirs # Total items represented in the JSON

    print(f"\n--- Generation Summary ---")
    print(f"Successfully generated: {output_filepath.resolve()}")
    print(f"Root directory scanned: {root_path}")
    print(f"Total top-level categories found: {num_categories}")
    print(f"Total directories processed (including categories): {total_dirs}")
    print(f"Total markdown files processed: {total_files}")
    print(f"Total entries added to _meta.json: {total_items}")
    print(f"--------------------------")


if __name__ == "__main__":
    # Allow specifying root directory via command line argument
    import argparse
    parser = argparse.ArgumentParser(description="Generate _meta.json for documentation structure.")
    parser.add_argument('root_dir', nargs='?', default='.',
                        help='The root directory to scan (default: current directory)')
    args = parser.parse_args()

    generate_meta_json(args.root_dir)
