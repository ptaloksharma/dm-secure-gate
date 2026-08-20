# DM SecureGate

A lightweight **static security baseline scanner** plus a **Next.js dashboard** for
visualizing results.

## Components

- **`cli/`** — the Python scanner engine (stdlib-only, no runtime deps).
  - Modular detection checks:
    - **CWE-798** — Use of Hard-coded Credentials / Keys
    - **CWE-306** — Missing Authentication for Critical Function
    - **CWE-942** — Permissive Cross-domain Policy (wildcard CORS)
    - **CWE-250 / CWE-749 / CWE-494** — Container hygiene (Dockerfile /
      docker-compose.yml): runs as root, exposed ports, unpinned `latest` tags,
      `privileged: true`
  - Emits a **standardized JSON report** (`ScanReport`) with vulnerability
    metadata, severities, and file locations.
- **`web-ui/`** — Next.js 14 (App Router, TypeScript) dashboard.
  - `/api/report` runs the CLI engine on demand and returns the latest JSON.
  - The dashboard renders the **Security Grade**, **Critical/High counts**, and
    **interactive remediation recommendation cards**.

## Installation & global command

Two options — pick either:

```bash
# A) pip-install (true global command on PATH):
pip install -e ./cli
dm-secure ./path/to/repo            # also aliased as `securegate`

# B) zero-install local wrapper (no pip needed):
./cli/bin/dm-secure ./path/to/repo
```

Both resolve the scanner package automatically and work from **any** working
directory.

## Usage

```bash
dm-secure <repo-path> -o report.json
# exit code 1 if Critical/High found (CI-gating friendly)
```

## Dashboard

```bash
cd cli && dm-secure ../expense-tracker -o report.json   # generate a report
cd ../web-ui && npm install
SECUREGATE_TARGET=../expense-tracker npm run dev         # http://localhost:3000
```

The dashboard fetches `/api/report` on load and on "Re-run scan", which re-executes
the scanner against the live source tree — so the metrics are always current.

## Validation

- `cd cli && python3 tests/test_checks.py` — unit tests for every detection check
  (true/false positives), including the container-hygiene rules.
- Full-stack integration: boot `web-ui` and render the real React components
  (grade badge, stat cards, remediation cards) against the live `/api/report`
  JSON (headless, no browser).

Reference results:
- Hardened `expense-tracker` repo → **Grade B** (2 Medium: CWE-250 no-`USER`
  Dockerfile, CWE-749 `8000:8000` exposed port). No Critical/High.
- Deliberate vulnerable fixture → **Grade F** (Critical CWE-798 + High
  CWE-942/CWE-250 + Medium CWE-494/CWE-749/CWE-250), detected identically by the
  CLI and the live API route.
