"""Dependency-free local server for the real execution workflow companion page."""
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


def idle_state() -> dict:
    return {
        "run_status": "IDLE",
        "current_test": None,
        "workflow": [],
        "summary": {"total": 0, "passed": 0, "failed": 0, "broken": 0, "skipped": 0},
        "events": [],
    }


class WorkflowHandler(SimpleHTTPRequestHandler):
    state_file: Path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def do_GET(self) -> None:
        if urlparse(self.path).path == "/api/state":
            self.send_state()
            return
        if urlparse(self.path).path in {"/", "/index.html"}:
            self.path = "/live_execution.html"
        super().do_GET()

    def send_state(self) -> None:
        try:
            payload = json.loads(self.state_file.read_text(encoding="utf-8")) if self.state_file.exists() else idle_state()
        except (OSError, json.JSONDecodeError):
            payload = idle_state()
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local API test execution workflow.")
    parser.add_argument("--state-file", required=True, type=Path)
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()
    WorkflowHandler.state_file = args.state_file
    server = ThreadingHTTPServer(("127.0.0.1", args.port), WorkflowHandler)
    print(f"Live Test Execution: http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
