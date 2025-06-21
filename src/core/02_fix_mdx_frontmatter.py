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
    python 02_fix_mdx_frontmatter.py [root_directory_to_scan] [options]

Examples:
    # Scan current directory
    python 02_fix_mdx_frontmatter.py

    # Scan specific directory
    python 02_fix_mdx_frontmatter.py ./content

    # Dry run to just see what would change
    python 02_fix_mdx_frontmatter.py ./content --dry-run

    # Skip confirmation prompt
    python 02_fix_mdx_frontmatter.py ./content --yes

**IMPORTANT: Always back up your files before running this script,
as it modifies files in place.**
"""

import os
import re
import yaml
from pathlib import Path
import argparse
import sys

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

def process_mdx_file(file_path: Path, dry_run=False):
    """
    Processes a single MD or MDX file to fix its YAML frontmatter if needed.
    
    Args:
        file_path (Path): Path to the MD/MDX file
        dry_run (bool): If True, only analyze without making changes
        
    Returns:
        tuple: (was_modified, needs_fix, has_error) - Boolean flags indicating file status
    """
    try:
        original_content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"⛔ Error reading {file_path}: {e}")
        return False, False, True

    fm_block_match = FRONTMATTER_BLOCK_PATTERN.match(original_content)
    if not fm_block_match:
        # No frontmatter block found
        return False, False, False

    original_frontmatter_block = fm_block_match.group(1)
    
    fm_content_match = FRONTMATTER_CONTENT_PATTERN.match(original_frontmatter_block)
    if not fm_content_match:
        # This should not happen if fm_block_match succeeded, but as a safeguard:
        print(f"⚠️ Could not extract frontmatter content from block in {file_path}")
        return False, False, True
        
    raw_frontmatter_content = fm_content_match.group(1)

    try:
        yaml.safe_load(raw_frontmatter_content)
        return False, False, False  # Already valid, no changes needed
    except yaml.YAMLError as e:
        error_str = str(e)
        # Check for the specific error related to unescaped quotes
        is_target_error = (
            "expected <block end>" in error_str and
            "found '<scalar>'" in error_str and
            "while parsing a block mapping" in error_str
        )

        if is_target_error:
            if not dry_run:
                print(f"⚠️ Potential quote issue found in {file_path}. Attempting fix...")
            
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
                    
                    # If in dry run mode, just report that this file would be fixed
                    if dry_run:
                        return False, True, False
                    
                    # Reconstruct the full frontmatter block with corrected content
                    new_frontmatter_block = f"---\n{fixed_fm_content_string}\n---"
                    
                    # Replace old frontmatter block with new one in the original content
                    # Ensure we replace only the first occurrence (the frontmatter block at the start)
                    new_file_content = original_content.replace(original_frontmatter_block, new_frontmatter_block + "\n", 1)
                    
                    file_path.write_text(new_file_content, encoding='utf-8')
                    print(f"🛠️ Successfully fixed and saved frontmatter for {file_path}")
                    return True, False, False
                except yaml.YAMLError as e_after_fix:
                    if not dry_run:
                        print(f"⛔ Error parsing frontmatter in {file_path} even after attempting fix: {e_after_fix}")
                        print(f"   Original raw frontmatter content:\n{raw_frontmatter_content}")
                        print(f"   Attempted fixed frontmatter content:\n{fixed_fm_content_string}")
                    return False, False, True
            else:
                return False, False, False
        else:
            # Different YAML error encountered, not the target we fix
            return False, False, True

def scan_directory(root_path: Path, dry_run=False):
    """
    Scans a directory recursively for MD/MDX files and analyzes/fixes frontmatter issues.
    
    Args:
        root_path (Path): Directory to scan
        dry_run (bool): If True, only analyze without making changes
        
    Returns:
        dict: Statistics about the scan results
    """
    stats = {
        "total_files_found": 0,
        "files_with_no_frontmatter": 0,
        "files_with_valid_frontmatter": 0,
        "files_needing_fix": 0,
        "files_with_other_errors": 0,
        "files_successfully_fixed": 0
    }
    
    files_to_scan = []
    for pattern in ['*.mdx', '*.md']:
        files_to_scan.extend(root_path.rglob(pattern))
    
    # Remove duplicates and sort for consistent processing order
    unique_files_to_process = sorted(list(set(files_to_scan)))
    
    stats["total_files_found"] = len(unique_files_to_process)

    if not unique_files_to_process:
        print(f"ℹ️ No .md or .mdx files found in {root_path}.")
        return stats

    for target_file in unique_files_to_process:
        was_modified, needs_fix, has_error = process_mdx_file(target_file, dry_run=dry_run)
        
        if was_modified:
            stats["files_successfully_fixed"] += 1
        elif needs_fix:
            stats["files_needing_fix"] += 1
        elif has_error:
            stats["files_with_other_errors"] += 1
        else:
            if FRONTMATTER_BLOCK_PATTERN.match(target_file.read_text(encoding='utf-8')):
                stats["files_with_valid_frontmatter"] += 1
            else:
                stats["files_with_no_frontmatter"] += 1
                
    return stats

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
    parser.add_argument(
        "--dry-run", "-d", 
        action="store_true",
        help="Only scan and report files that would be fixed without actually modifying them"
    )
    parser.add_argument(
        "--yes", "-y", 
        action="store_true",
        help="Skip confirmation and proceed with fixing files"
    )
    args = parser.parse_args()

    root_path = Path(args.root_dir).resolve() # Resolve to get absolute path
    if not root_path.is_dir():
        print(f"⛔ Error: '{root_path}' is not a valid directory.")
        return

    print(f"🔍 Scanning directory: {root_path}")
    print("---")
    
    # Initial dry run to gather statistics
    stats = scan_directory(root_path, dry_run=True)
    
    # Display scan statistics
    print(f"\n--- Scan Results ---")
    print(f"Total .md and .mdx files found: {stats['total_files_found']}")
    print(f"Files with no frontmatter: {stats['files_with_no_frontmatter']}")
    print(f"Files with valid frontmatter: {stats['files_with_valid_frontmatter']}")
    print(f"Files needing fixes: {stats['files_needing_fix']}")
    print(f"Files with other YAML errors: {stats['files_with_other_errors']}")
    
    # If it's just a dry run, we're done
    if args.dry_run:
        print("\n🔍 Dry run completed. No files were modified.")
        sys.exit(0)
    
    # If files need fixes, get confirmation unless --yes flag is set
    if stats['files_needing_fix'] > 0:
        if not args.yes:
            confirm = input(f"\n🔧 Ready to fix {stats['files_needing_fix']} files. Proceed? [y/N]: ")
            if confirm.lower() not in ('y', 'yes'):
                print("❌ Operation cancelled.")
                sys.exit(0)
        
        # Proceed with actual fixing
        print(f"\n🚀 Proceeding to fix {stats['files_needing_fix']} files...")
        fix_stats = scan_directory(root_path, dry_run=False)
        
        # Display final statistics
        print(f"\n--- Final Results ---")
        print(f"Files successfully fixed: {fix_stats['files_successfully_fixed']}")
        print(f"Files that couldn't be fixed: {stats['files_needing_fix'] - fix_stats['files_successfully_fixed']}")
    else:
        print("\n✅ No files need fixing!")

if __name__ == "__main__":
    main()