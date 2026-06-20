#!/usr/bin/env python3
"""
Local HTTP server that lets n8n trigger Pinterest pin generation.

Runs on http://127.0.0.1:8765 (localhost only, no external access).
POST /generate-pin with JSON body matching generate_pin.py CLI args, e.g.:

    {
      "slug": "japan-photo",
      "title": "JAPAN",
      "tagline": "A traveler's 8-section guide",
      "bullet1": "History & geography",
      "bullet2": "Politics & economy",
      "bullet3": "Society & culture",
      "bullet4": "Travel prep checklist",
      "cta": "Read the full profile →",
      "urlHint": "travelnow • countries/japan",
      "pexelsQuery": "Japan Kyoto temple sunrise"
    }

Returns 200 with {slug, exitCode, stdout, stderr} on success, 500 on script failure.

Start: python3 pin_server.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8765
REPO_ROOT = Path(__file__).resolve().parent
SCRIPT = REPO_ROOT / "generate_pin.py"


def build_args(payload: dict) -> list[str] | str:
    required = ["slug", "title", "tagline", "bullet1", "bullet2", "bullet3", "bullet4", "urlHint"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return f"missing required fields: {', '.join(missing)}"
    args = [
        sys.executable, str(SCRIPT),
        "--slug", payload["slug"],
        "--title", payload["title"],
        "--tagline", payload["tagline"],
        "--bullet1", payload["bullet1"],
        "--bullet2", payload["bullet2"],
        "--bullet3", payload["bullet3"],
        "--bullet4", payload["bullet4"],
        "--cta", payload.get("cta", "Read the full profile →"),
        "--url-hint", payload["urlHint"],
    ]
    if payload.get("photo"):
        args += ["--photo", payload["photo"]]
    elif payload.get("pexelsQuery"):
        args += ["--pexels-query", payload["pexelsQuery"]]
    else:
        return "need either 'photo' or 'pexelsQuery'"
    return args


class PinHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, body: dict) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"ok": True})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/generate-pin":
            self._send_json(404, {"error": "not found"})
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError as e:
            self._send_json(400, {"error": f"invalid JSON: {e}"})
            return

        args = build_args(payload)
        if isinstance(args, str):
            self._send_json(400, {"error": args})
            return

        result = subprocess.run(args, capture_output=True, text=True, cwd=str(REPO_ROOT))
        body = {
            "slug": payload["slug"],
            "exitCode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
        self._send_json(200 if result.returncode == 0 else 500, body)

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"[pin_server] {self.address_string()} - {fmt % args}\n")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), PinHandler)
    print(f"pin_server listening on http://{HOST}:{PORT}")
    print("POST /generate-pin with JSON body to render a pin")
    print("Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\npin_server stopped")
        server.server_close()


if __name__ == "__main__":
    main()
