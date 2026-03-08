#!/usr/bin/env python3
import hashlib
import hmac
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer


SECRET = os.environ.get("WEBHOOK_SECRET", "")
TARGET_PATH = "/oil-webhook"
BRANCH_REF = "refs/heads/main"
MAX_PAYLOAD_SIZE = 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != TARGET_PATH:
            self._send(404, b"Not Found")
            return

        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > MAX_PAYLOAD_SIZE:
            self._send(413, b"Payload too large")
            return

        body = self.rfile.read(length)
        signature = self.headers.get("X-Hub-Signature-256", "")
        expected = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not SECRET or not signature or not hmac.compare_digest(signature, expected):
            self._send(401, b"Invalid signature")
            return

        event = self.headers.get("X-GitHub-Event", "")
        if event == "ping":
            self._send(200, b"pong")
            return

        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(400, b"Invalid JSON")
            return

        if event == "push" and payload.get("ref") == BRANCH_REF:
            proc = subprocess.run(  # noqa: S603
                ["/opt/oil-monitor/deploy/deploy.sh"],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                self._send(500, b"deploy failed")
                return
            self._send(200, b"deploy success")
            return

        self._send(202, b"ignored")

    def log_message(self, fmt: str, *args) -> None:
        return


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 9002), Handler).serve_forever()

