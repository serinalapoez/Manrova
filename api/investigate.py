"""
Manrova Live Demo - Serverless Investigation Endpoint
========================================================
Vercel Python function. Reuses the exact shared core (core/, agents/,
oow/, data/demo/) - no duplicated business logic. Makes exactly ONE
Gemini call to narrate the already-computed structured result.

POST body is optional. If empty, runs the built-in MV Atlas demo scenario
(so the site still works with a single click for a casual visitor). If a
body is provided with real vessel data - as a registered tenant's vessel
would send - it runs the exact same pipeline on that real data instead.
Nothing about the OOW's logic changes between the two paths; only where
the input numbers come from changes.

Also demonstrates the Fortified Enterprise Fleet components live:
guardrail screening, gateway routing, observability tracing, and the
Memory Bank - see the enterprise/ package for each.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.domain.models import NavTelemetry
from oow.officer_of_the_watch import OfficerOfTheWatch
from data.demo.fleet_data import (
    HERO_TELEMETRY, CREW_RECORD, COMPLIANCE_RECORD, NEAR_MISS_REPORTS,
)
from enterprise.gateway.gateway import route_call, GatewayDeniedError
from enterprise.guardrail.guardrail import screen_input, GuardrailViolation
from enterprise.observability.observability import traced_span, get_trace_log
from enterprise.memory.firestore_bank import record_incident, get_recent_incidents
from enterprise.tenancy.tenancy import lookup_company

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
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return _fallback_narrative(incident), False
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = _build_prompt(incident)
        for model in FALLBACK_MODELS:
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                text = getattr(response, "text", None)
                if text:
                    return text.strip(), True
            except Exception:  # noqa: BLE001
                continue
        return _fallback_narrative(incident), False
    except Exception:
        return _fallback_narrative(incident), False


def _screen_near_miss_reports(reports: list[dict]) -> list[dict]:
    safe_reports = []
    for report in reports:
        try:
            safe_description = screen_input(report.get("description", ""), field_name="near_miss_description")
            safe_reports.append({**report, "description": safe_description})
        except GuardrailViolation:
            continue
    return safe_reports


def _build_telemetry_from_payload(payload: dict) -> NavTelemetry:
    """Builds a NavTelemetry from a real submitted payload. Missing fields
    fall back to the demo scenario's values, so a partial submission still
    produces a sensible result rather than erroring."""
    t = payload.get("telemetry", {})
    vessel_id = str(payload.get("vessel_id") or payload.get("vessel_name") or HERO_TELEMETRY.vessel_id)[:80]

    try:
        vessel_id = screen_input(vessel_id, field_name="vessel_id")
    except GuardrailViolation:
        vessel_id = HERO_TELEMETRY.vessel_id  # a flagged custom ID falls back rather than 500ing

    return NavTelemetry(
        vessel_id=vessel_id,
        gps_position=(
            float(t.get("gps_lat", HERO_TELEMETRY.gps_position[0])),
            float(t.get("gps_lon", HERO_TELEMETRY.gps_position[1])),
        ),
        radar_position=(
            float(t.get("radar_lat", HERO_TELEMETRY.radar_position[0])),
            float(t.get("radar_lon", HERO_TELEMETRY.radar_position[1])),
        ),
        gyro_heading=float(t.get("gyro_heading", HERO_TELEMETRY.gyro_heading)),
        speed_knots=float(t.get("speed_knots", HERO_TELEMETRY.speed_knots)),
    )


def _run_investigation(payload: dict) -> dict:
    with traced_span("investigation.run", {"has_custom_payload": bool(payload)}):

        is_custom = bool(payload)
        company_id = payload.get("company_id")

        try:
            telemetry = _build_telemetry_from_payload(payload) if is_custom else HERO_TELEMETRY
        except (TypeError, ValueError):
            telemetry = HERO_TELEMETRY  # malformed numeric input - degrade to demo rather than 500

        crew_record = payload.get("crew_record") if is_custom else CREW_RECORD
        compliance_record = payload.get("compliance_record") if is_custom else COMPLIANCE_RECORD
        near_miss_reports = payload.get("near_miss_reports") if is_custom else NEAR_MISS_REPORTS
        crew_record = crew_record or CREW_RECORD
        compliance_record = compliance_record or COMPLIANCE_RECORD
        near_miss_reports = near_miss_reports or []

        try:
            screened_reports = _screen_near_miss_reports(near_miss_reports)
        except Exception:
            screened_reports = near_miss_reports

        try:
            recent_history = get_recent_incidents(telemetry.vessel_id, limit=3)
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
            "crew_record": crew_record,
            "near_miss_reports": screened_reports,
            "compliance_record": compliance_record,
        }

        with traced_span("oow.handle_telemetry"):
            incident = oow.handle_telemetry(telemetry, fleet_context)

        if incident is None:
            return {
                "incident": None,
                "message": "No anomaly detected - vessel remains in normal operations.",
                "vessel_id": telemetry.vessel_id,
                "data_source": "custom" if is_custom else "demo",
            }

        with traced_span("narrate.gemini_call"):
            narrative, used_ai = _narrate_with_gemini(incident)

        result = {
            "incident_id": incident.incident_id,
            "vessel_id": incident.vessel_id,
            "state": incident.state.value,
            "narrative": narrative,
            "narrative_source": "gemini" if used_ai else "auto-generated",
            "data_source": "custom" if is_custom else "demo",
            "company_id": company_id,
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
                {"description": a.description} for a in incident.actions if a.requires_approval
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
            pass

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
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw or b"{}")
            result = _run_investigation(payload)
            self._send_json(result)
        except Exception as e:  # noqa: BLE001
            self._send_json({"error": str(e)}, status=500)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
