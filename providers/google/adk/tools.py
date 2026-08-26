"""
ADK Tools
==========
Plain Python functions ADK's LlmAgent calls as tools. Each tool wraps a
deterministic core agent (core/, agents/) and returns a structured dict per
ADK convention: {"status": "success"|"error", ...data}.

The tools never let the model do the math - deviation distances, fatigue
scoring, and compliance scoring stay in agents/*/agent.py. The model's job
is to call the right tool and narrate the result, not compute it.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from core.domain.models import NavTelemetry
from agents.nav_integrity.agent import NavIntegrityAgent
from agents.crew_readiness.agent import CrewReadinessAgent
from agents.fleet_pattern.agent import FleetPatternAgent
from agents.compliance_readiness.agent import ComplianceReadinessAgent
from core.risk.fusion import fuse_risk
from core.domain.models import Severity

_nav = NavIntegrityAgent()
_crew = CrewReadinessAgent()
_pattern = FleetPatternAgent()
_compliance = ComplianceReadinessAgent()


def _event_to_dict(event) -> dict:
    return {
        "status": "success",
        "agent": event.agent,
        "event_type": event.event_type,
        "severity": event.severity.value,
        "confidence": event.confidence,
        "vessel_id": event.vessel_id,
        "evidence": event.evidence,
    }


def check_navigation_integrity(
    vessel_id: str,
    gps_lat: float, gps_lon: float,
    radar_lat: float, radar_lon: float,
    gyro_heading: float, speed_knots: float,
) -> dict:
    """Checks whether a vessel's GPS, radar, and gyro data agree with each
    other. Returns a structured navigation integrity finding, or a no-anomaly
    result if the sensors agree within tolerance.

    Args:
        vessel_id: The vessel identifier, e.g. "V-001".
        gps_lat: GPS-reported latitude.
        gps_lon: GPS-reported longitude.
        radar_lat: Radar-derived latitude.
        radar_lon: Radar-derived longitude.
        gyro_heading: Current gyrocompass heading in degrees.
        speed_knots: Current speed over ground in knots.

    Returns:
        A dict with status and, if an anomaly was found, severity,
        confidence, and evidence describing the disagreement.
    """
    telemetry = NavTelemetry(
        vessel_id=vessel_id,
        gps_position=(gps_lat, gps_lon),
        radar_position=(radar_lat, radar_lon),
        gyro_heading=gyro_heading,
        speed_knots=speed_knots,
    )
    event = _nav.analyze(telemetry)
    if event is None:
        return {"status": "success", "severity": "none", "evidence": ["sensors agree within tolerance"]}
    return _event_to_dict(event)


def check_crew_readiness(
    vessel_id: str,
    rest_hours_last_24: float,
    continuous_duty_hours: float,
    unusual_rotation: bool,
    role: str = "unspecified",
) -> dict:
    """Assesses crew fatigue/readiness risk from operational watch-schedule
    data. Uses no personal or medical data - only rest hours, duty hours,
    and rotation-pattern flags.

    Args:
        vessel_id: The vessel identifier.
        rest_hours_last_24: Hours of rest logged in the last 24 hours.
        continuous_duty_hours: Hours of continuous duty on current watch.
        unusual_rotation: Whether an unusual rotation pattern was flagged.
        role: The crew role being assessed, e.g. "Chief Officer".

    Returns:
        A dict with status, severity, confidence, and evidence.
    """
    record = {
        "rest_hours_last_24": rest_hours_last_24,
        "continuous_duty_hours": continuous_duty_hours,
        "unusual_rotation": unusual_rotation,
        "role": role,
    }
    event = _crew.assess(vessel_id, record)
    return _event_to_dict(event)


def check_fleet_patterns(vessel_id: str, near_miss_reports: list[dict]) -> dict:
    """Scans recent fleet-wide near-miss reports for a recurring pattern
    relevant to the current vessel's situation (e.g. repeated steering
    issues across multiple vessels).

    Args:
        vessel_id: The vessel currently under investigation.
        near_miss_reports: A list of {"vessel_id": str, "description": str}
            near-miss report records from across the fleet.

    Returns:
        A dict with status, severity, confidence, and evidence listing any
        matching reports found.
    """
    event = _pattern.find_patterns(near_miss_reports, vessel_id)
    return _event_to_dict(event)


def check_compliance_readiness(
    vessel_id: str,
    radio_cert_expires_in_days: int,
    next_port_call_in_days: int,
    previous_navigation_deficiency: bool,
) -> dict:
    """Assesses compliance exposure by reasoning about certificate expiry
    relative to the vessel's operational schedule, not just raw dates.

    Args:
        vessel_id: The vessel identifier.
        radio_cert_expires_in_days: Days until the radio certificate expires.
        next_port_call_in_days: Days until the vessel's next port call.
        previous_navigation_deficiency: Whether a prior navigation
            deficiency is on record for this vessel.

    Returns:
        A dict with status, severity, confidence, and evidence.
    """
    record = {
        "radio_cert_expires_in_days": radio_cert_expires_in_days,
        "next_port_call_in_days": next_port_call_in_days,
        "previous_navigation_deficiency": previous_navigation_deficiency,
    }
    event = _compliance.assess(vessel_id, record)
    return _event_to_dict(event)


def fuse_fleet_risk(
    nav_severity: str,
    crew_severity: str,
    historical_severity: str,
    compliance_severity: str,
    base_confidence: float,
) -> dict:
    """Combines findings from all four specialist checks into one overall
    risk assessment using fixed, auditable weighting (never left to the
    model to eyeball) - navigation weighted highest, since it is the most
    safety-critical signal.

    Args:
        nav_severity: One of "none", "low", "medium", "high", "critical".
        crew_severity: One of "none", "low", "medium", "high", "critical".
        historical_severity: One of "none", "low", "medium", "high", "critical".
        compliance_severity: One of "none", "low", "medium", "high", "critical".
        base_confidence: Confidence score (0-1) from the triggering signal.

    Returns:
        A dict with status, overall_severity, confidence, and explanation.
    """
    result = fuse_risk(
        nav_risk=Severity(nav_severity),
        crew_risk=Severity(crew_severity),
        historical_similarity=Severity(historical_severity),
        compliance_exposure=Severity(compliance_severity),
        base_confidence=base_confidence,
    )
    return {
        "status": "success",
        "overall_severity": result.overall_severity.value,
        "confidence": result.confidence,
        "explanation": result.explanation,
    }
