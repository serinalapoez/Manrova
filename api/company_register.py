"""Register a new company tenant. POST {display_name?} -> {company_id, access_code}."""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from enterprise.tenancy.tenancy import register_company
from enterprise.guardrail.guardrail import screen_input, GuardrailViolation


class handler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw or b"{}")
            display_name = str(data.get("display_name", "")).strip()[:120]

            if display_name:
                try:
                    display_name = screen_input(display_name, field_name="display_name")
                except GuardrailViolation as e:
                    self._send_json({"error": str(e)}, status=400)
                    return

            company = register_company(display_name)
            self._send_json(company)
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": str(e)}, status=500)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
