"""
Agent Registry
================
The central repository for publishing, versioning, and discovering
enterprise-approved agents, per the Fortified Enterprise Fleet track
requirement. Backed by the same free Firestore instance as the Memory Bank.

Run `python -m enterprise.registry.seed_registry` once (after Firestore
credentials are configured) to publish Manrova's five agents to the
registry. Read with `list_registered_agents()`.
"""

from __future__ import annotations
from datetime import datetime, timezone

_COLLECTION = "manrova_agent_registry"

AGENTS = [
    {
        "agent_id": "nav-integrity-agent",
        "name": "Nav Integrity Agent",
        "version": "1.0.0",
        "owner": "Manrova Platform Team",
        "description": "Checks GPS/radar/gyro/speed agreement for navigation integrity anomalies.",
        "department": "Fleet Safety",
        "permissions": ["read:vessel_telemetry"],
    },
    {
        "agent_id": "crew-readiness-agent",
        "name": "Crew Readiness Agent",
        "version": "1.0.0",
        "owner": "Manrova Platform Team",
        "description": "Assesses fatigue/readiness risk from watch-schedule data.",
        "department": "Fleet Safety",
        "permissions": ["read:crew_watch_schedule"],
    },
    {
        "agent_id": "fleet-pattern-agent",
        "name": "Fleet Pattern Agent",
        "version": "1.0.0",
        "owner": "Manrova Platform Team",
        "description": "Scans fleet-wide near-miss reports for recurring cross-vessel patterns.",
        "department": "Fleet Safety",
        "permissions": ["read:near_miss_reports"],
    },
    {
        "agent_id": "compliance-readiness-agent",
        "name": "Compliance Readiness Agent",
        "version": "1.0.0",
        "owner": "Manrova Platform Team",
        "description": "Reasons about certificate/deficiency exposure relative to vessel schedule.",
        "department": "Compliance",
        "permissions": ["read:compliance_records"],
    },
    {
        "agent_id": "officer-of-the-watch",
        "name": "Officer of the Watch (OOW)",
        "version": "1.0.0",
        "owner": "Manrova Platform Team",
        "description": "Root orchestrating agent - correlates specialist findings, fuses risk, prepares actions.",
        "department": "Fleet Safety",
        "permissions": ["invoke:nav-integrity-agent", "invoke:crew-readiness-agent",
                         "invoke:fleet-pattern-agent", "invoke:compliance-readiness-agent",
                         "write:incident_actions"],
    },
]


from enterprise._gcp_auth import get_firestore_client as _get_firestore_client


def seed_registry() -> int:
    """Publishes all five agents to Firestore. Returns count written."""
    client = _get_firestore_client()
    if client is None:
        print("No Firestore credentials found - nothing written. "
              "Set GOOGLE_APPLICATION_CREDENTIALS and retry.")
        return 0

    for agent in AGENTS:
        record = dict(agent)
        record["_published_at"] = datetime.now(timezone.utc).isoformat()
        client.collection(_COLLECTION).document(agent["agent_id"]).set(record)

    print(f"Published {len(AGENTS)} agents to the registry.")
    return len(AGENTS)


def list_registered_agents() -> list[dict]:
    client = _get_firestore_client()
    if client is None:
        return AGENTS  # local fallback - the source list itself
    return [doc.to_dict() for doc in client.collection(_COLLECTION).stream()]


if __name__ == "__main__":
    seed_registry()
