"""Lead Tracker API — Customer Lead Intake & CRM microservice.

A small but fully functional FastAPI service: it validates inbound lead JSON with
Pydantic, persists to SQLite, and exposes endpoints to create, fetch, and list leads
plus an aggregate statistics view.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from . import db
from .config import DB_PATH
from .models import Lead, LeadCreate, LeadStats

app = FastAPI(title="Lead Tracker API", version="1.0.0")

# --- CWE-942 (intentional review finding) -------------------------------------
# Wildcard CORS lets any origin read responses cross-origin. Common copy/paste
# shortcut that exposes the API to any website a victim visits.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -----------------------------------------------------------------------------


@app.post("/api/leads", response_model=Lead, status_code=201)
def create_lead(payload: LeadCreate) -> Lead:
    """Accept an incoming lead submission, validate, and persist it."""
    return db.insert_lead(DB_PATH, payload)


@app.get("/api/leads", response_model=List[Lead])
def list_leads(limit: int = 100, company: Optional[str] = None) -> List[Lead]:
    """List stored leads, most recent first, optionally filtered by company."""
    return db.list_leads(DB_PATH, limit=limit, company=company)


@app.get("/api/leads/{lead_id}", response_model=Lead)
def get_lead(lead_id: int) -> Lead:
    lead = db.get_lead(DB_PATH, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found")
    return lead


@app.get("/api/leads/stats/summary", response_model=LeadStats)
def lead_summary() -> LeadStats:
    """Lightweight aggregate summary (budget totals)."""
    leads = db.list_leads(DB_PATH, limit=10_000)
    total = len(leads)
    high_value = sum(1 for l in leads if (l.budget or 0) >= 10_000)
    avg = sum(l.budget or 0 for l in leads) / total if total else 0.0
    return LeadStats(total_leads=total, high_value_leads=high_value, avg_budget=round(avg, 2))


# --- CWE-306 (intentional review finding) -------------------------------------
# Administrative stats endpoint with NO authentication dependency. Anyone who can
# reach the service can pull aggregate pipeline intelligence.
@app.get("/api/admin/stats")
def admin_stats() -> dict:
    """Sensitive operational stats — should require admin auth, but does not."""
    leads = db.list_leads(DB_PATH, limit=10_000)
    total = len(leads)
    high_value = sum(1 for l in leads if (l.budget or 0) >= 10_000)
    return {
        "total_leads": total,
        "high_value_leads": high_value,
        "avg_budget": round(sum(l.budget or 0 for l in leads) / total, 2) if total else 0.0,
        "companies": sorted({l.company for l in leads if l.company}),
    }
# -----------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "leads": db.count_leads(DB_PATH)}


if __name__ == "__main__":
    import uvicorn

    from .config import HOST, PORT

    uvicorn.run(app, host=HOST, port=PORT)
