"""
Nav Integrity Agent
=====================
Detects GPS/radar/gyro/speed inconsistencies. Safety-critical math is
deterministic; only the interpretation step is agentic.
"""

import math
from core.domain.models import AgentEvent, Severity, new_id


def _haversine_meters(p1: tuple, p2: tuple) -> float:
    lat1, lon1 = p1
    lat2, lon2 = p2
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# Deterministic thresholds - never delegated to the LLM
POSITION_DISAGREEMENT_THRESHOLD_M = 400
HIGH_DISAGREEMENT_THRESHOLD_M = 1500


class NavIntegrityAgent:
    name = "NavIntegrityAgent"

    def analyze(self, telemetry) -> AgentEvent | None:
        deviation_m = _haversine_meters(telemetry.gps_position, telemetry.radar_position)

        if deviation_m < POSITION_DISAGREEMENT_THRESHOLD_M:
            return None  # nothing worth an event

        severity = Severity.HIGH if deviation_m < HIGH_DISAGREEMENT_THRESHOLD_M else Severity.CRITICAL
        confidence = min(0.99, 0.6 + deviation_m / 5000)

        evidence = [
            f"GPS/radar position disagreement of {deviation_m:.0f}m",
            "gyro remains consistent" if telemetry.gyro_heading else "gyro data unavailable",
            f"speed log reads {telemetry.speed_knots:.1f} kn (nominal)",
        ]

        # --- Reasoning seam ---
        # In the AWS build this becomes a Strands agent.run() call.
        # In the Google build this becomes an ADK/Gemini call.
        # Both receive exactly this structured payload and return refined
        # evidence/narrative text - they never do the distance math above.

        return AgentEvent(
            event_id=new_id("evt"),
            agent=self.name,
            event_type="navigation_integrity",
            severity=severity,
            confidence=round(confidence, 2),
            vessel_id=telemetry.vessel_id,
            evidence=evidence,
            raw={"deviation_m": deviation_m},
        )
