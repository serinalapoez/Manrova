"""
Manrova - Incident State Machine
==================================
Deterministic, strict transitions. This is intentionally NOT left to the LLM -
state integrity is a correctness requirement, not a reasoning task.
"""

from core.domain.models import IncidentState

VALID_TRANSITIONS: dict[IncidentState, set[IncidentState]] = {
    IncidentState.NORMAL: {IncidentState.SIGNAL_DETECTED},
    IncidentState.SIGNAL_DETECTED: {IncidentState.CORRELATING},
    IncidentState.CORRELATING: {IncidentState.RISK_ASSESSMENT},
    IncidentState.RISK_ASSESSMENT: {IncidentState.MONITOR, IncidentState.INCIDENT_MODE},
    IncidentState.MONITOR: {IncidentState.NORMAL, IncidentState.SIGNAL_DETECTED},
    IncidentState.INCIDENT_MODE: {IncidentState.INVESTIGATION},
    IncidentState.INVESTIGATION: {IncidentState.ACTION_PLAN},
    IncidentState.ACTION_PLAN: {IncidentState.AWAITING_APPROVAL, IncidentState.EXECUTING},
    IncidentState.AWAITING_APPROVAL: {IncidentState.EXECUTING},
    IncidentState.EXECUTING: {IncidentState.TRACKING},
    IncidentState.TRACKING: {IncidentState.RESOLUTION},
    IncidentState.RESOLUTION: {IncidentState.LEARNING},
    IncidentState.LEARNING: {IncidentState.NORMAL},
}


class InvalidTransitionError(Exception):
    pass


def assert_valid_transition(current: IncidentState, target: IncidentState) -> None:
    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(
            f"Cannot move from {current.value} to {target.value}. "
            f"Allowed: {[s.value for s in allowed]}"
        )
