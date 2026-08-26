"""
Fleet Conductor
=================
The product centerpiece. Receives a Nav Integrity event, decides what
additional context is needed, requests it from the other specialists,
fuses risk, prepares actions, and drives the incident through its state
machine - stopping for human approval on consequential external actions.
"""

from core.domain.models import (
    Incident, IncidentState, PreparedAction, Severity, new_id,
)
from core.domain.state_machine import assert_valid_transition
from core.risk.fusion import fuse_risk
from agents.nav_integrity.agent import NavIntegrityAgent
from agents.crew_readiness.agent import CrewReadinessAgent
from agents.fleet_pattern.agent import FleetPatternAgent
from agents.compliance_readiness.agent import ComplianceReadinessAgent


class FleetConductor:
    def __init__(self):
        self.nav_agent = NavIntegrityAgent()
        self.crew_agent = CrewReadinessAgent()
        self.pattern_agent = FleetPatternAgent()
        self.compliance_agent = ComplianceReadinessAgent()

    def _move(self, incident: Incident, target: IncidentState, actor: str = "Conductor"):
        assert_valid_transition(incident.state, target)
        incident.transition(target, actor)

    def handle_telemetry(self, telemetry, fleet_context: dict) -> Incident | None:
        """Entry point: a telemetry tick arrives. Returns an Incident if the
        Nav Integrity Agent finds something worth investigating, else None
        (the Conductor stays silent - this is the default, expected path)."""

        nav_event = self.nav_agent.analyze(telemetry)
        if nav_event is None:
            return None  # normal operations, no notification, no incident

        incident = Incident(incident_id=new_id("incident"), vessel_id=telemetry.vessel_id)
        incident.log("NavIntegrityAgent", f"Anomaly detected: {nav_event.evidence[0]}")
        incident.events.append(nav_event)

        self._move(incident, IncidentState.SIGNAL_DETECTED)
        self._move(incident, IncidentState.CORRELATING)

        # --- Gather context from the other specialists ---
        crew_event = self.crew_agent.assess(telemetry.vessel_id, fleet_context["crew_record"])
        incident.events.append(crew_event)
        incident.log("CrewReadinessAgent", f"Readiness result: {crew_event.severity.value}")

        pattern_event = self.pattern_agent.find_patterns(
            fleet_context["near_miss_reports"], telemetry.vessel_id
        )
        incident.events.append(pattern_event)
        incident.log("FleetPatternAgent", f"Pattern scan: {pattern_event.severity.value}")

        compliance_event = self.compliance_agent.assess(
            telemetry.vessel_id, fleet_context["compliance_record"]
        )
        incident.events.append(compliance_event)
        incident.log("ComplianceReadinessAgent", f"Compliance context: {compliance_event.severity.value}")

        self._move(incident, IncidentState.RISK_ASSESSMENT)

        risk = fuse_risk(
            nav_risk=nav_event.severity,
            crew_risk=crew_event.severity,
            historical_similarity=pattern_event.severity,
            compliance_exposure=compliance_event.severity,
            base_confidence=nav_event.confidence,
        )
        incident.risk = risk
        incident.log("Conductor", f"Overall severity assessed: {risk.overall_severity.value} ({risk.confidence:.0%} confidence)")

        if risk.overall_severity in (Severity.NONE, Severity.LOW):
            self._move(incident, IncidentState.MONITOR)
            incident.log("Conductor", "Risk below incident threshold - continuing to monitor.")
            return incident

        # --- Incident mode ---
        self._move(incident, IncidentState.INCIDENT_MODE)
        self._move(incident, IncidentState.INVESTIGATION)
        incident.log("Conductor", "Evidence collected across all specialists.")

        self._move(incident, IncidentState.ACTION_PLAN)
        actions = self._prepare_actions(incident)
        incident.actions = actions

        needs_approval = any(a.requires_approval for a in actions)
        if needs_approval:
            self._move(incident, IncidentState.AWAITING_APPROVAL)
            incident.log("Conductor", f"{sum(a.requires_approval for a in actions)} action(s) require human approval.")
        else:
            self._move(incident, IncidentState.EXECUTING)

        return incident

    def _prepare_actions(self, incident: Incident) -> list[PreparedAction]:
        actions = [
            PreparedAction(new_id("act"), "internal", "Evidence package compiled", requires_approval=False),
            PreparedAction(new_id("act"), "internal", "Incident timeline created", requires_approval=False),
        ]
        if incident.risk.overall_severity in (Severity.HIGH, Severity.CRITICAL):
            actions.append(PreparedAction(new_id("act"), "external", "Notify Master", requires_approval=True))
            actions.append(PreparedAction(new_id("act"), "external", "Notify DPA", requires_approval=True))
        if incident.risk.overall_severity == Severity.CRITICAL:
            actions.append(PreparedAction(new_id("act"), "external", "Notify Class Society", requires_approval=True))
        for a in actions:
            incident.log("Conductor", f"Prepared action: {a.description} ({'approval required' if a.requires_approval else 'internal'})")
        return actions

    def approve_and_execute(self, incident: Incident, approver: str = "DPA") -> None:
        """Human approves the pending external actions. Only actions marked
        requires_approval are gated here - internal prep work already ran."""
        assert_valid_transition(incident.state, IncidentState.EXECUTING)
        for a in incident.actions:
            if a.requires_approval:
                a.approved = True
                incident.log(approver, f"Approved: {a.description}")
        incident.transition(IncidentState.EXECUTING, actor=approver)
        for a in incident.actions:
            a.executed = True
            incident.log("Conductor", f"Executed: {a.description}")

        self._move(incident, IncidentState.TRACKING)
        self._move(incident, IncidentState.RESOLUTION)
        incident.resolved = True
        incident.log("Conductor", "Incident marked resolved.")

        self._move(incident, IncidentState.LEARNING)
        incident.log("Conductor", "Outcome stored in fleet memory for future correlation.")
        self._move(incident, IncidentState.NORMAL)
