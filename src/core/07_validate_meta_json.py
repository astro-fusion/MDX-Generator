#!/usr/bin/env python3
"""
Validates the structure defined in _meta.json against the actual filesystem.

Purpose:
This script reads a _meta.json file and checks if all file paths referenced within
actually exist on the disk. It helps ensure that the metadata accurately reflects
the available content files.

Usage:
    python 07_validate_meta_json.py [meta_json_file] [options]

Examples:
    # Validate _meta.json in the current directory
    python 07_validate_meta_json.py 

    # Validate a specific meta.json file
    python 07_validate_meta_json.py ./content/_meta.json

    # Specify a base directory different from the meta.json location
    python 07_validate_meta_json.py --base-dir ./content

    # Specify a custom top-level category name (default is 'Documentation')
    python 07_validate_meta_json.py --top-key "My Documentation"

Structure:
The script validates that all referenced paths in a _meta.json exist:

Example _meta.json structure expected:
{
  "Documentation": [
    {
      "title": "Category 1",
      "children": [
        { "title": "Subcategory 1.1", "path": "01_Rasi/010101_Aries.md" },
        { "title": "Subcategory 1.2", "path": "01_Rasi/010102_Taurus.md" }
      ]
    },
    { "title": "Category 2", "path": "02_Houses/020101_First_House.md" }
    // ... more categories or direct file entries
  ]
}
"""
import json
import os
import sys
import argparse
from pathlib import Path


def load_meta(meta_path):
    """
    Load and parse the _meta.json file.
    
    Args:
        meta_path (Path): Path to the meta.json file
        
    Returns:
        dict: The parsed JSON data or None if an error occurs
    """
    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⛔ Error: Meta file not found at {meta_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"⛔ Error decoding JSON from {meta_path}: {str(e)}")
        return None
    except Exception as e:
        print(f"⛔ An unexpected error occurred loading {meta_path}: {str(e)}")
        return None


def validate_structure(entry, base_dir, stats):
    """
    Recursively validate an entry from the meta structure.
    Checks if file paths exist for file entries.
    
    Args:
        entry (dict): The entry to validate
        base_dir (Path): The base directory to resolve paths against
        stats (dict): Dictionary to track validation statistics
        
    Returns:
        list: List of error messages found during validation
    """
    errors = []
    
    # If the entry has children, assume it's a folder/category and recurse
    if "children" in entry and isinstance(entry["children"], list):
        stats["folders_checked"] += 1
        
        for child in entry["children"]:
            # Ensure child is a dictionary before recursing
            if isinstance(child, dict):
                child_errors = validate_structure(child, base_dir, stats)
                errors.extend(child_errors)
            else:
                error_msg = f"Invalid child format in '{entry.get('title', 'unknown category')}': Expected dict, got {type(child)}"
                errors.append(error_msg)
                stats["format_errors"] += 1
                
    # If it doesn't have children, assume it's a file entry
    elif "path" in entry:
        stats["files_checked"] += 1
        # Construct the full path relative to the base directory
        full_path = base_dir / entry["path"]
        
        # Check if the file exists
        if not full_path.is_file():
            error_msg = f"Missing file: {entry['path']} (referenced in entry titled: '{entry.get('title', 'unknown')}')"
            errors.append(error_msg)
            stats["missing_files"] += 1
        else:
            stats["valid_files"] += 1
    
    # Handle entries that are neither folders nor valid file entries
    else:
        # This case might indicate a malformed entry in the meta.json
        error_msg = f"Invalid entry format: Missing 'children' or 'path' key in entry titled: '{entry.get('title', 'unknown')}'"
        errors.append(error_msg)
        stats["format_errors"] += 1
    
    return errors


def validate_meta_json(meta_file, base_dir=None, top_key="Documentation"):
    """
    Validate the structure defined in a meta.json file.
    
    Args:
        meta_file (str): Path to the meta.json file
        base_dir (str, optional): Base directory to resolve paths against. If None, uses meta_file's directory.
        top_key (str, optional): The top-level key to look for in the meta.json file.
        
    Returns:
        tuple: (success, stats, errors) - Boolean success flag, statistics dict, and list of errors
    """
    # Convert paths to Path objects
    meta_path = Path(meta_file).resolve()
    
    # If base_dir is not specified, use the directory containing the meta_file
    if base_dir is None:
        base_dir = meta_path.parent
    else:
        base_dir = Path(base_dir).resolve()
    
    # Initialize statistics
    stats = {
        "files_checked": 0,
        "folders_checked": 0,
        "valid_files": 0,
        "missing_files": 0,
        "format_errors": 0
    }
    
    print(f"🔍 Validating structure defined in {meta_path}")
    print(f"   Base directory: {base_dir}")
    
    # Load the metadata from the JSON file
    meta_data = load_meta(meta_path)
    if not meta_data:
        return False, stats, [f"Failed to load meta file from {meta_path}"]
    
    # Check if the main top-level key exists and is a list
    if top_key not in meta_data or not isinstance(meta_data[top_key], list):
        error_msg = f"Meta file must contain a top-level key '{top_key}' with a list value."
        return False, stats, [error_msg]
    
    # Start the validation process for each top-level category/entry
    print(f"   Checking {len(meta_data[top_key])} top-level entries under '{top_key}'...")
    errors = []
    
    for category in meta_data[top_key]:
        if isinstance(category, dict):
            category_errors = validate_structure(category, base_dir, stats)
            errors.extend(category_errors)
        else:
            error_msg = f"Invalid top-level entry format in '{top_key}': Expected dict, got {type(category)}"
            errors.append(error_msg)
            stats["format_errors"] += 1
    
    return len(errors) == 0, stats, errors


def print_summary(success, stats, errors):
    """
    Print a summary of the validation process.
    
    Args:
        success (bool): Whether validation was successful
        stats (dict): Statistics from the validation process
        errors (list): List of validation errors
    """
    print("\n--- Validation Summary ---")
    print(f"Files checked: {stats['files_checked']}")
    print(f"Folders/categories checked: {stats['folders_checked']}")
    print(f"Valid files found: {stats['valid_files']}")
    print(f"Missing files: {stats['missing_files']}")
    print(f"Format errors: {stats['format_errors']}")
    print("--------------------------")
    
    if not success:
        print("\n❌ Validation errors found:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        print(f"\nFound {len(errors)} error(s) in the structure.")
    else:
        print("\n✅ All referenced files exist and structure is valid!")


def find_all_meta_files(root_dir):
    """Recursively find all _meta.json files under root_dir."""
    meta_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname == "_meta.json":
                meta_files.append(os.path.join(dirpath, fname))
    return meta_files


def main():
    parser = argparse.ArgumentParser(
        description="Validate all _meta.json files in a directory tree against the filesystem.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'meta_file_or_dir',
        nargs='?',
        default="_meta.json",
        help="Path to a _meta.json file or a directory to scan recursively (default: ./_meta.json)"
    )
    parser.add_argument(
        "--base-dir", "-b",
        help="Base directory to resolve file paths against (default: directory containing each meta_file)"
    )
    parser.add_argument(
        "--top-key", "-t",
        default="Documentation",
        help="Top-level key in the meta.json file (default: 'Documentation')"
    )
    args = parser.parse_args()

    meta_path = Path(args.meta_file_or_dir).resolve()

    # If a directory, scan for all _meta.json files
    if meta_path.is_dir():
        meta_files = find_all_meta_files(meta_path)
        if not meta_files:
            print(f"⚠️ No _meta.json files found in {meta_path}")
            sys.exit(1)
        overall_success = True
        for meta_file in meta_files:
            print(f"\n{'='*60}\nValidating: {meta_file}")
            # Use the parent folder as base_dir unless overridden
            base_dir = args.base_dir if args.base_dir else str(Path(meta_file).parent)
            success, stats, errors = validate_meta_json(meta_file, base_dir, args.top_key)
            print_summary(success, stats, errors)
            if not success:
                overall_success = False
        sys.exit(0 if overall_success else 1)
    else:
        # Single file mode (original behavior)
        success, stats, errors = validate_meta_json(meta_path, args.base_dir, args.top_key)
        print_summary(success, stats, errors)
        sys.exit(0 if success else 1)
