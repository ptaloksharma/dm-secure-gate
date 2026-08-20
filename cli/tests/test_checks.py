"""Self-contained unit tests for the detection checks (no external deps)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from securegate.checks import (
    check_hardcoded_credentials, check_wildcard_cors,
    check_missing_auth_boundary, check_container_hygiene, CheckContext,
)


def _ctx(rel, text):
    return CheckContext(repo_root="/tmp", rel_path=rel, lines=text.splitlines(), text=text)


def test_hardcoded_detected():
    c = _ctx("app/config.py", 'API_KEY = "abcdef1234567890abcdef1234"\n')
    assert len(check_hardcoded_credentials(c)) == 1


def test_hardcoded_env_not_flagged():
    c = _ctx("app/config.py", 'API_KEY = os.getenv("EXPENSE_TRACKER_API_KEY")\n')
    assert check_hardcoded_credentials(c) == []


def test_wildcard_cors_detected():
    c = _ctx("app/main.py", 'app.add_middleware(CORSMiddleware, allow_origins=["*"])\n')
    assert len(check_wildcard_cors(c)) == 1


def test_missing_auth_flagged():
    c = _ctx("app/routes.py", '@app.get("/api/expenses")\ndef list_expenses():\n    return []\n')
    assert len(check_missing_auth_boundary(c)) == 1


def test_auth_present_not_flagged():
    c = _ctx("app/routes.py",
             '@app.get("/api/expenses", dependencies=[Depends(require_api_key)])\n'
             'def list_expenses():\n    return []\n')
    assert check_missing_auth_boundary(c) == []


def test_container_root_user():
    c = _ctx("Dockerfile", "FROM python:3.11-slim\nUSER root\nCMD [\"uvicorn\"]\n")
    f = check_container_hygiene(c)
    assert any(x.cwe == "CWE-250" and "root USER" in x.title for x in f)


def test_container_no_user():
    c = _ctx("Dockerfile", "FROM python:3.11-slim\nCMD [\"uvicorn\"]\n")
    f = check_container_hygiene(c)
    assert any(x.cwe == "CWE-250" and "no USER" in x.title for x in f)


def test_container_latest_tag():
    c = _ctx("Dockerfile", "FROM node:latest\nCMD [\"npm\",\"start\"]\n")
    f = check_container_hygiene(c)
    assert any(x.cwe == "CWE-494" for x in f)


def test_container_pinned_tag_ok():
    c = _ctx("Dockerfile", "FROM python:3.11-slim\nCMD [\"uvicorn\"]\n")
    assert all(x.cwe != "CWE-494" for x in check_container_hygiene(c))


def test_compose_privileged():
    c = _ctx("docker-compose.yml",
             "services:\n  api:\n    image: app\n    privileged: true\n")
    assert any(x.cwe == "CWE-250" and "Privileged" in x.title for x in check_container_hygiene(c))


def test_compose_exposed_port():
    c = _ctx("docker-compose.yml",
             "services:\n  api:\n    image: app\n    ports:\n      - \"8000:8000\"\n")
    assert any(x.cwe == "CWE-749" for x in check_container_hygiene(c))


def test_compose_loopback_ok():
    c = _ctx("docker-compose.yml",
             "services:\n  api:\n    image: app\n    ports:\n      - \"127.0.0.1:8080:8080\"\n")
    assert all(x.cwe != "CWE-749" for x in check_container_hygiene(c))


def test_non_container_file_ignored():
    c = _ctx("README.md", "FROM node:latest\nprivileged: true\n- \"8000:8000\"\n")
    assert check_container_hygiene(c) == []


def test_executive_markdown_render():
    from securegate.report import build_report, Finding, Severity
    f = Finding(cwe="CWE-798", title="Hard-coded credential",
                severity=Severity.CRITICAL, file="app/secret.py", line=3,
                description="desc", recommendation="rotate it")
    rep = build_report(target="/repo", files_scanned=10,
                       checks_run=["check_hardcoded_credentials"], findings=[f])
    md = rep.to_markdown(client="Acme Corp")
    assert "Acme Corp" in md
    assert "**F**" in md
    assert "CWE-798" in md
    assert "Critical" in md
    assert "DM Digital Solutions B.V." in md


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
    print("ALL TESTS PASSED")
