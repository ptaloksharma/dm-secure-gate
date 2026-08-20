"""Command-line entrypoint for the DM SecureGate scanner."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List

from .checks import ALL_CHECKS
from .report import ScanReport, build_report
from .scanner import scan_path


def run_scan(target: str) -> ScanReport:
    target = os.path.abspath(target)
    if not os.path.isdir(target):
        raise SystemExit(f"error: target is not a directory: {target}")
    files_scanned, findings = scan_path(target, checks=ALL_CHECKS)
    return build_report(
        target=target,
        files_scanned=files_scanned,
        checks_run=[c.__name__ for c in ALL_CHECKS],
        findings=findings,
    )


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="securegate",
        description="DM SecureGate — static security baseline scanner "
                    "(CWE-798, CWE-306, CWE-942).",
    )
    parser.add_argument("target", nargs="?", default=".", help="repo path to scan")
    parser.add_argument("-o", "--output", help="write JSON report to this path")
    parser.add_argument("--quiet", action="store_true", help="suppress console summary")
    args = parser.parse_args(argv)

    report = run_scan(args.target)

    if args.output:
        out = os.path.abspath(args.output)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(report.to_json())
        if not args.quiet:
            print(f"Report written to {out}")

    if not args.quiet:
        print(report.to_json())
    else:
        # even in quiet mode, surface the grade + counts to stderr
        print(
            f"grade={report.grade} critical={report.counts.get('Critical',0)} "
            f"high={report.counts.get('High',0)} "
            f"medium={report.counts.get('Medium',0)} "
            f"findings={len(report.findings)}",
            file=sys.stderr,
        )
    # Non-zero exit on Critical/High so CI can gate on it.
    if report.counts.get("Critical", 0) or report.counts.get("High", 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
