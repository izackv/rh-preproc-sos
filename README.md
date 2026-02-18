# RHEL SOS Report Analyzer

A Python tool that processes Red Hat Enterprise Linux (RHEL) sosreport directories and generates categorized Markdown files suitable for AI-assisted analysis using tools like NotebookLM, Gemini Gems, or similar platforms.

## Overview

When troubleshooting RHEL systems, sosreport collects extensive diagnostic data that can be overwhelming to parse manually. This analyzer:

- Organizes sosreport data into logical subject categories
- Generates clean Markdown files optimized for AI consumption
- Automatically scans for common issues and red flags
- Truncates large files to manageable sizes while preserving the most relevant (recent) data

## Requirements

- Python 3.10+ (uses type hints with `|` syntax)
- No external dependencies (uses only standard library)

## Usage

```bash
python preproc-sos.py <sosreport_dir> <output_dir>
```

### Example

```bash
python preproc-sos.py /tmp/sosreport-myhost-2025 /tmp/analysis_output
```

## Directory Validation

The script performs several safety checks before processing:

**SOS Report Directory:**
- Validates that the input looks like a valid sosreport by checking for common indicators (`sos_commands/`, `etc/`, `proc/`, `var/`, `installed-rpms`, etc.)
- Requires at least `sos_commands/` plus 2 other indicators, or 4+ indicators total

**Output Directory:**
- If the directory doesn't exist, prompts for permission before creating it
- If the directory is not empty:
  - Prevents writing to the sosreport directory itself (common mistake)
  - Shows existing files/folders and asks for confirmation before overwriting

## Generated Output

The analyzer produces 14 Markdown files:

| File | Description |
|------|-------------|
| `00_issues_investigation.md` | Automated scan for common problems and red flags |
| `01_system_overview.md` | System identification, hardware, BIOS, DMI, kernel info |
| `02_networking.md` | IP addresses, routes, DNS, bonding, firewall rules |
| `03_storage_filesystems.md` | Block devices, mount points, LVM, multipath, fstab |
| `04_services_boot.md` | Systemd units, failed services, boot targets, cron jobs |
| `05_packages_subscriptions.md` | Installed RPMs, repos, subscription manager status |
| `06_security_selinux.md` | SELinux, audit rules, PAM, SSH, crypto policies |
| `07_performance_tuning.md` | Tuned profiles, sysctl, NUMA, resource limits |
| `08a_log_messages.md` | /var/log/messages - main system log |
| `08b_log_dmesg.md` | Kernel ring buffer (dmesg) |
| `08c_log_secure.md` | /var/log/secure - authentication events |
| `08d_log_audit.md` | /var/log/audit/audit.log - SELinux & audit events |
| `08e_log_journal.md` | Systemd journal output |
| `08f_log_boot_cron.md` | Boot and cron logs |

Logs are split into separate files to maximize data for NotebookLM (500K words per source limit).

## Issues Investigation

The `00_issues_investigation.md` file automatically checks for:

- Failed systemd units
- SELinux denials (AVC)
- OOM killer events
- Kernel errors, panics, and oops
- Filesystem errors
- Disk space issues (≥90% usage)
- Network errors and drops
- Multipath issues
- Core dumps and segfaults
- Subscription/entitlement warnings
- NTP/time sync problems
- Zombie processes
- Authentication failures

## Configuration

### Subject Definitions

The subject categories are defined in `subjects.py` for easy customization. Each subject specifies:

- `title`: Display title for the markdown file
- `description`: Brief description of the category
- `max_lines`: Maximum lines to include per file (default: 1,500, logs: 40,000)
- `files`: List of specific file paths to include
- `globs`: Glob patterns to match additional files

```python
# Default limits in subjects.py
DEFAULT_MAX_LINES = 1500      # Config files, command output
LOG_MAX_LINES = 40000         # Logs (~500K words for NotebookLM)
```

Edit `subjects.py` to add, remove, or modify subjects without touching the main logic.

### Issue Checks

The automated issue checks are defined in `issue_checks.py`. Each check specifies:

- `name`: Display name for the issue
- `source`: Path to the file in sosreport to scan
- `check`: Lambda function that returns True if the issue is detected
- `filter`: Optional lambda to extract relevant lines for display
- `description`: What this issue means

Edit `issue_checks.py` to add, remove, or modify which issues are scanned for.

## Recommended Workflow

1. Generate the analysis files:
   ```bash
   python preproc-sos.py /path/to/sosreport /path/to/output
   ```

2. Start with `00_issues_investigation.md` to identify flagged problems

3. Dive into subject-specific files for detailed analysis

4. Upload all `.md` files to NotebookLM or Gemini Gems

5. Ask questions like:
   - "What are the critical issues on this system?"
   - "Explain the SELinux denials and suggest fixes"
   - "Is the storage healthy? Any signs of disk failure?"
   - "Are there any security concerns based on the audit log?"
   - "What services are failing and why?"
   - "Compare this system config against RHEL best practices"

## License

This project is provided as-is for RHEL system administration and troubleshooting purposes.
