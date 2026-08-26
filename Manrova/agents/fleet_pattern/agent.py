"""
Fleet Pattern Agent
======================
Looks for recurring signals across vessels (near-misses, incident reports)
that individually look minor but together indicate an emerging fleet-wide
issue. This is the "one vessel's experience protects the fleet" capability.
"""

from collections import Counter
from core.domain.models import AgentEvent, Severity, new_id

# crude keyword clustering for the demo - a real build would use embeddings
_STEERING_KEYWORDS = ["steering", "rudder", "helm"]


class FleetPatternAgent:
    name = "FleetPatternAgent"

    def find_patterns(self, near_miss_reports: list[dict], focus_vessel_id: str) -> AgentEvent:
        matches = [
            r for r in near_miss_reports
            if any(k in r["description"].lower() for k in _STEERING_KEYWORDS)
        ]
        vessels_affected = sorted({r["vessel_id"] for r in matches})

        if len(vessels_affected) >= 2:
            severity = Severity.HIGH if len(vessels_affected) >= 3 else Severity.MEDIUM
            confidence = min(0.95, 0.55 + 0.12 * len(vessels_affected))
            evidence = [f'{r["vessel_id"]}: "{r["description"]}"' for r in matches]
            evidence.append(f"{len(vessels_affected)} vessels affected across fleet")
        else:
            severity = Severity.NONE
            confidence = 0.6
            evidence = ["no recurring cross-vessel pattern detected"]

        return AgentEvent(
            event_id=new_id("evt"),
            agent=self.name,
            event_type="fleet_pattern",
            severity=severity,
            confidence=round(confidence, 2),
            vessel_id=focus_vessel_id,
            evidence=evidence,
            raw={"vessels_affected": vessels_affected},
        )
