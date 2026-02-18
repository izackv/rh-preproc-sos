#!/usr/bin/env python3
"""
RHEL SOS Report Analyzer
========================
Reads an sosreport directory and produces categorized Markdown files
suitable for upload to NotebookLM, Gemini Gems, or similar AI tools.

Usage:
    python sosreport_analyzer.py /path/to/sosreport /path/to/output
"""

import os
import sys
import glob
from datetime import datetime
from pathlib import Path

from subjects import SUBJECTS, DEFAULT_MAX_LINES, LOG_MAX_LINES
from issue_checks import ISSUE_CHECKS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TRUNCATION_NOTICE = "\n... [TRUNCATED — showing last {n} lines] ...\n"
MAX_WORDS_PER_FILE = 499000  # NotebookLM limit (500K) with safety margin
WORD_TRUNCATION_NOTICE = "\n\n... [TRUNCATED — content exceeded word limit, showing last {n} words] ...\n\n"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def confirm_prompt(message: str) -> bool:
    """Ask user for yes/no confirmation."""
    while True:
        response = input(f"{message} [y/N]: ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no", ""):
            return False
        print("Please enter 'y' or 'n'.")


def is_valid_sos_directory(path: str) -> tuple[bool, list[str]]:
    """
    Check if the given path looks like a valid sosreport directory.
    Returns (is_valid, list_of_found_indicators).
    """
    # Common directories and files found in sosreport
    sos_indicators = [
        "sos_commands",
        "etc",
        "proc",
        "var",
        "sos_logs",
        "sos_reports",
        "installed-rpms",
        "uname",
        "hostname",
        "uptime",
        "date",
        "free",
        "version.txt",
    ]

    found = []
    for indicator in sos_indicators:
        full_path = os.path.join(path, indicator)
        if os.path.exists(full_path):
            found.append(indicator)

    # Consider valid if we find at least sos_commands + 2 others, or 4+ indicators
    has_sos_commands = "sos_commands" in found
    is_valid = (has_sos_commands and len(found) >= 3) or len(found) >= 4

    return is_valid, found


def read_file_safe(filepath: str, max_lines: int = DEFAULT_MAX_LINES) -> str | None:
    """Read a file, return content truncated to max_lines (from the tail)."""
    if not os.path.isfile(filepath):
        return None
    try:
        with open(filepath, "r", errors="replace") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            notice = TRUNCATION_NOTICE.format(n=max_lines)
            return notice + "".join(lines[-max_lines:])
        return "".join(lines)
    except Exception as e:
        return f"[ERROR reading file: {e}]"


def resolve_paths(sos_root: str, file_list: list[str], glob_patterns: list[str]) -> list[str]:
    """Resolve explicit file paths and glob patterns into a deduplicated, sorted list."""
    found = set()

    for relpath in file_list:
        full = os.path.join(sos_root, relpath)
        if os.path.isfile(full):
            found.add(full)
        elif os.path.isdir(full):
            for root, _, files in os.walk(full):
                for fname in files:
                    found.add(os.path.join(root, fname))

    for pattern in glob_patterns:
        for match in glob.glob(os.path.join(sos_root, pattern), recursive=False):
            if os.path.isfile(match):
                found.add(match)
            elif os.path.isdir(match):
                for root, _, files in os.walk(match):
                    for fname in files:
                        found.add(os.path.join(root, fname))

    return sorted(found)


def make_relative(path: str, sos_root: str) -> str:
    """Return path relative to sos_root."""
    return os.path.relpath(path, sos_root)


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def truncate_to_word_limit(content: str, max_words: int) -> tuple[str, bool]:
    """
    Truncate content to max_words, keeping the end (most recent data).
    Preserves line structure by truncating whole lines.
    Returns (truncated_content, was_truncated).
    """
    total_words = count_words(content)
    if total_words <= max_words:
        return content, False

    # Truncate by lines from the end, preserving line breaks
    lines = content.splitlines(keepends=True)
    kept_lines = []
    word_count = 0

    # Work backwards, keeping lines until we hit the word limit
    for line in reversed(lines):
        line_words = len(line.split())
        if word_count + line_words > max_words:
            break
        kept_lines.append(line)
        word_count += line_words

    # Reverse to restore original order
    kept_lines.reverse()
    notice = WORD_TRUNCATION_NOTICE.format(limit=max_words, n=word_count)
    return notice + "".join(kept_lines), True


def build_subject_md(sos_root: str, subject_def: dict) -> str:
    """Build the markdown content for one subject, respecting word limits."""
    # Build header
    header_lines = [
        f"# {subject_def['title']}",
        "",
        f"> {subject_def['description']}",
        "",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> SOS Report: `{os.path.basename(sos_root)}`",
        "",
        "---",
        "",
    ]
    header = "\n".join(header_lines)

    file_list = subject_def.get("files", [])
    glob_patterns = subject_def.get("globs", [])
    max_lines = subject_def.get("max_lines", DEFAULT_MAX_LINES)
    resolved = resolve_paths(sos_root, file_list, glob_patterns)

    if not resolved:
        return header + "*No matching files found in this sosreport.*"

    # Build content sections
    content_lines = []
    files_found = 0
    for filepath in resolved:
        relpath = make_relative(filepath, sos_root)
        content = read_file_safe(filepath, max_lines=max_lines)
        if content is None:
            continue

        content = content.strip()
        if not content:
            continue

        files_found += 1
        content_lines.append(f"## {relpath}")
        content_lines.append("")
        content_lines.append("```")
        content_lines.append(content)
        content_lines.append("```")
        content_lines.append("")

    if files_found == 0:
        return header + "*No readable files with content found for this subject.*"

    content = "\n".join(content_lines)

    # Build footer
    footer = f"\n---\n*Total files included: {files_found}*"

    # Calculate word budget for content (exclude header and footer)
    header_words = count_words(header)
    footer_words = count_words(footer)
    truncation_notice_words = 20  # Approximate words in truncation notice
    content_word_budget = MAX_WORDS_PER_FILE - header_words - footer_words - truncation_notice_words

    # Truncate content if necessary
    content_words = count_words(content)
    was_truncated = False
    if content_words > content_word_budget:
        content, was_truncated = truncate_to_word_limit(content, content_word_budget)
        if was_truncated:
            print(f"      (content truncated from {content_words} to ~{content_word_budget} words)")

    return header + content + footer


def build_issues_md(sos_root: str) -> str:
    """Build the issues investigation markdown, respecting word limits."""
    # Build header
    header_lines = [
        "# Issues Investigation Report",
        "",
        "> Automated scan of the sosreport for common problems and red flags.",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> SOS Report: `{os.path.basename(sos_root)}`",
        "",
        "---",
        "",
    ]

    # System identity section (part of header)
    header_lines.append("## System Identity")
    header_lines.append("")
    for quick_file in ["etc/redhat-release", "sos_commands/kernel/uname_-a",
                       "sos_commands/host/hostnamectl", "uptime"]:
        content = read_file_safe(os.path.join(sos_root, quick_file), max_lines=20)
        if content:
            header_lines.append(f"**{quick_file}:**")
            header_lines.append(f"```\n{content.strip()}\n```")
            header_lines.append("")
    header_lines.append("---")
    header_lines.append("")

    header = "\n".join(header_lines)

    # --- Run each issue check (main content) ---
    content_lines = []
    issues_found = 0
    clean_checks = []

    for check_def in ISSUE_CHECKS:
        source_path = os.path.join(sos_root, check_def["source"])
        content = read_file_safe(source_path, max_lines=LOG_MAX_LINES)

        if content is None:
            continue

        triggered = False
        try:
            triggered = check_def["check"](content)
        except Exception:
            triggered = False

        if not triggered:
            clean_checks.append(check_def["name"])
            continue

        issues_found += 1
        content_lines.append(f"## {check_def['name']}")
        content_lines.append("")
        content_lines.append(f"**Source:** `{check_def['source']}`")
        content_lines.append(f"**What this means:** {check_def['description']}")
        content_lines.append("")

        # Apply filter if defined, otherwise show full (truncated) content
        display_content = content
        if "filter" in check_def:
            try:
                all_lines = content.splitlines()
                filtered = check_def["filter"](all_lines)
                if filtered:
                    display_content = "\n".join(filtered)
                else:
                    display_content = content
            except Exception:
                display_content = content

        content_lines.append("```")
        content_lines.append(display_content.strip())
        content_lines.append("```")
        content_lines.append("")
        content_lines.append("---")
        content_lines.append("")

    main_content = "\n".join(content_lines)

    # --- Build footer (summary and next steps) ---
    footer_lines = [
        "## Summary",
        "",
        f"- **Issues flagged:** {issues_found}",
        f"- **Checks passed:** {len(clean_checks)}",
        "",
    ]

    if clean_checks:
        footer_lines.append("### Clean Checks (no issues detected)")
        footer_lines.append("")
        for name in clean_checks:
            footer_lines.append(f"- {name}")
        footer_lines.append("")

    footer_lines.extend([
        "---",
        "",
        "## Recommended Next Steps",
        "",
        "Use this file together with the subject-specific files to investigate "
        "flagged issues in detail. Upload all generated markdown files to "
        "NotebookLM or Gemini Gems and ask questions like:",
        "",
        '- "What are the critical issues on this system?"',
        '- "Explain the SELinux denials and suggest fixes"',
        '- "Is the storage healthy? Any signs of disk failure?"',
        '- "Are there any security concerns based on the audit log?"',
        '- "What services are failing and why?"',
        '- "Compare this system config against RHEL best practices"',
        "",
    ])

    footer = "\n".join(footer_lines)

    # Calculate word budget for content (exclude header and footer)
    header_words = count_words(header)
    footer_words = count_words(footer)
    truncation_notice_words = 20
    content_word_budget = MAX_WORDS_PER_FILE - header_words - footer_words - truncation_notice_words

    # Truncate content if necessary
    content_words = count_words(main_content)
    if content_words > content_word_budget:
        main_content, was_truncated = truncate_to_word_limit(main_content, content_word_budget)
        if was_truncated:
            print(f"      (content truncated from {content_words} to ~{content_word_budget} words)")

    return header + main_content + footer


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) < 3:
        print("Usage: python sosreport_analyzer.py <sosreport_dir> <output_dir>")
        print()
        print("Example:")
        print("  python sosreport_analyzer.py /tmp/sosreport-myhost-2025 /tmp/analysis_output")
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
