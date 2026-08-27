"""
Manrova Live Demo - Serverless Investigation Endpoint
========================================================
Vercel Python function. Reuses the exact shared core (core/, agents/,
oow/, data/demo/) - no duplicated business logic. Makes exactly ONE
Gemini call to narrate the already-computed structured result, instead of
the full multi-agent delegation chain (8-10+ calls) used in the ADK/Strands
builds - this keeps the public demo fast, cheap, and resistant to free-tier
rate limits.

If the Gemini call fails for any reason (quota, network, deprecated model),
falls back to a clean auto-generated narrative from the structured data so
the live site never shows a judge a raw error.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from oow.officer_of_the_watch import OfficerOfTheWatch
from data.demo.fleet_data import (
    HERO_TELEMETRY, CREW_RECORD, COMPLIANCE_RECORD, NEAR_MISS_REPORTS,
)

FALLBACK_MODELS = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.7-flash", "gemini-flash-latest"]


def _build_prompt(incident) -> str:
    r = incident.risk
    lines = [
        "You are the Officer of the Watch for Manrova, an autonomous maritime fleet operations system.",
        "Write a short, clear incident narrative (3-4 sentences, plain prose, no markdown headers) "
        "for a fleet operations officer, based ONLY on these already-computed findings - do not "
        "invent any numbers not shown here:",
        f"Vessel: {incident.vessel_id}",
        f"Navigation risk: {r.nav_risk.value}",
        f"Crew readiness risk: {r.crew_risk.value}",
        f"Fleet pattern risk: {r.historical_similarity.value}",
        f"Compliance risk: {r.compliance_exposure.value}",
        f"Overall severity: {r.overall_severity.value} (confidence {r.confidence:.0%})",
        "Reasons: " + "; ".join(r.explanation),
        f"Pending actions requiring human approval: "
        + ", ".join(a.description for a in incident.actions if a.requires_approval),
        "End by clearly stating that no external notification will be sent without human approval.",
    ]
    return "\n".join(lines)


def _fallback_narrative(incident) -> str:
    r = incident.risk
    pending = [a.description for a in incident.actions if a.requires_approval]
    parts = [
        f"{incident.vessel_id} has been flagged at {r.overall_severity.value.upper()} severity "
        f"with {r.confidence:.0%} confidence.",
        " ".join(r.explanation) + ".",
    ]
    if pending:
        parts.append(
            "The following actions are prepared and awaiting human approval before anything is "
            "sent: " + ", ".join(pending) + "."
        )
    else:
        parts.append("No external notification is required - monitoring continues.")
    return " ".join(parts)


def _narrate_with_gemini(incident) -> tuple[str, bool]:
    """Returns (narrative_text, used_ai). Falls back cleanly on any failure."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return _fallback_narrative(incident), False

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(incident)
        last_error = None
        for model in FALLBACK_MODELS:
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                text = getattr(response, "text", None)
                if text:
                    return text.strip(), True
            except Exception as e:  # noqa: BLE001 - any provider error, try next model
                last_error = e
                continue
        return _fallback_narrative(incident), False
    except Exception:
        return _fallback_narrative(incident), False


def _run_investigation() -> dict:
    oow = OfficerOfTheWatch()
    fleet_context = {
        "crew_record": CREW_RECORD,
        "near_miss_reports": NEAR_MISS_REPORTS,
        "compliance_record": COMPLIANCE_RECORD,
    }
    incident = oow.handle_telemetry(HERO_TELEMETRY, fleet_context)

    if incident is None:
        return {"incident": None, "message": "No anomaly detected - fleet remains in normal operations."}

    narrative, used_ai = _narrate_with_gemini(incident)

    return {
        "incident_id": incident.incident_id,
        "vessel_id": incident.vessel_id,
        "state": incident.state.value,
        "narrative": narrative,
        "narrative_source": "gemini" if used_ai else "auto-generated",
        "risk": {
            "nav": incident.risk.nav_risk.value,
            "crew": incident.risk.crew_risk.value,
            "pattern": incident.risk.historical_similarity.value,
            "compliance": incident.risk.compliance_exposure.value,
            "overall": incident.risk.overall_severity.value,
            "confidence": incident.risk.confidence,
            "explanation": incident.risk.explanation,
        },
        "pending_actions": [
            {"description": a.description}
            for a in incident.actions if a.requires_approval
        ],
        "timeline": [
            {"actor": t.actor, "description": t.description, "timestamp": t.timestamp.isoformat()}
            for t in incident.timeline
        ],
    }


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
            result = _run_investigation()
            self._send_json(result)
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": str(e)}, status=500)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
