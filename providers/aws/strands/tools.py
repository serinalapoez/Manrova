"""
Strands Tools
==============
@tool-decorated functions Strands agents call directly. Each wraps a
deterministic core agent (core/, agents/) - the LLM never computes distances,
fatigue scores, or compliance risk itself, only calls these and narrates
the result. Identical responsibility split to providers/google/adk/tools.py,
just adapted to Strands' @tool decorator instead of ADK's plain-function
convention.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from strands import tool

from core.domain.models import NavTelemetry, Severity
from agents.nav_integrity.agent import NavIntegrityAgent
from agents.crew_readiness.agent import CrewReadinessAgent
from agents.fleet_pattern.agent import FleetPatternAgent
from agents.compliance_readiness.agent import ComplianceReadinessAgent
from core.risk.fusion import fuse_risk

_nav = NavIntegrityAgent()
_crew = CrewReadinessAgent()
_pattern = FleetPatternAgent()
_compliance = ComplianceReadinessAgent()


def _event_summary(event) -> str:
    if event is None:
        return "No anomaly detected - sensors agree within tolerance."
    lines = [f"severity={event.severity.value} confidence={event.confidence}"]
    lines.extend(f"- {e}" for e in event.evidence)
    return "\n".join(lines)


@tool
def check_navigation_integrity(
    vessel_id: str,
    gps_lat: float, gps_lon: float,
    radar_lat: float, radar_lon: float,
    gyro_heading: float, speed_knots: float,
) -> str:
    """Check whether a vessel's GPS, radar, and gyro data agree with each
    other. Returns severity, confidence, and evidence for any navigation
    integrity anomaly found, or confirms sensors agree within tolerance.

    Args:
        vessel_id: The vessel identifier, e.g. "V-001".
        gps_lat: GPS-reported latitude.
        gps_lon: GPS-reported longitude.
        radar_lat: Radar-derived latitude.
        radar_lon: Radar-derived longitude.
        gyro_heading: Current gyrocompass heading in degrees.
        speed_knots: Current speed over ground in knots.
    """
    telemetry = NavTelemetry(
        vessel_id=vessel_id,
        gps_position=(gps_lat, gps_lon),
        radar_position=(radar_lat, radar_lon),
        gyro_heading=gyro_heading,
        speed_knots=speed_knots,
    )
    return _event_summary(_nav.analyze(telemetry))


@tool
def check_crew_readiness(
    vessel_id: str,
    rest_hours_last_24: float,
    continuous_duty_hours: float,
    unusual_rotation: bool,
    role: str = "unspecified",
) -> str:
    """Assess crew fatigue/readiness risk from operational watch-schedule
    data only - no personal or medical data.

    Args:
        vessel_id: The vessel identifier.
        rest_hours_last_24: Hours of rest logged in the last 24 hours.
        continuous_duty_hours: Hours of continuous duty on current watch.
        unusual_rotation: Whether an unusual rotation pattern was flagged.
        role: The crew role being assessed, e.g. "Chief Officer".
    """
    record = {
        "rest_hours_last_24": rest_hours_last_24,
        "continuous_duty_hours": continuous_duty_hours,
        "unusual_rotation": unusual_rotation,
        "role": role,
    }
    return _event_summary(_crew.assess(vessel_id, record))


@tool
def check_fleet_patterns(vessel_id: str, near_miss_reports_json: str) -> str:
    """Scan recent fleet-wide near-miss reports for a recurring pattern
    relevant to the vessel under investigation.

    Args:
        vessel_id: The vessel currently under investigation.
        near_miss_reports_json: JSON array of near-miss report objects, each
            with "vessel_id" and "description" string fields.
    """
    import json
    reports = json.loads(near_miss_reports_json)
    return _event_summary(_pattern.find_patterns(reports, vessel_id))


@tool
def check_compliance_readiness(
    vessel_id: str,
    radio_cert_expires_in_days: int,
    next_port_call_in_days: int,
    previous_navigation_deficiency: bool,
) -> str:
    """Assess compliance exposure by reasoning about certificate expiry
    relative to the vessel's operational schedule, not just raw dates.

    Args:
        vessel_id: The vessel identifier.
        radio_cert_expires_in_days: Days until the radio certificate expires.
        next_port_call_in_days: Days until the vessel's next port call.
        previous_navigation_deficiency: Whether a prior navigation
            deficiency is on record for this vessel.
    """
    record = {
        "radio_cert_expires_in_days": radio_cert_expires_in_days,
        "next_port_call_in_days": next_port_call_in_days,
        "previous_navigation_deficiency": previous_navigation_deficiency,
    }
    return _event_summary(_compliance.assess(vessel_id, record))


@tool
def fuse_fleet_risk(
    nav_severity: str,
    crew_severity: str,
    historical_severity: str,
    compliance_severity: str,
    base_confidence: float,
) -> str:
    """Combine findings from all four specialist checks into one overall
    risk assessment using fixed, auditable weighting - never left to the
    model to eyeball. Navigation is weighted highest as the most
    safety-critical signal.

    Args:
        nav_severity: One of "none", "low", "medium", "high", "critical".
        crew_severity: One of "none", "low", "medium", "high", "critical".
        historical_severity: One of "none", "low", "medium", "high", "critical".
        compliance_severity: One of "none", "low", "medium", "high", "critical".
        base_confidence: Confidence score (0-1) from the triggering signal.
    """
    result = fuse_risk(
        nav_risk=Severity(nav_severity),
        crew_risk=Severity(crew_severity),
        historical_similarity=Severity(historical_severity),
        compliance_exposure=Severity(compliance_severity),
        base_confidence=base_confidence,
    )
    lines = [f"overall_severity={result.overall_severity.value} confidence={result.confidence}"]
    lines.extend(f"- {e}" for e in result.explanation)
    return "\n".join(lines)
