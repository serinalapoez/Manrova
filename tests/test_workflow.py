import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from core.domain.models import Severity, IncidentState
from core.domain.state_machine import assert_valid_transition, InvalidTransitionError
from core.risk.fusion import fuse_risk
from oow.officer_of_the_watch import OfficerOfTheWatch
from data.demo.fleet_data import HERO_TELEMETRY, CREW_RECORD, COMPLIANCE_RECORD, NEAR_MISS_REPORTS


def test_valid_transition_allowed():
    assert_valid_transition(IncidentState.NORMAL, IncidentState.SIGNAL_DETECTED)


def test_invalid_transition_rejected():
    with pytest.raises(InvalidTransitionError):
        assert_valid_transition(IncidentState.NORMAL, IncidentState.EXECUTING)


def test_risk_fusion_escalates_on_corroborating_evidence():
    result = fuse_risk(
        nav_risk=Severity.HIGH,
        crew_risk=Severity.HIGH,
        historical_similarity=Severity.HIGH,
        compliance_exposure=Severity.LOW,
        base_confidence=0.9,
    )
    assert result.overall_severity in (Severity.HIGH, Severity.CRITICAL)
    assert len(result.explanation) >= 2


def test_low_risk_stays_quiet():
    result = fuse_risk(
        nav_risk=Severity.LOW,
        crew_risk=Severity.NONE,
        historical_similarity=Severity.NONE,
        compliance_exposure=Severity.NONE,
        base_confidence=0.7,
    )
    assert result.overall_severity in (Severity.NONE, Severity.LOW)


def test_full_incident_workflow_reaches_resolution():
    oow = OfficerOfTheWatch()
    fleet_context = {
        "crew_record": CREW_RECORD,
        "near_miss_reports": NEAR_MISS_REPORTS,
        "compliance_record": COMPLIANCE_RECORD,
    }
    incident = oow.handle_telemetry(HERO_TELEMETRY, fleet_context)
    assert incident is not None
    assert incident.state in (IncidentState.AWAITING_APPROVAL, IncidentState.EXECUTING)

    oow.approve_and_execute(incident)
    assert incident.resolved is True
    assert incident.state == IncidentState.NORMAL
    assert all(a.executed for a in incident.actions if a.requires_approval)
