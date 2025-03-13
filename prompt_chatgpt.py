#!/usr/bin/env python3
"""
combine_python_files.py

This script scans the current directory and all its subdirectories for Python (.py) files, excludes specified files,
adds a comment with the relative path at the top of each included file, and combines them into
a single .txt file.

Usage:
    python combine_python_files.py [--exclude substr1 substr2 ...] [--output output_filename.txt]

Example:
    python combine_python_files.py --exclude test util --output all_scripts.txt
"""

import os
import argparse
from pathlib import Path

def parse_arguments():
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments containing excluded substrings and output filename.
    """
    parser = argparse.ArgumentParser(
        description="Combine Python files into a single .txt file with relative paths."
    )
    parser.add_argument(
        '--exclude',
        nargs='*',
        default=["linear_model_old", "prompt_chatgpt"],
        help='List of substrings. Files containing any of these substrings in their filenames will be excluded.'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='combined_python_files.txt',
        help='Name of the output .txt file. Defaults to combined_python_files.txt'
    )
    return parser.parse_args()

def get_python_files(current_dir, excluded_substrings):
    """
    Retrieves all Python files in the current directory and subdirectories, excluding those that match the exclusion criteria.

    Args:
        current_dir (Path): Path object of the current directory.
        excluded_substrings (list): List of substrings to exclude files containing them.

    Returns:
        list: List of Path objects representing the included Python files.
    """
    # Glob all .py files recursively in the current directory and subdirectories
    all_py_files = list(current_dir.rglob('*.py'))

    # Always exclude 'prompt_chatgpt.py'
    excluded_substrings = excluded_substrings.copy()  # Make a copy to avoid modifying the original list
    excluded_substrings.append('prompt_chatgpt.py')

    # Filter out files that contain any of the excluded substrings
    included_files = []
    for file in all_py_files:
        filename = file.name
        if any(excl.lower() in filename.lower() for excl in excluded_substrings):
            print(f"Excluding file: {file.relative_to(current_dir)}")
            continue
        included_files.append(file)

    return included_files

def combine_files(included_files, output_file, current_dir):
    """
    Combines the contents of included Python files into a single .txt file with relative path comments.

    Args:
        included_files (list): List of Path objects for included Python files.
        output_file (Path): Path object for the output .txt file.
        current_dir (Path): Path object of the current directory.
    """
    if not included_files:
        print("No Python files to include.")
        return

    with output_file.open('w', encoding='utf-8') as out_f:
        for file in included_files:
            # Get the relative path from the current directory
            relative_path = file.relative_to(current_dir)
            # Write the comment line
            out_f.write(f"# {relative_path}\n")
            # Write the file contents
            try:
                with file.open('r', encoding='utf-8') as in_f:
                    contents = in_f.read()
                    out_f.write(contents)
            except Exception as e:
                print(f"Error reading {relative_path}: {e}")
                continue
            # Add two newlines to separate files
            out_f.write("\n\n")
        out_f.write("Just modify those files that need so, for those, give the full code once modified. \n")
        
        # If there is a prompt.txt file, add it to the end of the combined file
        prompt_file = current_dir / "prompt.txt"
        if prompt_file.is_file():
            out_f.write("\n\n# Additional Prompt\n")
            with prompt_file.open('r', encoding='utf-8') as in_f:
                contents = in_f.read()
                out_f.write(contents)
            out_f.write("\n\n")
            
    print(f"Combined {len(included_files)} Python files into {output_file}")

def main():
    # Parse command-line arguments
    args = parse_arguments()

    # Define the current directory
    current_dir = Path.cwd()

    # Retrieve the list of Python files to include
    included_files = get_python_files(current_dir, args.exclude)

    # Define the output file path
    output_file = current_dir / args.output

    # Combine the files into the output .txt file
    combine_files(included_files, output_file, current_dir)

if __name__ == "__main__":
    main()
