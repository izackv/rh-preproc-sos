#!/usr/bin/env python3
"""
RHEL SOS Report Analyzer
========================
Reads an sosreport directory and produces categorized Markdown files
suitable for upload to NotebookLM, Gemini Gems, or similar AI tools.

Usage:
    python preproc-sos.py /path/to/sosreport /path/to/output
"""

import os
import sys

from subjects import SUBJECTS
from utils import confirm_prompt, is_valid_sos_directory
from builders import build_subject_md, build_issues_md


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) < 3:
        print("Usage: python preproc-sos.py <sosreport_dir> <output_dir>")
        print()
        print("Example:")
        print("  python preproc-sos.py /tmp/sosreport-myhost-2025 /tmp/analysis_output")
        sys.exit(1)

    sos_root = os.path.abspath(sys.argv[1])
    output_dir = os.path.abspath(sys.argv[2])

    # --- Validate SOS directory exists ---
    if not os.path.isdir(sos_root):
        print(f"ERROR: sosreport directory not found: {sos_root}")
        sys.exit(1)

    # --- Validate SOS directory looks like a valid sosreport ---
    is_valid, found_indicators = is_valid_sos_directory(sos_root)
    if not is_valid:
        print(f"ERROR: Directory does not appear to be a valid sosreport: {sos_root}")
        print()
        if found_indicators:
            print(f"  Found only: {', '.join(found_indicators)}")
        else:
            print("  No sosreport indicators found (sos_commands, etc, proc, var, installed-rpms, ...)")
        print()
        print("A valid sosreport directory should contain 'sos_commands/' and other")
        print("diagnostic directories like 'etc/', 'proc/', 'var/', etc.")
        sys.exit(1)

    # --- Handle output directory ---
    if not os.path.exists(output_dir):
        # Output directory doesn't exist - create it
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: {output_dir}")
        print()
    elif os.path.isdir(output_dir):
        # Output directory exists - check if it's the same as SOS directory
        if os.path.samefile(sos_root, output_dir):
            print(f"ERROR: Output directory cannot be the same as the sosreport directory!")
            print(f"  SOS directory: {sos_root}")
            print(f"  Output directory: {output_dir}")
            print()
            print("Please specify a different output directory.")
            sys.exit(1)

        # Check if output directory is not empty
        existing_items = os.listdir(output_dir)
        if existing_items:
            print(f"Output directory is not empty: {output_dir}")
            print()
            # Show up to 10 items
            display_items = existing_items[:10]
            print("  Existing items:")
            for item in display_items:
                item_path = os.path.join(output_dir, item)
                item_type = "dir" if os.path.isdir(item_path) else "file"
                print(f"    - {item} ({item_type})")
            if len(existing_items) > 10:
                print(f"    ... and {len(existing_items) - 10} more items")
            print()
            if not confirm_prompt("Continue? (some existing files may be overwritten)"):
                print("Aborted.")
                sys.exit(0)
            print()
    else:
        print(f"ERROR: Output path exists but is not a directory: {output_dir}")
        sys.exit(1)

    print(f"SOS Report Analyzer")
    print(f"{'=' * 50}")
    print(f"Source:  {sos_root}")
    print(f"Output:  {output_dir}")
    print()

    # Generate subject files
    for key, subject_def in SUBJECTS.items():
        print(f"  Generating: {key}.md — {subject_def['title']}...")
        md_content = build_subject_md(sos_root, subject_def)
        out_path = os.path.join(output_dir, f"{key}.md")
        with open(out_path, "w") as f:
            f.write(md_content)
        size_kb = os.path.getsize(out_path) / 1024
        print(f"    → {out_path} ({size_kb:.1f} KB)")

    # Generate issues investigation file
    print(f"  Generating: 00_issues_investigation.md...")
    issues_md = build_issues_md(sos_root)
    issues_path = os.path.join(output_dir, "00_issues_investigation.md")
    with open(issues_path, "w") as f:
        f.write(issues_md)
    size_kb = os.path.getsize(issues_path) / 1024
    print(f"    → {issues_path} ({size_kb:.1f} KB)")

    print()
    print(f"{'=' * 50}")
    print(f"Done! {len(SUBJECTS) + 1} files generated in: {output_dir}")
    print()
    print("Recommended workflow:")
    print("  1. Start with 00_issues_investigation.md to see flagged problems")
    print("  2. Dive into subject-specific files for detailed analysis")
    print("  3. Upload all .md files to NotebookLM or Gemini Gems")
    print()


if __name__ == "__main__":
    main()
