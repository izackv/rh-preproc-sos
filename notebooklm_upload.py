#!/usr/bin/env python3
"""
NotebookLM Upload
=================
Creates a NotebookLM notebook and uploads all .md files from a directory.

Requires:
    pip install "notebooklm-py[browser]"
    playwright install chromium
    notebooklm login  (one-time Google sign-in)

Usage (standalone):
    python notebooklm_upload.py <output_dir> [--name "My Notebook"]
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path


async def upload_to_notebooklm(output_dir: str, notebook_name: str) -> str:
    """Create a NotebookLM notebook and upload all .md files from output_dir.

    Returns the notebook ID.
    """
    try:
        from notebooklm import NotebookLMClient
    except ImportError:
        print("ERROR: notebooklm-py is required for NotebookLM upload.")
        print()
        print("Set up a virtual environment and install:")
        print("  python3 -m venv .venv")
        print("  source .venv/bin/activate")
        print('  pip install "notebooklm-py[browser]"')
        print("  playwright install chromium")
        print("  notebooklm login")
        sys.exit(1)

    output_path = Path(output_dir)
    md_files = sorted(output_path.glob("*.md"))

    if not md_files:
        print(f"ERROR: No .md files found in {output_dir}")
        sys.exit(1)

    print(f"Found {len(md_files)} markdown files to upload")
    print()

    async with await NotebookLMClient.from_storage() as client:
        # Create notebook
        print(f"Creating notebook: {notebook_name}")
        notebook = await client.notebooks.create(notebook_name)
        notebook_id = notebook.id
        print(f"  Notebook created (ID: {notebook_id})")
        print()

        # Upload each file
        uploaded = 0
        for md_file in md_files:
            try:
                await client.sources.add_file(notebook_id, md_file)
                print(f"  Uploaded: {md_file.name}")
                uploaded += 1
            except Exception as e:
                print(f"  FAILED:   {md_file.name} — {e}")

        # Summary
        print()
        print(f"{'=' * 50}")
        print(f"Notebook:  {notebook_name}")
        print(f"Uploaded:  {uploaded}/{len(md_files)} sources")
        print(f"URL:       https://notebooklm.google.com/notebook/{notebook_id}")
        print(f"{'=' * 50}")

    return notebook_id


def main():
    parser = argparse.ArgumentParser(
        description="Upload markdown files to a NotebookLM notebook"
    )
    parser.add_argument(
        "output_dir",
        help="Directory containing .md files to upload",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Notebook name (defaults to directory basename)",
    )
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output_dir)
    notebook_name = args.name or os.path.basename(output_dir)

    if not os.path.isdir(output_dir):
        print(f"ERROR: Directory not found: {output_dir}")
        sys.exit(1)

    asyncio.run(upload_to_notebooklm(output_dir, notebook_name))


if __name__ == "__main__":
    main()
