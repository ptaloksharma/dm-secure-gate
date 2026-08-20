"""File discovery + per-file check orchestration."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, List, Tuple

from .checks import ALL_CHECKS, Check, CheckContext, SKIP_DIRS, SKIP_EXT
from .report import Finding

# A global auth middleware / dependency present anywhere in the repo means the
# app gates requests centrally, so per-route decorator absence is NOT a finding.
_GLOBAL_AUTH_RE = __import__("re").compile(
    r"(?i)(add_middleware\([^)]*auth|middleware\(.http.\)|"
    r"app\.middleware\(|require_api_key|verify_api_key|auth_middleware)"
)


def discover_files(root: str) -> Iterator[Tuple[str, str]]:
    """Yield (rel_path, abs_path) for scannable files under ``root``."""
    root_path = Path(root).resolve()
    for dirpath, dirnames, filenames in os.walk(root_path):
        # prune skipped dirs in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if Path(name).suffix.lower() in SKIP_EXT:
                continue
            abs_path = os.path.join(dirpath, name)
            try:
                rel = os.path.relpath(abs_path, root_path)
            except ValueError:
                rel = abs_path
            # defensive: never scan vendored dependency trees
            if "site-packages" in rel.split(os.sep) or ".venv" in rel.split(os.sep):
                continue
            yield rel, abs_path


def scan_path(root: str, checks: List[Check] = ALL_CHECKS) -> Tuple[int, List[Finding]]:
    """Run all checks across every scannable file. Returns (files_scanned, findings)."""
    files_scanned = 0
    findings: List[Finding] = []
    has_global_auth = False
    file_contexts = []
    for rel, abs_path in discover_files(root):
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        if "\x00" in text:
            continue
        files_scanned += 1
        lines = text.splitlines()
        ctx = CheckContext(repo_root=root, rel_path=rel, lines=lines, text=text)
        file_contexts.append(ctx)
        if _GLOBAL_AUTH_RE.search(text):
            has_global_auth = True
    for ctx in file_contexts:
        for check in checks:
            # The missing-auth check is suppressed when the repo enforces auth
            # globally (middleware), avoiding false positives on middleware-gated apps.
            if check.__name__ == "check_missing_auth_boundary" and has_global_auth:
                continue
            findings.extend(check(ctx))
    return files_scanned, findings
