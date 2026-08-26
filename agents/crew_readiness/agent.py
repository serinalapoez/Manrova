"""
Crew Readiness Agent
======================
Assesses fatigue/readiness risk from watch schedules and rest hours.
Non-sensitive operational data only - no personal/medical data.
"""

from core.domain.models import AgentEvent, Severity, new_id


class CrewReadinessAgent:
    name = "CrewReadinessAgent"

    def assess(self, vessel_id: str, crew_record: dict) -> AgentEvent:
        rest_hours_last_24 = crew_record.get("rest_hours_last_24", 8)
        continuous_duty_hours = crew_record.get("continuous_duty_hours", 0)
        rotation_flag = crew_record.get("unusual_rotation", False)

        risk_points = 0
        evidence = []

        if rest_hours_last_24 < 6:
            risk_points += 2
            evidence.append(f"reduced rest interval ({rest_hours_last_24}h in last 24h)")
        if continuous_duty_hours > 10:
            risk_points += 2
            evidence.append(f"extended watch pattern ({continuous_duty_hours}h continuous duty)")
        if rotation_flag:
            risk_points += 1
            evidence.append("unusual rotation pattern flagged")

        if risk_points >= 4:
            severity = Severity.HIGH
        elif risk_points >= 2:
            severity = Severity.MEDIUM
        elif risk_points >= 1:
            severity = Severity.LOW
        else:
            severity = Severity.NONE
            evidence.append("no elevated fatigue indicators")

        return AgentEvent(
            event_id=new_id("evt"),
            agent=self.name,
            event_type="crew_readiness",
            severity=severity,
            confidence=0.85,
            vessel_id=vessel_id,
            evidence=evidence,
            raw={"role": crew_record.get("role", "unspecified")},
        )
