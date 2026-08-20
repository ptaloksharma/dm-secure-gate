"""Modular detection checks.

Each check is a pure function taking a :class:`CheckContext` (one file's lines)
and returning a list of :class:`Finding`. Keeping them decoupled makes the
engine trivially extensible and individually testable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, List

from .report import Finding, Severity

# Files / dirs we never inspect.
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".next", "coverage", "strix_runs", ".hermes", ".pytest_cache",
    "site-packages",  # third-party libs: never scan vendored deps
}
SKIP_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf",
    ".eot", ".mp4", ".webm", ".pdf", ".zip", ".gz", ".lock", ".pyc", ".db",
}


@dataclass
class CheckContext:
    repo_root: str
    rel_path: str          # path relative to repo_root
    lines: List[str]       # raw file lines (no trailing newline)
    text: str              # full file text (for regex across the whole file)


Check = Callable[[CheckContext], List[Finding]]


# ---------------------------------------------------------------------------
# CWE-798 — Use of Hard-coded Credentials
# ---------------------------------------------------------------------------
# Patterns: assignment of an obvious secret to a variable name containing
# key/secret/token/password/api_key, or literal secret-shaped values.
_HARDCODED_RE = re.compile(
    r"(?i)(?:api[_-]?key|apikey|secret|token|password|passwd|pwd|access[_-]?key"
    r"|auth[_-]?token|client[_-]?secret|private[_-]?key)\s*[:=]\s*"
    r"(?:['\"](?=[A-Za-z0-9_\-]{16,}|sk-[A-Za-z0-9]|AKIA[0-9A-Z]{16})[^'\"]+['\"]"
    r"|['\"][A-Za-z0-9_\-]{24,}['\"])"
)


def check_hardcoded_credentials(ctx: CheckContext) -> List[Finding]:
    findings: List[Finding] = []
    for i, line in enumerate(ctx.lines, start=1):
        m = _HARDCODED_RE.search(line)
        if not m:
            continue
        # Ignore obvious placeholders / env-var reads / empty strings.
        val = m.group(0)
        if "getenv" in line or "os.environ" in line or "os.getenv" in line:
            continue
        if "your-" in val.lower() or "xxxxx" in val.lower() or "<" in val:
            continue
        findings.append(Finding(
            cwe="CWE-798",
            title="Hard-coded credential / key in source",
            severity=Severity.CRITICAL,
            file=ctx.rel_path,
            line=i,
            snippet=line.strip()[:160],
            description=(
                "A credential-shaped value is assigned directly in source code. "
                "Hard-coded secrets are exposed to anyone with repo access and "
                "leak through VCS history."
            ),
            recommendation=(
                "Move the secret to an environment variable or a secrets manager "
                "and read it at runtime (e.g. os.getenv('EXPENSE_TRACKER_API_KEY')). "
                "Rotate the exposed value."
            ),
            confidence="high",
        ))
    return findings


# ---------------------------------------------------------------------------
# CWE-306 — Missing Authentication for Critical Function
# ---------------------------------------------------------------------------
# Heuristic: a route handler (FastAPI/Flask/Express) that is NOT gated by an
# auth dependency / decorator / middleware marker.
_AUTH_MARKERS = re.compile(
    r"(?i)(Depends\([^)]*auth|@\w*login_required|@\w*auth\w*|require_auth|"
    r"authenticate|verify_token|@jwt|@auth|X-API-Key|api_key|Authorization|"
    r"middleware|add_middleware)"
)
_ROUTE_DEFS = re.compile(
    r"(?ix)^\s*(?:@\w+\.\w+\(|\b(?:app|router|api|web|server)\.[A-Za-z]+\()",
)
_HTTP_METHODS = re.compile(r"\b(get|post|put|delete|patch|options)\s*\(")


def check_missing_auth_boundary(ctx: CheckContext) -> List[Finding]:
    findings: List[Finding] = []
    in_handler_block = False
    handler_start = 0
    for i, line in enumerate(ctx.lines, start=1):
        if _ROUTE_DEFS.search(line) and _HTTP_METHODS.search(line):
            in_handler_block = True
            handler_start = i
            # The decorator is on the PRECEDING lines; if no auth marker appears
            # in the decorator stack above, flag the route.
            above = "\n".join(ctx.lines[max(0, i - 4):i])
            if not _AUTH_MARKERS.search(above) and not _AUTH_MARKERS.search(line):
                findings.append(Finding(
                    cwe="CWE-306",
                    title="Route handler without an authentication boundary",
                    severity=Severity.HIGH,
                    file=ctx.rel_path,
                    line=i,
                    snippet=line.strip()[:160],
                    description=(
                        "An HTTP route handler is defined with no detectable "
                        "authentication dependency, decorator, or middleware "
                        "reference. Critical functions must enforce authZ."
                    ),
                    recommendation=(
                        "Attach an auth dependency/decorator (e.g. FastAPI "
                        "Depends(require_api_key)) or enforce it in a global "
                        "middleware so every /api/* route is gated."
                    ),
                    confidence="medium",
                ))
    return findings


# ---------------------------------------------------------------------------
# CWE-942 — Permissive Cross-domain Policy (wildcard CORS)
# ---------------------------------------------------------------------------
_WILDCARD_CORS_RE = re.compile(
    r"(?i)(?:allow_origins|origins|Access-Control-Allow-Origin)\s*[=:]?\s*"
    r"(?:\[\s*['\"]?\*\s*['\"]?\s*\]|['\"]\*\s*['\"]|\*\s*\))"
)


def check_wildcard_cors(ctx: CheckContext) -> List[Finding]:
    findings: List[Finding] = []
    if "cors" not in ctx.text.lower() and "*" not in ctx.text:
        return findings
    for i, line in enumerate(ctx.lines, start=1):
        if _WILDCARD_CORS_RE.search(line):
            findings.append(Finding(
                cwe="CWE-942",
                title="Wildcard CORS policy (cross-origin exposure)",
                severity=Severity.HIGH,
                file=ctx.rel_path,
                line=i,
                snippet=line.strip()[:160],
                description=(
                    "A wildcard ('*') CORS origin policy allows any website to "
                    "read responses cross-origin, enabling cross-site data theft "
                    "when paired with ambient credentials."
                ),
                recommendation=(
                    "Restrict allow_origins to an explicit trusted-origin list "
                    "(or empty for a same-origin SPA). Never combine '*' with "
                    "credentialed requests."
                ),
                confidence="high",
            ))
    return findings


ALL_CHECKS: List[Check] = [
    check_hardcoded_credentials,
    check_missing_auth_boundary,
    check_wildcard_cors,
]
