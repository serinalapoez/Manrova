"""
Memory Bank
=============
Persistent, secure cross-session context for the Fortified Enterprise Fleet
track. Backed by Cloud Firestore (Firebase Spark plan - genuinely free, no
billing account required, distinct from Cloud Run/Compute which do need
billing). Every investigation the OOW completes is written here, so the
fleet's history survives beyond a single process run - the literal
"memory" the four agents draw context from over time.

Falls back to an in-memory dict if Firestore isn't configured (no
credentials found), so local development and offline testing never break -
this mirrors the same graceful-degradation pattern used for the Gemini
narrative call in api/investigate.py.
"""

from __future__ import annotations
import os
import json
from datetime import datetime, timezone

_COLLECTION = "manrova_incidents"

# In-memory fallback store, keyed by incident_id - used when Firestore
# credentials aren't available (e.g. running the CLI demo locally without
# a service account configured).
_fallback_store: dict[str, dict] = {}


from enterprise._gcp_auth import get_firestore_client as _get_firestore_client


def record_incident(incident_dict: dict) -> None:
    """Persist a completed (or in-progress) incident record. Accepts the
    same JSON-serializable dict shape api/investigate.py already builds -
    no separate schema to maintain."""
    payload = dict(incident_dict)
    payload["_recorded_at"] = datetime.now(timezone.utc).isoformat()

    client = _get_firestore_client()
    if client is None:
        _fallback_store[payload.get("incident_id", "unknown")] = payload
        return

    doc_id = payload.get("incident_id", "unknown")
    client.collection(_COLLECTION).document(doc_id).set(payload)


def get_recent_incidents(vessel_id: str, limit: int = 5) -> list[dict]:
    """Retrieve recent incident history for a vessel - this is what lets a
    specialist agent say 'this vessel had a similar event 3 weeks ago'
    instead of starting from zero every time."""
    client = _get_firestore_client()
    if client is None:
        matches = [v for v in _fallback_store.values() if v.get("vessel_id") == vessel_id]
        return sorted(matches, key=lambda r: r.get("_recorded_at", ""), reverse=True)[:limit]

    query = (
        client.collection(_COLLECTION)
        .where("vessel_id", "==", vessel_id)
        .order_by("_recorded_at", direction="DESCENDING")
        .limit(limit)
    )
    return [doc.to_dict() for doc in query.stream()]


def get_incident_by_id(incident_id: str) -> dict | None:
    """Retrieves a single incident record by ID - used by the Approve &
    Send flow, which resumes an investigation across a separate serverless
    request rather than holding a live Python object in memory."""
    client = _get_firestore_client()
    if client is None:
        return _fallback_store.get(incident_id)

    doc = client.collection(_COLLECTION).document(incident_id).get()
    return doc.to_dict() if doc.exists else None
