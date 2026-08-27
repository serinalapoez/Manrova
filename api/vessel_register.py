"""Register a vessel under a company. POST {company_id, name, vessel_class?}
-> vessel record. Vessel name can be a real name or an internal alias -
Manrova never requires disclosing a real hull identity."""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from enterprise.tenancy.tenancy import register_vessel, lookup_company
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

            company_id = str(data.get("company_id", "")).strip()
            access_code = str(data.get("access_code", "")).strip().upper()
            name = str(data.get("name", "")).strip()[:120]
            vessel_class = str(data.get("vessel_class", "unspecified")).strip()[:60]

            if not company_id or not name:
                self._send_json({"error": "company_id and name are required."}, status=400)
                return

            company = lookup_company(access_code)
            if company is None or company["company_id"] != company_id:
                self._send_json({"error": "Invalid access code for this company."}, status=403)
                return

            try:
                name = screen_input(name, field_name="vessel_name")
            except GuardrailViolation as e:
                self._send_json({"error": str(e)}, status=400)
                return

            vessel = register_vessel(company_id, name, vessel_class or "unspecified")
            self._send_json(vessel)
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": str(e)}, status=500)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
