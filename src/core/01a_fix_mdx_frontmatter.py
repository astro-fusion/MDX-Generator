#!/usr/bin/env python3
"""
MD/MDX Frontmatter Fixer Script

This script scans for .md and .mdx files in a specified directory (or the
current directory if none is provided) and attempts to fix common YAML
frontmatter parsing errors related to unescaped single quotes in 'title'
and 'description' fields.

Specifically, it targets errors like:
"expected <block end>, but found '<scalar>' ... while parsing a block mapping"
which often occur with entries like:
  title: 'Some Text's with an apostrophe'

The script will attempt to change such lines to the correct YAML syntax:
  title: 'Some Text''s with an apostrophe'

Usage:
    python 01a_fix_mdx_frontmatter.py [root_directory_to_scan]

Example (scan './content' directory):
    python 01a_fix_mdx_frontmatter.py ./content

Example (scan current directory and subdirectories):
    python 01a_fix_mdx_frontmatter.py

**IMPORTANT: Always back up your files before running this script,
as it modifies files in place.**
"""

import os
import re
import yaml
from pathlib import Path
import argparse

# Pattern to extract the whole frontmatter block (---...---)
FRONTMATTER_BLOCK_PATTERN = re.compile(r'^(---[^\S\r\n]*\n.*?\n---[^\S\r\n]*\n)', re.DOTALL | re.MULTILINE)
# Pattern to extract content within frontmatter (excluding ---)
FRONTMATTER_CONTENT_PATTERN = re.compile(r'^---\s*(.*?)\s*---', re.DOTALL)

def fix_yaml_line_for_quotes(line_text):
    """
    Fixes a YAML line for 'title' or 'description' if it uses single quotes
    and contains unescaped single quotes within the value.
    Example: title: 'Vastu's' -> title: 'Vastu''s'
    """
    # Regex to match "key: 'value'" for title or description
    # Group 1: The key part (e.g., "title: ")
    # Group 2: The content within the single quotes
    # Group 3: Optional comment part or trailing whitespace
    match = re.match(r"^(\s*(?:title|description)\s*:\s*)'(.*)'(\s*(?:#.*)?)$", line_text)
    if match:
        prefix = match.group(1)
        value = match.group(2)
        suffix = match.group(3) if match.group(3) else ""

        # If the value contains a single quote, it needs to be escaped to ''
        # This simple replacement handles ' -> ''
        # e.g. "It's" becomes "It''s"
        if "'" in value:
            fixed_value = value.replace("'", "''")
            return f"{prefix}'{fixed_value}'{suffix}"
    return line_text # Return original line if no change needed or not matching pattern

def process_mdx_file(file_path: Path):
    """
    Processes a single MD or MDX file to fix its YAML frontmatter if needed.
    Returns True if the file was modified, False otherwise.
    """
    try:
        original_content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"⛔ Error reading {file_path}: {e}")
        return False

    fm_block_match = FRONTMATTER_BLOCK_PATTERN.match(original_content)
    if not fm_block_match:
        # print(f"ℹ️ No frontmatter block found in {file_path}")
        return False

    original_frontmatter_block = fm_block_match.group(1)
    
    fm_content_match = FRONTMATTER_CONTENT_PATTERN.match(original_frontmatter_block)
    if not fm_content_match:
        # This should not happen if fm_block_match succeeded, but as a safeguard:
        print(f"⚠️ Could not extract frontmatter content from block in {file_path}")
        return False
        
    raw_frontmatter_content = fm_content_match.group(1)

    try:
        yaml.safe_load(raw_frontmatter_content)
        # print(f"✅ Frontmatter in {file_path} is already valid.")
        return False # Already valid
    except yaml.YAMLError as e:
        error_str = str(e)
        # Check for the specific error related to unescaped quotes
        is_target_error = (
            "expected <block end>" in error_str and
            "found '<scalar>'" in error_str and
            "while parsing a block mapping" in error_str
        )

        if is_target_error:
            print(f"⚠️ Potential quote issue found in {file_path}. Attempting fix...")
            # print(f"   Error details: {error_str.splitlines()[0]}") # Print first line of error

            fixed_fm_lines = []
            modified_in_lines = False
            for line in raw_frontmatter_content.splitlines():
                original_line = line
                fixed_line = fix_yaml_line_for_quotes(line)
                if original_line != fixed_line:
                    modified_in_lines = True
                fixed_fm_lines.append(fixed_line)

            if modified_in_lines:
                fixed_fm_content_string = "\n".join(fixed_fm_lines)
                
                # Verify if the fix resolves the YAML parsing
                try:
                    yaml.safe_load(fixed_fm_content_string)
                    
                    # Reconstruct the full frontmatter block with corrected content
                    new_frontmatter_block = f"---\n{fixed_fm_content_string}\n---"
                    
                    # Replace old frontmatter block with new one in the original content
                    # Ensure we replace only the first occurrence (the frontmatter block at the start)
                    new_file_content = original_content.replace(original_frontmatter_block, new_frontmatter_block + "\n", 1)
                    
                    file_path.write_text(new_file_content, encoding='utf-8')
                    print(f"🛠️ Successfully fixed and saved frontmatter for {file_path}")
                    return True
                except yaml.YAMLError as e_after_fix:
                    print(f"⛔ Error parsing frontmatter in {file_path} even after attempting fix: {e_after_fix}")
                    print(f"   Original raw frontmatter content:\n{raw_frontmatter_content}")
                    print(f"   Attempted fixed frontmatter content:\n{fixed_fm_content_string}")
                    return False
            else:
                # print(f"ℹ️ No applicable fix made to {file_path} for the identified error type (lines unchanged).")
                return False
        else:
            # print(f"ℹ️ Skipping {file_path}, different YAML error encountered: {error_str.splitlines()[0]}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description="Fix YAML frontmatter in MD and MDX files for specific single quote issues in 'title' and 'description'.",
        formatter_class=argparse.RawTextHelpFormatter # To preserve help text formatting
    )
    parser.add_argument(
        'root_dir', 
        type=str,
        nargs='?',
        default='.',
        help='The root directory to scan for MD/MDX files (e.g., ./content). Defaults to current directory if not specified.'
    )
    args = parser.parse_args()

    root_path = Path(args.root_dir).resolve() # Resolve to get absolute path
    if not root_path.is_dir():
        print(f"⛔ Error: '{root_path}' is not a valid directory.")
        return

    print(f"🚀 Starting scan in directory: {root_path}")
    print("---")
    
    fixed_files_count = 0
    processed_files_count = 0
    
    files_to_scan = []
    for pattern in ['*.mdx', '*.md']:
        files_to_scan.extend(root_path.rglob(pattern))
    
    # Remove duplicates (e.g. if a file is somehow .md and .mdx, though unlikely)
    # and sort for consistent processing order
    unique_files_to_process = sorted(list(set(files_to_scan)))
    
    total_target_files_found = len(unique_files_to_process)

    if not unique_files_to_process:
        print(f"ℹ️ No .md or .mdx files found in {root_path}.")
        return

    for target_file in unique_files_to_process:
        # print(f"\nProcessing: {target_file}") # Uncomment for verbose per-file processing start
        if process_mdx_file(target_file): # Function name kept for simplicity, handles both
            fixed_files_count += 1
        processed_files_count +=1 
    
    print(f"\n--- Scan Complete ---")
    print(f"Total .md and .mdx files found: {total_target_files_found}")
    print(f"Total files processed for potential fixes: {processed_files_count}")
    print(f"Total files successfully fixed and saved: {fixed_files_count}")
    print(f"---------------------")

if __name__ == "__main__":
    main()