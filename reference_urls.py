"""
Reference URLs for NotebookLM upload.

URLs are organized by RHEL major version. The "common" list is always included.
Edit this file to add, remove, or update reference documentation URLs.
"""

# Always uploaded regardless of RHEL version
COMMON_URLS = [
    "https://github.com/sosreport/sos/wiki",
    "https://github.com/myllynen/rhel-troubleshooting-guide",
]

# Per-RHEL-version URLs (keyed by major version as int)
# Uses docs.redhat.com (publicly accessible, no login required)
VERSION_URLS = {
    9: [
        # Networking
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/configuring_and_managing_networking/index",
        # Storage
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/managing_storage_devices/index",
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/managing_file_systems/index",
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/configuring_and_managing_logical_volumes/index",
        # Performance & kernel
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/monitoring_and_managing_system_status_and_performance/index",
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/managing_monitoring_and_updating_the_kernel/index",
        # System administration & systemd
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/configuring_basic_system_settings/index",
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/using_systemd_unit_files_to_customize_and_optimize_your_system/index",
        # Security
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/using_selinux/index",
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/security_hardening/index",
    ],
    8: [
        # Networking
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/configuring_and_managing_networking/index",
        # Storage
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/managing_storage_devices/index",
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/managing_file_systems/index",
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/configuring_and_managing_logical_volumes/index",
        # Performance & kernel
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/monitoring_and_managing_system_status_and_performance/index",
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/managing_monitoring_and_updating_the_kernel/index",
        # System administration
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/configuring_basic_system_settings/index",
        # Security
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/using_selinux/index",
        "https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html-single/security_hardening/index",
    ],
}


def get_reference_urls(rhel_major_version: int | None) -> list[str]:
    """Return the list of reference URLs for the given RHEL major version.

    Includes common URLs plus version-specific URLs.
    Falls back to RHEL 9 if the version is unknown.
    """
    urls = list(COMMON_URLS)
    version = rhel_major_version or 9
    urls.extend(VERSION_URLS.get(version, VERSION_URLS[9]))
    return urls
