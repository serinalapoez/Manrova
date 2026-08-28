"""Look up a company tenant by access code. POST {access_code} ->
{company, vessels}. Returns 404-style error dict if not found."""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from enterprise.tenancy.tenancy import lookup_company, list_vessels
from enterprise.memory.firestore_bank import get_recent_incidents


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
            access_code = str(data.get("access_code", "")).strip().upper()

            company = lookup_company(access_code)
            if company is None:
                self._send_json({"error": "Access code not found."}, status=404)
                return

            vessels = list_vessels(company["company_id"])
            for vessel in vessels:
                try:
                    vessel["recent_incidents"] = get_recent_incidents(vessel["name"], limit=3)
                except Exception:
                    vessel["recent_incidents"] = []  # memory bank read is best-effort, never blocks lookup
            self._send_json({"company": company, "vessels": vessels})
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": str(e)}, status=500)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
