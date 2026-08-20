"""Configuration helpers for the Lead Tracker API.

Holds runtime configuration loaded from the environment, with safe defaults for
local development. Secrets should always come from the environment in production.
"""
import os

# SQLite database file (created on first run).
DB_PATH = os.getenv("LEAD_TRACKER_DB", "leads.db")

# API binding.
HOST = os.getenv("LEAD_TRACKER_HOST", "0.0.0.0")
PORT = int(os.getenv("LEAD_TRACKER_PORT", "8000"))

# --- CWE-798 (intentional review finding) -------------------------------------
# A hard-coded fallback API token. Enterprises frequently ship a "default" token
# like this in a config helper "just for local testing" and it leaks to prod.
FALLBACK_API_TOKEN = "lt_sandbox_DEMO_ONLY_0000000000000000abcdef"
# -----------------------------------------------------------------------------


def get_api_token() -> str:
    """Return the API token from the environment, falling back to the hard-coded default."""
    return os.getenv("LEAD_TRACKER_API_TOKEN", FALLBACK_API_TOKEN)
