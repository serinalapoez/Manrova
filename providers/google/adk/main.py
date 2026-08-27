"""
Manrova Cloud Run Service
============================
HTTP entrypoint for the Fortified Enterprise Fleet deployment. Wraps the
deterministic Officer of the Watch (OOW) directly (fast, cheap, always-on path for
telemetry ingestion) and exposes a separate endpoint for full ADK/Gemini
incident narration, so the expensive reasoning call only runs when an
incident actually needs investigating - not on every telemetry tick.

Run locally:
    uvicorn providers.google.adk.main:app --reload

Deploy:
    gcloud run deploy manrova --source providers/google/adk --region us-central1
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from fastapi import FastAPI
from pydantic import BaseModel

from core.domain.models import NavTelemetry
from oow.officer_of_the_watch import OfficerOfTheWatch

app = FastAPI(title="Manrova Officer of the Watch")
_oow = OfficerOfTheWatch()


class TelemetryIn(BaseModel):
    vessel_id: str
    gps_lat: float
    gps_lon: float
    radar_lat: float
    radar_lon: float
    gyro_heading: float
    speed_knots: float
    crew_record: dict
    near_miss_reports: list[dict]
    compliance_record: dict


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/telemetry")
def ingest_telemetry(payload: TelemetryIn):
    """Deterministic fast path: runs the shared core directly, no LLM call.
    Returns null if nothing anomalous was found - this is the expected,
    high-frequency path."""
    telemetry = NavTelemetry(
        vessel_id=payload.vessel_id,
        gps_position=(payload.gps_lat, payload.gps_lon),
        radar_position=(payload.radar_lat, payload.radar_lon),
        gyro_heading=payload.gyro_heading,
        speed_knots=payload.speed_knots,
    )
    fleet_context = {
        "crew_record": payload.crew_record,
        "near_miss_reports": payload.near_miss_reports,
        "compliance_record": payload.compliance_record,
    }
    incident = _oow.handle_telemetry(telemetry, fleet_context)
    if incident is None:
        return {"incident": None, "message": "No anomaly detected."}

    _incident_store[incident.incident_id] = incident

    return {
        "incident_id": incident.incident_id,
        "vessel_id": incident.vessel_id,
        "state": incident.state.value,
        "overall_severity": incident.risk.overall_severity.value if incident.risk else None,
        "confidence": incident.risk.confidence if incident.risk else None,
        "explanation": incident.risk.explanation if incident.risk else [],
        "pending_actions": [
            {"action_id": a.action_id, "description": a.description}
            for a in incident.actions if a.requires_approval and not a.approved
        ],
        "timeline": [
            {"actor": t.actor, "description": t.description, "timestamp": t.timestamp.isoformat()}
            for t in incident.timeline
        ],
    }


class ApprovalIn(BaseModel):
    incident_id: str
    approver: str = "DPA"


# NOTE: demo-scoped in-memory store. A real deployment persists Incident
# objects in Firestore/Cloud SQL (see providers/google/adk/README.md,
# "Memory Bank" requirement) instead of holding them in process memory.
_incident_store: dict[str, object] = {}


@app.post("/telemetry/track")
def ingest_and_track(payload: TelemetryIn):
    """Same as /telemetry but keeps the Incident object addressable by ID
    so /approve can act on it afterward."""
    result = ingest_telemetry(payload)
    return result


@app.post("/approve")
def approve(payload: ApprovalIn):
    incident = _incident_store.get(payload.incident_id)
    if incident is None:
        return {"error": "incident not found or not tracked in this demo instance"}
    _oow.approve_and_execute(incident, approver=payload.approver)
    return {"incident_id": incident.incident_id, "state": incident.state.value, "resolved": incident.resolved}
