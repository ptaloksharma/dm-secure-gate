# DM SecureGate

### Static Security Baseline Scanner & Executive Compliance Dashboard
**by DM Digital Solutions B.V.** — *Smart Systems. Inclusive Solutions.*

DM SecureGate is a lightweight, dependency-free static analysis tool that scans a
code repository for common security anti-patterns and produces a standardized,
board-ready compliance report — both as machine-readable JSON (for the live
dashboard) and as an Executive Markdown brief (for client architecture reviews).

It ships with a **Next.js dashboard** that renders the Security Grade, Critical/High
counts, and interactive remediation cards directly from the scanner's live output.

---

## What it checks (CWE coverage)

| Check | CWE | What it catches |
|-------|-----|-----------------|
| Hard-coded credentials / keys | **CWE-798** | Secrets assigned directly in source (API keys, tokens, passwords) |
| Missing authentication boundary | **CWE-306** | Route handlers without an auth dependency / decorator / middleware |
| Wildcard CORS exposure | **CWE-942** | `allow_origins = ["*"]` cross-origin policy |
| Container hygiene | **CWE-250 / CWE-749 / CWE-494** | Runs as `root` (no `USER`), ports exposed to all interfaces, unpinned `latest` image tags, `privileged: true` |

Scans are **dependency-free** (Python standard library only) and skip vendored /
build directories (`.venv`, `node_modules`, `site-packages`, `.next`, …) so the
engine stays portable and fast.

---

## Installation — run the CLI globally

Two options; either works from **any** working directory.

### A) Pip-install (recommended — a true global command)

```bash
pip install -e ./cli
dm-secure ./path/to/repo            # also aliased as `securegate`
```

### B) Zero-install local wrapper (no pip needed)

```bash
./cli/bin/dm-secure ./path/to/repo
```

Both resolve the scanner package automatically and work regardless of your current
directory.

**Quick scan:**

```bash
dm-secure /path/to/repo
dm-secure /path/to/repo -o report.json          # write JSON to a file
dm-secure /path/to/repo --format md --client "Acme Corp" -o report.md   # executive brief
# exit code is 1 if Critical/High findings exist (CI-gating friendly)
```

---

## Security Grades (A–F)

The Security Grade is a single-letter roll-up of the finding severities:

| Grade | Meaning | Condition |
|-------|---------|-----------|
| **A** | Baseline secure | No Critical / High / Medium findings |
| **B** | Minor hardening needed | Medium findings only (no Critical/High) |
| **C** | Weak — fix before release | 1–2 High-severity findings |
| **D** | Poor — blockers present | 3+ High-severity findings |
| **E** | *(reserved)* | Reserved for future severity tiers |
| **F** | **Failed** — unacceptable | Any Critical (e.g. hard-coded credentials) |

> **Interpretation for reviewers:** treat **C or below** as a release blocker.
> **F** means a credential or privileged-access violation was detected and the
> repository must be remediated before any client hand-over.

---

## Executive Compliance Report

For client architecture reviews, generate a board-ready Markdown brief:

```bash
dm-secure /path/to/repo --format md --client "Client Name" -o COMPLIANCE_REPORT.md
```

This produces a document containing:

- **Prepared-for / target / scan-date / scanner version** header
- **Executive Summary** with the Security Grade, files scanned, findings by severity
- A **Findings-by-Severity** table
- **Detailed Findings**, each with severity, location (`file:line`), description,
  and an actionable recommendation

Sample reports live in [`docs/`](./docs): a **Grade B** internal audit and a
**Grade F** vulnerable-reference scan. A machine-readable [`REPORT_sample.json`](./docs/REPORT_sample.json)
is included for dashboard / pipeline integration.

---

## Dashboard (web-ui/)

```bash
cd cli && dm-secure ../expense-tracker -o report.json     # generate a report
cd ../web-ui && npm install
SECUREGATE_TARGET=../expense-tracker npm run dev           # http://localhost:3000
```

The dashboard fetches `/api/report` on load and on **"Re-run scan"**, re-executing
the scanner against the live source tree — so the grade, counts, and remediation
cards always reflect current code. If the Python engine is unavailable, it falls
back to the committed sample so the UI still renders.

---

## Verification

- `cd cli && python3 tests/test_checks.py` — unit tests for every detection check
  (true/false positives) plus the executive Markdown renderer.
- Headless full-stack: boot `web-ui` and server-render the real React components
  (grade badge, stat cards, remediation cards) against the live `/api/report` JSON.

### Reference results
- Hardened `expense-tracker` repo → **Grade B** (2 Medium: CWE-250 root container,
  CWE-749 exposed `8000:8000`). No Critical/High.
- Deliberate vulnerable fixture → **Grade F** (Critical CWE-798 + High CWE-942/CWE-250
  + Medium CWE-494/CWE-749/CWE-250), detected identically by the CLI and the live API.

---

*DM SecureGate — a product of **DM Digital Solutions B.V.**
"Smart Systems. Inclusive Solutions."*
