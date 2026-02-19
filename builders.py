"""
Markdown builders for SOS Report Analyzer.

Builds the categorized subject files and the issues investigation report.
"""

import os
from datetime import datetime

from subjects import DEFAULT_MAX_LINES, LOG_MAX_LINES
from issue_checks import ISSUE_CHECKS
from utils import (
    read_file_safe,
    resolve_paths,
    make_relative,
    heading_anchor,
    count_words,
    truncate_to_word_limit,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MAX_WORDS_PER_FILE = 499000  # NotebookLM limit (500K) with safety margin


# ---------------------------------------------------------------------------
# Subject markdown builder
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Issues investigation markdown builder
# ---------------------------------------------------------------------------
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

    # --- Run each issue check ---
    triggered_checks = []  # list of (check_def, display_content)
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

        # Determine display content
        display_content = content
        if "filter" in check_def:
            try:
                all_lines = content.splitlines()
                filtered = check_def["filter"](all_lines)
                if filtered:
                    display_content = "\n".join(filtered)
                else:
                    display_content = None
            except Exception:
                display_content = content

        triggered_checks.append((check_def, display_content))

    # --- Build summary (placed right after header) ---
    summary_lines = [
        "## Summary",
        "",
        f"- **Issues flagged:** {len(triggered_checks)}",
        f"- **Checks passed:** {len(clean_checks)}",
        "",
    ]

    if triggered_checks:
        summary_lines.append("### Flagged Issues")
        summary_lines.append("")
        for check_def, _ in triggered_checks:
            anchor = heading_anchor(check_def["name"])
            summary_lines.append(
                f"- [{check_def['name']}](#{anchor}) — {check_def['description']}"
            )
        summary_lines.append("")

    if clean_checks:
        summary_lines.append("### Clean Checks (no issues detected)")
        summary_lines.append("")
        for name in clean_checks:
            summary_lines.append(f"- {name}")
        summary_lines.append("")

    summary_lines.append("---")
    summary_lines.append("")
    summary = "\n".join(summary_lines)

    # --- Build detail sections for each triggered issue ---
    detail_lines = []
    for check_def, display_content in triggered_checks:
        detail_lines.append(f"## {check_def['name']}")
        detail_lines.append("")
        detail_lines.append(f"**Source:** `{check_def['source']}`")
        detail_lines.append(f"**What this means:** {check_def['description']}")
        detail_lines.append("")

        if display_content is None:
            terms = check_def.get("filter_terms", "the specified patterns")
            detail_lines.append(
                f"*Searched `{check_def['source']}` for {terms} "
                f"— no matching lines found.*"
            )
        else:
            detail_lines.append("```")
            detail_lines.append(display_content.strip())
            detail_lines.append("```")
        detail_lines.append("")
        detail_lines.append("---")
        detail_lines.append("")

    main_content = "\n".join(detail_lines)

    # --- Build footer (next steps) ---
    footer_lines = [
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
    ]
    footer = "\n".join(footer_lines)

    # Calculate word budget for detail content (exclude header, summary, footer)
    header_words = count_words(header)
    summary_words = count_words(summary)
    footer_words = count_words(footer)
    truncation_notice_words = 20
    content_word_budget = (MAX_WORDS_PER_FILE - header_words - summary_words
                           - footer_words - truncation_notice_words)

    # Truncate detail content if necessary
    content_words = count_words(main_content)
    if content_words > content_word_budget:
        main_content, was_truncated = truncate_to_word_limit(main_content, content_word_budget)
        if was_truncated:
            print(f"      (content truncated from {content_words} to ~{content_word_budget} words)")

    return header + summary + main_content + footer
