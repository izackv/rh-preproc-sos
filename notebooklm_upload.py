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
from datetime import date
from pathlib import Path

from reference_urls import get_reference_urls
from skill_template import STATIC_SKILL


def build_notebook_instructions(system_meta: dict) -> str:
    dynamic_header = f"""\
## System Under Analysis

- **Host:**          {system_meta.get('hostname', 'See 01_system_overview.md')}
- **RHEL Version:**  {system_meta.get('rhel_version', 'See 01_system_overview.md')}
- **Architecture:**  {system_meta.get('arch', 'See 01_system_overview.md')}
- **Analysis Date:** {system_meta.get('date', date.today().isoformat())}
- **SOS Report:**    {system_meta.get('sos_report_name', 'See 01_system_overview.md')}

"""
    return dynamic_header + STATIC_SKILL


async def upload_to_notebooklm(
    output_dir: str,
    notebook_name: str,
    rhel_version: int | None = None,
) -> str:
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

    instructions = build_notebook_instructions({"sos_report_name": notebook_name})

    # Write instructions as a source file to upload alongside the data
    instructions_file = output_path / "00_notebook_instructions.md"
    instructions_file.write_text(instructions)

    # Re-discover .md files so the instructions file is included
    md_files = sorted(output_path.glob("*.md"))

    async with await NotebookLMClient.from_storage() as client:
        # Create notebook
        print(f"Creating notebook: {notebook_name}")
        notebook = await client.notebooks.create(notebook_name)
        notebook_id = notebook.id
        print(f"  Notebook created (ID: {notebook_id})")

        # Add instructions as a note with guidance to set as conversation goal
        note_content = (
            "IMPORTANT: Copy the contents below into the conversation "
            "goals for best results.\n"
            "\n"
            "How to do it:\n"
            '  1. Open chat settings (gear icon in the chat panel)\n'
            '  2. Under "Conversation goals", select "Custom"\n'
            "  3. Paste the text below into the custom goals field\n"
            "  4. Click Save\n"
            "\n"
            "Setting custom conversation goals acts as a system prompt "
            "that shapes every response. The same instructions are also "
            "uploaded as a source (00_notebook_instructions.md), but "
            "conversation goals are more binding for behavioral rules "
            "like triage workflow, severity classification, and tone.\n"
            "\n"
            "---\n"
            "\n"
        ) + instructions
        await client.notes.create(
            notebook_id,
            title="Setup: Copy this into Notebook Guide",
            content=note_content,
        )
        print(f"  Added instructions note")
        print()

        # Upload each file (including 00_notebook_instructions.md)
        uploaded = 0
        for md_file in md_files:
            try:
                await client.sources.add_file(notebook_id, md_file)
                print(f"  Uploaded: {md_file.name}")
                uploaded += 1
            except Exception as e:
                print(f"  FAILED:   {md_file.name} — {e}")

        # Upload reference URLs
        ref_urls = get_reference_urls(rhel_version)
        if ref_urls:
            print()
            version_label = f"RHEL {rhel_version}" if rhel_version else "default"
            print(f"  Adding {len(ref_urls)} reference URLs ({version_label})...")
            for url in ref_urls:
                try:
                    await client.sources.add_url(notebook_id, url)
                    # Show just the doc name, not the full URL
                    short = url.rsplit("/", 2)[-2] if "/html-single/" in url else url.split("/")[-1]
                    print(f"  Uploaded: {short}")
                    uploaded += 1
                except Exception as e:
                    print(f"  FAILED:   {url} — {e}")

        # Summary
        print()
        print(f"{'=' * 50}")
        print(f"Notebook:  {notebook_name}")
        total = len(md_files) + len(ref_urls)
        print(f"Uploaded:  {uploaded}/{total} sources ({len(md_files)} files, {len(ref_urls)} URLs)")
        print(f"URL:       https://notebooklm.google.com/notebook/{notebook_id}")
        print()
        print("ACTION REQUIRED:")
        print("  Open the notebook and find the note titled")
        print('  "Setup: Copy this into Notebook Guide".')
        print("  Copy its contents into the conversation goals:")
        print('  Chat settings > Conversation goals > Custom')
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
