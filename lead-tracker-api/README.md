# Lead Tracker API (Enterprise Sandbox)

A deliberately realistic **Customer Lead Intake & CRM** microservice used to
exercise **DM SecureGate** (the `dm-secure-gate` scanner). It is a fully working
FastAPI app — not a stub — so the scanner is tested against real, runnable code.

## What it does
- `POST /api/leads` — accept a lead (`name`, `email`, `company`, `budget`, `source`),
  validate via Pydantic, persist to SQLite.
- `GET /api/leads` — list stored leads (optionally `?company=`).
- `GET /api/leads/{id}` — fetch one lead.
- `GET /api/leads/stats/summary` and `GET /api/admin/stats` — aggregate stats.
- `GET /health` — liveness.

## Run it
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m lead_tracker_api.main
# in another shell:
curl -X POST localhost:8000/api/leads -H 'content-type: application/json' \
  -d '{"name":"Ada Lovelace","email":"ada@analytical.io","company":"Analytical Engines","budget":25000}'
curl localhost:8000/api/leads
```

## Seeded findings (for the scanner demo)
This project intentionally contains real enterprise anti-patterns so DM SecureGate
has something to catch:

| Finding | CWE | Where |
|---------|-----|-------|
| Hard-coded fallback API token | **CWE-798** | `lead_tracker_api/config.py` (`FALLBACK_API_TOKEN`) |
| Unprotected admin stats endpoint | **CWE-306** | `lead_tracker_api/main.py` (`/api/admin/stats`) |
| Wildcard CORS policy | **CWE-942** | `lead_tracker_api/main.py` (`allow_origins=["*"]`) |
| Root container (no USER) | **CWE-250** | `Dockerfile` (no `USER` directive) |
| Unpinned `latest` base image | **CWE-494** | `Dockerfile` (`FROM python:latest`) |

> These are **intentional** and should be flagged by `dm-secure`. Do not deploy this
> service as-is.
