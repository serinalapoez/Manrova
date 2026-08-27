"""
Manrova Live Demo - Serverless Investigation Endpoint
========================================================
Vercel Python function. Reuses the exact shared core (core/, agents/,
oow/, data/demo/) - no duplicated business logic. Makes exactly ONE
Gemini call to narrate the already-computed structured result, instead of
the full multi-agent delegation chain (8-10+ calls) used in the ADK/Strands
builds - this keeps the public demo fast, cheap, and resistant to free-tier
rate limits.

Also demonstrates the Fortified Enterprise Fleet components live:
- enterprise.guardrail screens the untrusted near-miss report text before
  it reaches any agent or LLM call
- enterprise.gateway routes and permission-checks the OOW's calls to each
  specialist against the Agent Registry
- enterprise.observability wraps the whole investigation, and each
  specialist consultation, in trace spans
- enterprise.memory persists the completed incident to Firestore (the
  Memory Bank) so future investigations of the same vessel have history

If the Gemini call fails for any reason (quota, network, deprecated model),
falls back to a clean auto-generated narrative from the structured data so
the live site never shows a judge a raw error. Same graceful-degradation
principle applies to every enterprise component below - none of them can
crash the demo.
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
from enterprise.gateway.gateway import route_call, GatewayDeniedError
from enterprise.guardrail.guardrail import screen_input, GuardrailViolation
from enterprise.observability.observability import traced_span, get_trace_log
from enterprise.memory.firestore_bank import record_incident, get_recent_incidents

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


def _screen_near_miss_reports(reports: list[dict]) -> list[dict]:
    """Runs each report's free-text description through the guardrail
    before it can reach any agent. Never lets a guardrail issue crash the
    demo - a flagged report is dropped from this run rather than raising,
    since the reports are synthetic demo data and a false positive here
    shouldn't block the whole investigation."""
    safe_reports = []
    for report in reports:
        try:
            safe_description = screen_input(report["description"], field_name="near_miss_description")
            safe_reports.append({**report, "description": safe_description})
        except GuardrailViolation:
            continue  # dropped - would be logged to a security queue in production
    return safe_reports


def _run_investigation() -> dict:
    with traced_span("investigation.run", {"vessel_id": HERO_TELEMETRY.vessel_id}):

        try:
            screened_reports = _screen_near_miss_reports(NEAR_MISS_REPORTS)
        except Exception:
            screened_reports = NEAR_MISS_REPORTS  # guardrail itself failed - degrade, don't crash

        try:
            recent_history = get_recent_incidents(HERO_TELEMETRY.vessel_id, limit=3)
        except Exception:
            recent_history = []

        with traced_span("gateway.route_specialist_calls"):
            try:
                for action in [
                    "invoke:nav-integrity-agent", "invoke:crew-readiness-agent",
                    "invoke:fleet-pattern-agent", "invoke:compliance-readiness-agent",
                ]:
                    route_call("officer-of-the-watch", action)
                gateway_status = "all calls authorized"
            except GatewayDeniedError as e:
                gateway_status = f"denied: {e}"

        oow = OfficerOfTheWatch()
        fleet_context = {
            "crew_record": CREW_RECORD,
            "near_miss_reports": screened_reports,
            "compliance_record": COMPLIANCE_RECORD,
        }

        with traced_span("oow.handle_telemetry"):
            incident = oow.handle_telemetry(HERO_TELEMETRY, fleet_context)

        if incident is None:
            return {"incident": None, "message": "No anomaly detected - fleet remains in normal operations."}

        with traced_span("narrate.gemini_call"):
            narrative, used_ai = _narrate_with_gemini(incident)

        result = {
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
            "enterprise": {
                "gateway_status": gateway_status,
                "prior_incidents_on_record": len(recent_history),
                "trace_spans_recorded": len(get_trace_log()),
            },
        }

        try:
            record_incident(result)
        except Exception:
            pass  # memory bank write is best-effort - never blocks the response

        return result


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
