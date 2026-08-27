"""
Manrova - Core Domain Models
=============================
Shared, provider-agnostic data structures. Both the AWS/Strands build and the
Google/ADK build import from here. Nothing in this file knows about Gemini,
Bedrock, Strands, or Google Cloud - that separation is the point.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentState(str, Enum):
    NORMAL = "normal"
    SIGNAL_DETECTED = "signal_detected"
    CORRELATING = "correlating"
    RISK_ASSESSMENT = "risk_assessment"
    MONITOR = "monitor"
    INCIDENT_MODE = "incident_mode"
    INVESTIGATION = "investigation"
    ACTION_PLAN = "action_plan"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    TRACKING = "tracking"
    RESOLUTION = "resolution"
    LEARNING = "learning"


@dataclass
class Vessel:
    vessel_id: str
    name: str
    vessel_class: str
    status: str = "normal"  # normal | monitoring | incident


@dataclass
class NavTelemetry:
    vessel_id: str
    gps_position: tuple
    radar_position: tuple
    gyro_heading: float
    speed_knots: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentEvent:
    """Structured output every specialist agent produces. This is what gets
    reasoned over by the Officer of the Watch - never raw free text."""
    event_id: str
    agent: str
    event_type: str
    severity: Severity
    confidence: float
    vessel_id: str
    evidence: list[str]
    raw: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskAssessment:
    nav_risk: Severity
    crew_risk: Severity
    historical_similarity: Severity
    compliance_exposure: Severity
    overall_severity: Severity
    confidence: float
    explanation: list[str]


@dataclass
class PreparedAction:
    action_id: str
    kind: str  # "internal" | "external"
    description: str
    requires_approval: bool
    approved: bool = False
    executed: bool = False


@dataclass
class TimelineEntry:
    timestamp: datetime
    actor: str
    description: str


@dataclass
class Incident:
    incident_id: str
    vessel_id: str
    state: IncidentState = IncidentState.NORMAL
    events: list[AgentEvent] = field(default_factory=list)
    risk: Optional[RiskAssessment] = None
    actions: list[PreparedAction] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    resolved: bool = False

    def log(self, actor: str, description: str) -> None:
        self.timeline.append(TimelineEntry(datetime.utcnow(), actor, description))

    def transition(self, new_state: IncidentState, actor: str = "Officer of the Watch") -> None:
        self.log(actor, f"State: {self.state.value} -> {new_state.value}")
        self.state = new_state
