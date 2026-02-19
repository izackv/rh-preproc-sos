"""
Utility functions for SOS Report Analyzer.

Generic helpers for file I/O, path resolution, text truncation,
directory validation, and user interaction.
"""

import os
import glob
import re

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRUNCATION_NOTICE = "\n... [TRUNCATED — showing last {n} lines] ...\n"
WORD_TRUNCATION_NOTICE = "\n\n... [TRUNCATED — content exceeded word limit, showing last {n} words] ...\n\n"


# ---------------------------------------------------------------------------
# User interaction
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


# ---------------------------------------------------------------------------
# Directory validation
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# SOS metadata
# ---------------------------------------------------------------------------
def detect_rhel_version(sos_root: str) -> int | None:
    """Detect the RHEL major version from etc/redhat-release in the sosreport.

    Returns the major version as int (e.g., 8 or 9), or None if undetectable.
    """
    release_file = os.path.join(sos_root, "etc", "redhat-release")
    if not os.path.isfile(release_file):
        return None
    try:
        with open(release_file, "r") as f:
            content = f.read().strip()
        # e.g. "Red Hat Enterprise Linux release 9.3 (Plow)"
        match = re.search(r"release\s+(\d+)", content)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------
def read_file_safe(filepath: str, max_lines: int = 1500) -> str | None:
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


# ---------------------------------------------------------------------------
# Text processing
# ---------------------------------------------------------------------------
def heading_anchor(name: str) -> str:
    """Convert a heading name to a markdown anchor link."""
    anchor = name.lower()
    anchor = "".join(c for c in anchor if c.isalnum() or c in " -")
    anchor = anchor.replace(" ", "-")
    while "--" in anchor:
        anchor = anchor.replace("--", "-")
    return anchor.strip("-")


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
