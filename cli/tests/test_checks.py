"""Self-contained unit tests for the detection checks (no external deps)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from securegate.checks import check_hardcoded_credentials, check_wildcard_cors
from securegate.checks import check_missing_auth_boundary, CheckContext


def _ctx(rel, text):
    return CheckContext(repo_root="/tmp", rel_path=rel, lines=text.splitlines(), text=text)


def test_hardcoded_detected():
    c = _ctx("app/config.py", 'API_KEY = "abcdef1234567890abcdef1234"\n')
    f = check_hardcoded_credentials(c)
    assert len(f) == 1 and f[0].cwe == "CWE-798"


def test_hardcoded_env_not_flagged():
    c = _ctx("app/config.py", 'API_KEY = os.getenv("EXPENSE_TRACKER_API_KEY")\n')
    assert check_hardcoded_credentials(c) == []


def test_wildcard_cors_detected():
    c = _ctx("app/main.py", 'app.add_middleware(CORSMiddleware, allow_origins=["*"])\n')
    f = check_wildcard_cors(c)
    assert len(f) == 1 and f[0].cwe == "CWE-942"


def test_missing_auth_flagged():
    c = _ctx("app/routes.py", '@app.get("/api/expenses")\ndef list_expenses():\n    return []\n')
    f = check_missing_auth_boundary(c)
    assert len(f) == 1 and f[0].cwe == "CWE-306"


def test_auth_present_not_flagged():
    c = _ctx("app/routes.py",
             '@app.get("/api/expenses", dependencies=[Depends(require_api_key)])\n'
             'def list_expenses():\n    return []\n')
    assert check_missing_auth_boundary(c) == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("ALL TESTS PASSED")
