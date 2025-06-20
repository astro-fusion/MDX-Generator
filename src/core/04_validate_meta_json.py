#!/usr/bin/env python3
"""
Validates the structure defined in _meta.json against the actual filesystem.

Purpose:
This script reads the _meta.json file located in the same directory
and checks if all file paths referenced within the 'Vedic Astrology'
section actually exist on the disk. It helps ensure that the metadata
accurately reflects the available content files.

Usage:
Navigate to the directory containing this script and _meta.json, then run:
  python3 validate.py

Example _meta.json structure expected:
{
  "Vedic Astrology": [
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
from pathlib import Path
import sys

def load_meta(meta_path):
    """Load and parse the _meta.json file."""
    try:
        with open(meta_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: _meta.json not found at {meta_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {meta_path}: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred loading {meta_path}: {str(e)}")
        sys.exit(1)

def validate_structure(entry, base_dir, errors):
    """
    Recursively validate an entry from the meta structure.
    Checks if file paths exist for file entries.
    """
    # If the entry has children, assume it's a folder/category and recurse
    if "children" in entry and isinstance(entry["children"], list):
        for child in entry["children"]:
            # Ensure child is a dictionary before recursing
            if isinstance(child, dict):
                validate_structure(child, base_dir, errors)
            else:
                errors.append(f"Invalid child format in '{entry.get('title', 'unknown category')}': Expected dict, got {type(child)}")
    # If it doesn't have children, assume it's a file entry
    elif "path" in entry:
        # Construct the full path relative to the script's directory
        full_path = base_dir / entry["path"]
        # Check if the file exists
        if not full_path.is_file(): # Use is_file() for explicit file check
            errors.append(f"Missing file: {entry['path']} (referenced in entry titled: '{entry.get('title', 'unknown')}')")
    # Handle entries that are neither folders nor valid file entries (optional)
    # else:
    #     # This case might indicate a malformed entry in _meta.json
    #     errors.append(f"Invalid entry format: Missing 'children' or 'path' key in entry titled: '{entry.get('title', 'unknown')}'")


def main():
    # Determine the base directory (where the script is located)
    base_dir = Path(__file__).parent
    # Define the path to the _meta.json file
    meta_path = base_dir / "_meta.json"

    print(f"🔍 Validating structure defined in {meta_path}")
    print(f"   Relative to base directory: {base_dir}")

    # Load the metadata from the JSON file
    meta_data = load_meta(meta_path)
    errors = [] # Initialize an empty list to store validation errors

    # Check if the main 'Vedic Astrology' key exists and is a list
    if "Vedic Astrology" not in meta_data or not isinstance(meta_data["Vedic Astrology"], list):
        print(f"\n❌ Validation error:")
        print(f"  \033[91m_meta.json must contain a top-level key 'Vedic Astrology' with a list value.\033[0m")
        sys.exit(1)

    # Start the validation process for each top-level category/entry
    print(f"   Checking {len(meta_data['Vedic Astrology'])} top-level entries under 'Vedic Astrology'...")
    for category in meta_data["Vedic Astrology"]:
         if isinstance(category, dict):
            validate_structure(category, base_dir, errors)
         else:
            errors.append(f"Invalid top-level entry format in 'Vedic Astrology': Expected dict, got {type(category)}")


    # Print the validation results
    if errors:
        print("\n❌ Validation errors found:")
        for error in errors:
            # Print each error message in red
            print(f"  \033[91m- {error}\033[0m")
        print(f"\nFound {len(errors)} error(s) in the structure defined by _meta.json.")
        sys.exit(1) # Exit with a non-zero status code to indicate failure
    else:
        # Print success message in green
        print("\n\033[92m✅ All referenced files exist and structure appears valid!\033[0m")
        # print("Checked all entries in:")
        # print(f" - {len(meta_data.get('Vedic Astrology', []))} main categories/entries")
        sys.exit(0) # Exit with status code 0 to indicate success

if __name__ == "__main__":
    main()
