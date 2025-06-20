"""
Generates _meta.json files recursively within a specified directory structure.

This script walks through a directory tree, identifies subdirectories containing
.md or .mdx files, and creates a _meta.json file in each of those subdirectories.
The _meta.json file contains a list of the markdown/mdx files, ordered numerically
based on a prefix in their filename (e.g., '01_introduction.md'), and includes
a cleaned-up title derived from the filename.

The script can be run from the command line, optionally taking the root directory
to scan as an argument. If no argument is provided, it defaults to the current
directory.
"""
import os
import json
import re
import argparse # Import argparse for command-line arguments

def generate_meta_json(root_dir):
    """
    Scans the directory tree starting from root_dir and generates _meta.json files.

    For each subdirectory containing .md or .mdx files, it creates a _meta.json
    file listing those files, ordered and titled based on filename conventions.

    Args:
        root_dir (str): The path to the root directory to start scanning.
    """
    # --- Summary Counters ---
    dirs_scanned = 0
    meta_files_created = 0
    md_files_processed = 0
    # --- End Summary Counters ---

    # Ensure the provided root directory exists
    if not os.path.isdir(root_dir):
        print(f"Error: Root directory '{root_dir}' not found or is not a directory.")
        return

    abs_root_dir = os.path.abspath(root_dir)
    print(f"Scanning directory tree starting from: {abs_root_dir}")

    # Walk through the directory tree starting from root_dir
    for current_dir, dirs, files in os.walk(root_dir):
        dirs_scanned += 1 # Increment directory counter
        abs_current_dir = os.path.abspath(current_dir)
        # Skip the root directory itself if it's the one passed as argument
        # (usually we want _meta.json in subdirectories, not the root)
        # if abs_current_dir == abs_root_dir:
             # Optional: uncomment the next line if you *never* want _meta.json in the root folder provided
             # continue
             # pass # Allow processing in the root if needed, comment 'continue' above

        # Filter for files ending in .md OR .mdx
        md_files = [f for f in files if f.endswith('.md') or f.endswith('.mdx')]

        # Only proceed if there are markdown/mdx files in the current directory
        if md_files:
            print(f"\nProcessing directory: {abs_current_dir}")
            print(f"Found markdown/mdx files: {', '.join(md_files)}")

            # Use the directory name as the section title, replacing underscores with spaces
            # Example: '01_Introduction' becomes '01 Introduction'
            section_title = os.path.basename(current_dir).replace('_', ' ').strip()
            # If the current directory is the root, use '.' as the key, otherwise use the cleaned name
            json_key = section_title if abs_current_dir != abs_root_dir else "."

            items = [] # List to hold file metadata dictionaries

            # Process each markdown/mdx file found
            for md_file in md_files:
                md_files_processed += 1 # Increment markdown file counter
                filename = md_file # Store the full filename

                # --- Extract order and title from filename ---
                # Regex breakdown:
                # ^(\d+)     : Match one or more digits at the beginning (capture group 1: order)
                # _*         : Match zero or more underscores
                # (.+)       : Match one or more characters (capture group 2: raw title)
                # \.(mdx?)   : Match a literal dot '.', then 'md', then optionally 'x' (capture group 3: extension)
                # $          : End of the string
                match = re.match(r'^(\d+)_*(.+)\.(mdx?)$', md_file) # mdx? makes 'x' optional
                if match:
                    order = int(match.group(1)) # Extract the leading number as order
                    raw_title = match.group(2) # Extract the part after number(s) and underscore(s)
                    # extension = match.group(3) # The actual extension (.md or .mdx) - not used here but available
                else:
                    # Fallback if filename doesn't match the pattern (e.g., no leading number)
                    order = None
                    # Remove .md or .mdx extension for the raw title
                    if md_file.endswith('.mdx'):
                        raw_title = md_file[:-4] # Remove .mdx
                    else:
                        raw_title = md_file[:-3] # Remove .md

                # Clean up the title: replace underscores with spaces
                # Example: 'My_File_Name' becomes 'My File Name'
                title = re.sub(r'_', ' ', raw_title).strip()

                # Append the extracted metadata to the items list
                item_data = {
                    "file": filename, # The original filename
                    "title": title,   # The cleaned title
                    "order": order    # The extracted order (or None)
                }
                items.append(item_data)
                print(f"  - Processed '{filename}': title='{title}', order={order}")


            # Sort items based on the extracted 'order' number
            # Files without an order number (order is None) will be placed at the end
            # using float('inf') as a key ensures None values sort last.
            items.sort(key=lambda x: x['order'] if x['order'] is not None else float('inf'))

            # Create the final dictionary structure for _meta.json
            # The key is the cleaned directory name (section title)
            meta = {
                section_title: items
            }

            # --- Write _meta.json file ---
            meta_file_path = os.path.join(current_dir, '_meta.json')
            try:
                # Write the dictionary to the _meta.json file
                # Use UTF-8 encoding for broad compatibility
                # Use indent=2 for readability
                with open(meta_file_path, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, indent=2)
                print(f"Successfully generated: {os.path.abspath(meta_file_path)}")
            except IOError as e:
                print(f"Error writing _meta.json to {os.path.abspath(meta_file_path)}: {e}")
            except Exception as e:
                 print(f"An unexpected error occurred while writing _meta.json in {abs_current_dir}: {e}")


    # --- Print Summary ---
    print("\n--- Processing Summary ---")
    print(f"Directories scanned: {dirs_scanned}")
    print(f"Markdown/MDX files processed: {md_files_processed}")
    print(f"_meta.json files created/updated: {meta_files_created}")
    print("--------------------------")

# --- Main execution block ---
if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Generate _meta.json files for directories containing .md/.mdx files.")
    parser.add_argument("root_dir",
                        nargs='?', # Makes the argument optional
                        default='.', # Default to current directory if no argument is given
                        help="The root directory to start scanning (default: current directory)")

    # Parse arguments
    args = parser.parse_args()

    # Call the main function with the specified or default directory
    generate_meta_json(args.root_dir)
# --- End Main execution block ---
