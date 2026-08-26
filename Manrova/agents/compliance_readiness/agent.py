"""
Compliance Readiness Agent
=============================
Reasons about operational consequences of compliance state, not just dates.
"""

from datetime import datetime
from core.domain.models import AgentEvent, Severity, new_id


class ComplianceReadinessAgent:
    name = "ComplianceReadinessAgent"

    def assess(self, vessel_id: str, compliance_record: dict) -> AgentEvent:
        expiry_days = compliance_record.get("radio_cert_expires_in_days", 999)
        next_port_call_days = compliance_record.get("next_port_call_in_days", 999)
        prior_deficiency = compliance_record.get("previous_navigation_deficiency", False)

        evidence = []
        risk_points = 0

        if expiry_days <= 30:
            risk_points += 1
            evidence.append(f"radio certificate expires in {expiry_days} days")
        if expiry_days <= next_port_call_days:
            risk_points += 1
            evidence.append(
                f"certificate expiry ({expiry_days}d) falls before next port call ({next_port_call_days}d)"
            )
        if prior_deficiency:
            risk_points += 1
            evidence.append("previous navigation deficiency on record")

        if risk_points >= 3:
            severity = Severity.HIGH
        elif risk_points == 2:
            severity = Severity.MEDIUM
        elif risk_points == 1:
            severity = Severity.LOW
        else:
            severity = Severity.NONE
            evidence.append("compliance status nominal")

        return AgentEvent(
            event_id=new_id("evt"),
            agent=self.name,
            event_type="compliance_readiness",
            severity=severity,
            confidence=0.9,
            vessel_id=vessel_id,
            evidence=evidence,
            raw={"checked_at": datetime.utcnow().isoformat()},
        )
