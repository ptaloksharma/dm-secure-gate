"""DM SecureGate — modular source scanner and standardized report contract.

The CLI engine statically inspects a target repository for three baseline
security weaknesses and emits a single, machine-readable JSON report:

  * CWE-798  Use of Hard-coded Credentials
  * CWE-306  Missing Authentication for Critical Function
  * CWE-942  Permissive Cross-domain Policy with Untrusted Domains (wildcard CORS)

The report schema is defined in ``report.py`` and is the contract between the
CLI engine and any consumer (including the Next.js dashboard under web-ui/).
"""
from .report import (
    Severity,
    Finding,
    ScanReport,
    build_report,
    grade_for_counts,
    SEVERITY_ORDER,
)
from .checks import (
    Check,
    CheckContext,
    check_hardcoded_credentials,
    check_missing_auth_boundary,
    check_wildcard_cors,
    ALL_CHECKS,
)
from .scanner import scan_path, discover_files
from .cli import main

__all__ = [
    "Severity", "Finding", "ScanReport", "build_report", "grade_for_counts",
    "SEVERITY_ORDER", "Check", "CheckContext", "check_hardcoded_credentials",
    "check_missing_auth_boundary", "check_wildcard_cors", "ALL_CHECKS",
    "scan_path", "discover_files", "main",
]
