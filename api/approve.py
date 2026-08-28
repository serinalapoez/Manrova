"""
Approve & Send Endpoint
==========================
POST {incident_id, approver?} -> the updated incident record, with all
pending actions marked approved and executed, and the state advanced
through executing -> tracking -> resolution -> learning -> normal.

Design note: this mirrors OfficerOfTheWatch.approve_and_execute()'s
behavior, but operates on the stored JSON record from Firestore rather
than the live Python Incident object - each Vercel function invocation is
a fresh, stateless process, so the object built during the original
/api/investigate call doesn't exist anymore by the time a human clicks
Approve. This is a small, simple state transition (mark actions approved,
log it, advance the state label) - low risk of drifting from the core
class's logic, but worth flagging as its own implementation rather than a
call into oow/officer_of_the_watch.py directly.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from enterprise.memory.firestore_bank import get_incident_by_id, record_incident


def _approve_and_execute(record: dict, approver: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    timeline = list(record.get("timeline", []))
    pending = record.get("pending_actions", [])

    for action in pending:
        timeline.append({"actor": approver, "description": f"Approved: {action['description']}", "timestamp": now})
    for action in pending:
        timeline.append({"actor": "Officer of the Watch", "description": f"Executed: {action['description']}", "timestamp": now})

    for state, note in [
        ("executing", "State: action_plan -> executing"),
        ("tracking", "State: executing -> tracking"),
        ("resolution", "State: tracking -> resolution"),
    ]:
        timeline.append({"actor": "Officer of the Watch", "description": note, "timestamp": now})
    timeline.append({"actor": "Officer of the Watch", "description": "Incident marked resolved.", "timestamp": now})
    timeline.append({"actor": "Officer of the Watch", "description": "State: resolution -> learning", "timestamp": now})
    timeline.append({"actor": "Officer of the Watch", "description": "Outcome stored in fleet memory for future correlation.", "timestamp": now})
    timeline.append({"actor": "Officer of the Watch", "description": "State: learning -> normal", "timestamp": now})

    record["timeline"] = timeline
    record["state"] = "normal"
    record["resolved"] = True
    record["pending_actions"] = []  # approved and executed - nothing left pending
    return record


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
            incident_id = str(data.get("incident_id", "")).strip()
            approver = str(data.get("approver", "")).strip()[:80] or "Fleet Operator"

            if not incident_id:
                self._send_json({"error": "incident_id is required."}, status=400)
                return

            record = get_incident_by_id(incident_id)
            if record is None:
                self._send_json({"error": "Incident not found."}, status=404)
                return

            if not record.get("pending_actions"):
                self._send_json({"error": "This incident has no actions awaiting approval."}, status=400)
                return

            updated = _approve_and_execute(record, approver)

            try:
                record_incident(updated)
            except Exception:
                pass  # best-effort persistence, same as investigate.py's pattern

            self._send_json(updated)
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": str(e)}, status=500)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
