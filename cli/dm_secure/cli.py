"""Command-line entrypoint for the DM SecureGate scanner.

Two modes:
  * default / ``scan`` — run the static scanner against a repo and emit a report
    (JSON or executive Markdown).
  * ``ui`` — launch the bundled Next.js dashboard locally (served by Python's
    stdlib HTTP server, with a live ``/api/report`` endpoint that re-runs the
    scanner on demand).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from .checks import ALL_CHECKS
from .report import ScanReport, build_report
from .scanner import scan_path


def run_scan(target: str) -> ScanReport:
    target = os.path.abspath(target)
    if not os.path.isdir(target):
        raise SystemExit(f"error: target is not a directory: {target}")
    files_scanned, findings = scan_path(target, checks=ALL_CHECKS)
    return build_report(
        target=target,
        files_scanned=files_scanned,
        checks_run=[c.__name__ for c in ALL_CHECKS],
        findings=findings,
    )


# ---------------------------------------------------------------------------
# `ui` subcommand — serve the bundled dashboard + live /api/report
# ---------------------------------------------------------------------------
def _ui_target_default() -> str:
    # The dashboard scans whatever repo the user is standing in when they launch it.
    return os.path.abspath(os.getcwd())


def run_ui(port: int, target: str, host: str = "127.0.0.1") -> int:
    """Launch the bundled Next.js dashboard.

    The wheel ships the production build as a Next "standalone" server under
    ``dm_secure/webui/server.js``. We run it with Node (already required for the
    API routes) and inject the CLI location + scan target via env vars so the
    dashboard's /api/* endpoints (report + Strix) can talk to the local engine.

    Falls back to a dependency-free Python static server (serving /api/report only)
    if the standalone server or Node is unavailable.
    """
    import shutil
    import subprocess

    webui_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "dm_secure", "webui")
    server_js = os.path.join(webui_dir, "server.js")
    scan_target = os.path.abspath(target)
    # __file__ = <repo>/cli/dm_secure/cli.py  ->  dirname x2 = <repo>/cli
    cli_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    node = shutil.which("node")
    if node and os.path.isfile(server_js):
        env = dict(os.environ)
        env["PORT"] = str(port)
        env["HOSTNAME"] = host
        env["SECUREGATE_CLI_DIR"] = cli_dir
        env["SECUREGATE_TARGET"] = scan_target
        url = f"http://{host}:{port}/"
        print(f"DM SecureGate dashboard running at {url}")
        print(f"  scanning target: {scan_target}")
        print(f"  Strix engine: {_strix_path() or 'not detected'}")
        print("  press Ctrl+C to stop.")
        try:
            subprocess.run([node, server_js], cwd=webui_dir, env=env)
        except KeyboardInterrupt:
            print("\nstopped.")
        return 0

    # --- Fallback: minimal Python server (no Node / no standalone build) ---
    print("warning: Node or the bundled Next server was not found; serving a "
          "static fallback (Strix endpoints unavailable).", file=sys.stderr)
    return _run_ui_fallback(webui_dir, scan_target, host, port)


def _strix_path() -> str | None:
    import shutil
    import stat
    candidates = [
        os.path.join(os.path.expanduser("~"), "strix-venv", "bin", "strix"),
        "/home/opc/strix-venv/bin/strix",
        "/home/opc/.strix/bin/strix",
    ]
    for c in candidates:
        try:
            if os.path.isfile(c) and (os.stat(c).st_mode & stat.S_IXUSR):
                return c
        except OSError:
            continue
    return shutil.which("strix")


def _run_ui_fallback(webui_dir: str, scan_target: str, host: str, port: int) -> int:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import urllib.parse

    if not os.path.isdir(webui_dir):
        print(f"error: bundled dashboard not found at {webui_dir}", file=sys.stderr)
        return 1

    def serve_report():
        try:
            report = run_scan(scan_target)
            return (200, "application/json", report.to_json().encode("utf-8"))
        except Exception as e:  # pragma: no cover - defensive
            return (500, "application/json",
                    json.dumps({"error": "scan failed", "detail": str(e)}).encode("utf-8"))

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, ctype, body):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/api/report" or parsed.path.startswith("/api/report"):
                code, ctype, body = serve_report()
                self._send(code, ctype, body)
                return
            rel = parsed.path.lstrip("/")
            if rel == "" or rel.endswith("/"):
                rel = "index.html"
            rel = rel.replace("\\", "/")
            if ".." in rel.split("/"):
                self._send(403, "text/plain", b"forbidden")
                return
            fpath = os.path.join(webui_dir, rel)
            if not os.path.isfile(fpath):
                fpath = os.path.join(webui_dir, "index.html")
                ctype = "text/html"
            else:
                ext = os.path.splitext(fpath)[1].lower()
                ctype = {
                    ".html": "text/html", ".js": "text/javascript",
                    ".css": "text/css", ".json": "application/json",
                    ".svg": "image/svg+xml", ".png": "image/png",
                    ".ico": "image/x-icon", ".txt": "text/plain",
                    ".woff2": "font/woff2", ".woff": "font/woff",
                }.get(ext, "application/octet-stream")
            try:
                with open(fpath, "rb") as fh:
                    self._send(200, ctype, fh.read())
            except OSError:
                self._send(404, "text/plain", b"not found")

        def log_message(self, *args):  # type: ignore[override]
            pass

    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"DM SecureGate dashboard running at {url}")
    print(f"  scanning target: {scan_target}")
    print("  press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dm-secure",
        description="DM SecureGate — static security baseline scanner "
                    "(CWE-798, CWE-306, CWE-942, CWE-250/749/494) by DM Digital Solutions B.V.",
    )
    parser.add_argument("--version", action="version",
                        version="dm-secure 0.1.0 (DM SecureGate — DM Digital Solutions B.V.)")
    sub = parser.add_subparsers(dest="command")

    scan = sub.add_parser("scan", help="scan a repo and emit a report (default)")
    scan.add_argument("target", nargs="?", default=".", help="repo path to scan")
    scan.add_argument("-o", "--output", help="write report to this path")
    scan.add_argument("--format", choices=["json", "md"], default="json",
                      help="report format: json (default) or md (executive Markdown)")
    scan.add_argument("--client", default="Client",
                      help="client name shown in the executive Markdown report")
    scan.add_argument("--quiet", action="store_true", help="suppress console summary")

    ui = sub.add_parser("ui", help="launch the local compliance dashboard")
    ui.add_argument("-p", "--port", type=int, default=8080, help="port to bind (default 8080)")
    ui.add_argument("--host", default="127.0.0.1", help="host to bind (default 127.0.0.1)")
    ui.add_argument("--target", default=None, help="repo the dashboard should scan")
    return parser


def main(argv: List[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Default-subcommand pattern: `dm-secure ./repo` => `dm-secure scan ./repo`.
    if argv and argv[0] not in ("scan", "ui") and not argv[0].startswith("-"):
        argv.insert(0, "scan")

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        report = run_scan(args.target)
        if args.format == "md":
            rendered = report.to_markdown(client=args.client)
        else:
            rendered = report.to_json()
        if args.output:
            out = os.path.abspath(args.output)
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(rendered)
            if not args.quiet:
                print(f"Report written to {out}")
        if not args.quiet:
            print(rendered)
        else:
            print(
                f"grade={report.grade} critical={report.counts.get('Critical',0)} "
                f"high={report.counts.get('High',0)} "
                f"medium={report.counts.get('Medium',0)} "
                f"findings={len(report.findings)}",
                file=sys.stderr,
            )
        return 1 if (report.counts.get("Critical", 0) or report.counts.get("High", 0)) else 0

    if args.command == "ui":
        target = args.target or _ui_target_default()
        return run_ui(port=args.port, target=target, host=args.host)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
