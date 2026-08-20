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


# ---------------------------------------------------------------------------
# CWE-250 / CWE-749 — Container hygiene (Dockerfile + docker-compose.yml)
# ---------------------------------------------------------------------------
# Anti-patterns we flag:
#   * running as root (USER root, or no USER at all in a Dockerfile)
#   * publishing ports to 0.0.0.0 / all interfaces (CWE-749 exposed surface)
#   * unpinned `latest` image tags (non-reproducible, silent drift)
#   * `privileged: true` containers (full host access)
_CONTAINER_FILE_RE = re.compile(r"(?i)(Dockerfile[^/]*|.*docker-compose[^/]*\.(ya?ml|json))$")
_ROOT_USER_RE = re.compile(r"(?im)^\s*USER\s+root\b")
_USER_SET_RE = re.compile(r"(?im)^\s*USER\s+\S+")
_PRIVILEGED_RE = re.compile(r"(?im)^\s*privileged\s*:\s*true\b")
_PORT_PUBLISH_RE = re.compile(
    r"(?i)^\s*-\s*[\"']?\d{1,5}:[\"']?\d{1,5}\b|^\s*ports\s*:|^\s*-\s*[\"']?[\"']?\d{1,5}:"
)
_LATEST_TAG_RE = re.compile(r"(?i)(FROM\s+\S+|:\s*\S*)\blatest\b")


def check_container_hygiene(ctx: CheckContext) -> List[Finding]:
    findings: List[Finding] = []
    if not _CONTAINER_FILE_RE.search(ctx.rel_path):
        return findings
    text = ctx.text
    is_dockerfile = ctx.rel_path.lower().startswith("dockerfile") or ctx.rel_path.lower().endswith("/dockerfile")

    # --- Dockerfile-specific: root user / no USER ---
    if is_dockerfile:
        if _ROOT_USER_RE.search(text):
            findings.append(Finding(
                cwe="CWE-250",
                title="Container runs as root USER",
                severity=Severity.HIGH,
                file=ctx.rel_path,
                snippet="USER root",
                description=(
                    "The image explicitly switches to the root user. A compromise "
                    "of the app then yields root inside the container, easing "
                    "break-out and host-impact escalation."
                ),
                recommendation="Add a non-root USER (e.g. create a dedicated user and `USER appuser`).",
                confidence="high",
            ))
        elif not _USER_SET_RE.search(text):
            findings.append(Finding(
                cwe="CWE-250",
                title="Container runs as root (no USER directive)",
                severity=Severity.MEDIUM,
                file=ctx.rel_path,
                snippet="(no USER directive)",
                description=(
                    "Dockerfiles default to root when no USER is set. Drop "
                    "privileges by declaring a non-root USER before the CMD/ENTRYPOINT."
                ),
                recommendation="Add `USER <non-root>` (create the user earlier in the build).",
                confidence="high",
            ))

    # --- unpinned `latest` base image ---
    for i, line in enumerate(ctx.lines, start=1):
        if _LATEST_TAG_RE.search(line) and "FROM" in line:
            findings.append(Finding(
                cwe="CWE-494",
                title="Unpinned 'latest' image tag",
                severity=Severity.MEDIUM,
                file=ctx.rel_path,
                line=i,
                snippet=line.strip()[:160],
                description=(
                    "A `latest` base image is mutable and non-reproducible; the "
                    "running image can change silently between builds, undermining "
                    "supply-chain integrity."
                ),
                recommendation="Pin the base image to an explicit version/digest (e.g. python:3.11-slim).",
                confidence="high",
            ))
            break  # one finding per file for the latest-tag issue

    # --- docker-compose: privileged + exposed ports ---
    if "compose" in ctx.rel_path.lower():
        for i, line in enumerate(ctx.lines, start=1):
            if _PRIVILEGED_RE.search(line):
                findings.append(Finding(
                    cwe="CWE-250",
                    title="Privileged container in compose",
                    severity=Severity.HIGH,
                    file=ctx.rel_path,
                    line=i,
                    snippet=line.strip()[:160],
                    description=(
                        "privileged: true grants the container near-full access to "
                        "the host kernel, equivalent to root on the host."
                    ),
                    recommendation="Remove `privileged: true`; grant only the specific capabilities required.",
                    confidence="high",
                ))
        # exposed ports: a mapping published to all interfaces
        if re.search(r"(?i)ports\s*:\s*\n(\s*-\s*[\"']?\d)", text) or "0.0.0.0" in text:
            # find the first offending publish line
            for i, line in enumerate(ctx.lines, start=1):
                if re.match(r"(?i)^\s*-\s*[\"']?\d{1,5}:", line) or "0.0.0.0" in line:
                    findings.append(Finding(
                        cwe="CWE-749",
                        title="Container port exposed to all interfaces",
                        severity=Severity.MEDIUM,
                        file=ctx.rel_path,
                        line=i,
                        snippet=line.strip()[:160],
                        description=(
                            "A published port mapping binds the service to all host "
                            "interfaces (0.0.0.0), widening the network attack surface."
                        ),
                        recommendation=(
                            "Bind to 127.0.0.1 (e.g. '127.0.0.1:8080:8080') or rely on "
                            "an internal docker network / reverse proxy."
                        ),
                        confidence="medium",
                    ))
                    break

    return findings


ALL_CHECKS: List[Check] = [
    check_hardcoded_credentials,
    check_missing_auth_boundary,
    check_wildcard_cors,
    check_container_hygiene,
]
