"""
Issue check definitions for SOS Report Analyzer.

Each check defines a common problem or red flag to look for in sosreport data.
Edit this file to customize which issues are scanned for.

Structure:
    {
        "name": "Display name for the issue",
        "source": "path/to/file/in/sosreport",
        "check": lambda content: <bool expression>,  # Returns True if issue detected
        "filter": lambda lines: <filtered lines>,    # Optional: extract relevant lines
        "filter_terms": "human-readable search terms", # Optional: describes what filter looks for
        "description": "What this issue means",
    }
"""

import re

ISSUE_CHECKS = [
    {
        "name": "Failed Systemd Units",
        "source": "sos_commands/systemd/systemctl_list-units_--failed",
        "check": lambda content: content.strip() and "0 loaded units listed" not in content,
        "description": "Services that have failed and may need attention.",
    },
    {
        "name": "SELinux Denials in Audit Log",
        "source": "var/log/audit/audit.log",
        "check": lambda content: "denied" in content.lower() or "avc:" in content.lower(),
        "filter": lambda lines: [l for l in lines if "denied" in l.lower() or "avc:" in l.lower()][-200:],
        "filter_terms": "lines containing 'denied' or 'avc:'",
        "description": "SELinux AVC denials that may indicate policy issues.",
    },
    {
        "name": "OOM Killer Events",
        "source": "var/log/messages",
        "check": lambda content: "out of memory" in content.lower() or "oom-killer" in content.lower(),
        "filter": lambda lines: [l for l in lines if "oom" in l.lower()][-100:],
        "filter_terms": "lines containing 'oom'",
        "description": "Out-of-memory killer invocations — system ran out of RAM.",
    },
    {
        "name": "Kernel Errors / Panics / Oops in dmesg",
        "source": "sos_commands/kernel/dmesg",
        "check": lambda content: any(kw in content.lower() for kw in ["error", "panic", "oops", "bug:", "call trace"]),
        "filter": lambda lines: [l for l in lines if any(kw in l.lower() for kw in ["error", "panic", "oops", "bug:", "call trace", "warning"])][-200:],
        "filter_terms": "lines containing 'error', 'panic', 'oops', 'bug:', 'call trace', or 'warning'",
        "description": "Kernel-level errors, panics, or warnings from dmesg.",
    },
    {
        "name": "Filesystem Errors in Logs",
        "source": "var/log/messages",
        "check": lambda content: any(kw in content.lower() for kw in ["ext4-fs error", "xfs error", "i/o error", "buffer i/o error", "filesystem error", "remount,ro"]),
        "filter": lambda lines: [l for l in lines if any(kw in l.lower() for kw in ["ext4", "xfs error", "i/o error", "buffer i/o", "filesystem error", "readonly"])][-100:],
        "filter_terms": "lines containing 'ext4', 'xfs error', 'i/o error', 'buffer i/o', 'filesystem error', or 'readonly'",
        "description": "Filesystem errors that could indicate disk problems.",
    },
    {
        "name": "Disk Space Issues",
        "source": "sos_commands/filesys/df_-al",
        "check": lambda content: any(int(m) >= 90 for m in re.findall(r'(\d+)%', content) if m.isdigit()),
        "filter": lambda lines: [lines[0]] + [l for l in lines[1:] if re.search(r'(9\d|100)%', l)],
        "filter_terms": "lines showing 90–100% disk usage",
        "description": "Filesystems at or above 90% usage.",
    },
    {
        "name": "Network Errors / Drops",
        "source": "sos_commands/networking/ip_-s_link",
        "check": lambda content: True,  # always include for review
        "description": "Network interface statistics — check for RX/TX errors and drops.",
    },
    {
        "name": "Multipath Issues",
        "source": "sos_commands/multipath/multipath_-ll",
        "check": lambda content: any(kw in content.lower() for kw in ["faulty", "failed", "shaky", "ghost"]),
        "description": "Multipath paths that are not in active/ready state.",
    },
    {
        "name": "Core Dumps / Segfaults in Logs",
        "source": "var/log/messages",
        "check": lambda content: any(kw in content.lower() for kw in ["segfault", "core dump", "trapping"]),
        "filter": lambda lines: [l for l in lines if any(kw in l.lower() for kw in ["segfault", "core dump", "trapping"])][-100:],
        "filter_terms": "lines containing 'segfault', 'core dump', or 'trapping'",
        "description": "Application crashes recorded in system logs.",
    },
    {
        "name": "Subscription / Entitlement Warnings",
        "source": "sos_commands/subscription_manager/subscription-manager_status",
        "check": lambda content: "invalid" in content.lower() or "not registered" in content.lower() or "warning" in content.lower(),
        "description": "Subscription manager reporting issues with entitlements.",
    },
    {
        "name": "NTP / Time Sync Issues",
        "source": "sos_commands/date/timedatectl",
        "check": lambda content: "no" in content.lower() and "synchronized" in content.lower(),
        "description": "System clock is not synchronized — could cause auth and log issues.",
    },
    {
        "name": "Kdump / Crash Configuration",
        "source": "etc/kdump.conf",
        "check": lambda content: True,  # always include for reference
        "description": "Kdump configuration — verify crash dump settings.",
    },
    {
        "name": "High Zombie / Defunct Processes",
        "source": "sos_commands/process/ps_auxwww",
        "check": lambda content: content.lower().count("defunct") > 5 or content.lower().count("<zombie>") > 5,
        "filter": lambda lines: [l for l in lines if "defunct" in l.lower() or "zombie" in l.lower()][:100],
        "filter_terms": "lines containing 'defunct' or 'zombie'",
        "description": "Large number of zombie/defunct processes detected.",
    },
    {
        "name": "Hardware Errors (MCE)",
        "source": "sos_commands/hardware/dmidecode",
        "check": lambda content: True,  # always include summary
        "description": "DMI/BIOS data — review for hardware alerts.",
    },
    {
        "name": "Swap Usage",
        "source": "sos_commands/memory/free_-m",
        "check": lambda content: True,  # always include
        "description": "Memory and swap usage — high swap may indicate memory pressure.",
    },
    {
        "name": "Authentication Failures",
        "source": "var/log/secure",
        "check": lambda content: "failed" in content.lower() or "invalid user" in content.lower(),
        "filter": lambda lines: [l for l in lines if "failed" in l.lower() or "invalid user" in l.lower()][-200:],
        "filter_terms": "lines containing 'failed' or 'invalid user'",
        "description": "Failed authentication attempts — potential security concern.",
    },
]
