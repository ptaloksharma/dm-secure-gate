# DM SecureGate

A lightweight **static security baseline scanner** plus a **Next.js dashboard** for
visualizing results.

## Components

- **`cli/`** — the Python scanner engine (stdlib-only, no runtime deps).
  - Modular detection checks:
    - **CWE-798** — Use of Hard-coded Credentials / Keys
    - **CWE-306** — Missing Authentication for Critical Function
    - **CWE-942** — Permissive Cross-domain Policy (wildcard CORS)
  - Emits a **standardized JSON report** (`ScanReport`) with vulnerability
    metadata, severities, and file locations.
- **`web-ui/`** — Next.js 14 (App Router, TypeScript) dashboard.
  - `/api/report` runs the CLI engine on demand and returns the latest JSON.
  - The dashboard renders the **Security Grade**, **Critical/High counts**, and
    **interactive remediation recommendation cards**.

## Usage

### CLI

```bash
cd cli
python3 -m securegate <repo-path> -o report.json
# exit code 1 if Critical/High found (CI-gating friendly)
```

### Dashboard

```bash
cd cli && python3 -m securegate ../expense-tracker -o report.json   # generate a report
cd ../web-ui && npm install
SECUREGATE_TARGET=../expense-tracker npm run dev                    # http://localhost:3000
```

The dashboard fetches `/api/report` on load and on "Re-run scan", which re-executes
the scanner against the live source tree — so the metrics are always current.

## Validation

`python3 tests/test_checks.py` exercises each detection check against synthetic
fixtures (true/false positives). Scanning the hardened `expense-tracker` repo
yields Grade **A** (0 findings) once credentials, query-string keys, wildcard CORS,
and fail-closed auth are in place.
