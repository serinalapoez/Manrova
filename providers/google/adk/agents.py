"""
ADK Agents
===========
Wires the deterministic core into Gemini-powered ADK agents. Each specialist
is a narrow LlmAgent with exactly one tool - it cannot do anything the tool
doesn't expose, which keeps it from freelancing on safety-critical findings.

The Fleet Conductor is the root_agent: it has all four specialists as
sub_agents plus the fusion tool, and its instruction encodes the same
workflow discipline as conductor/fleet_conductor/conductor.py - gather
context from every specialist before fusing risk, and always fuse risk
before proposing any external action.

Run locally with either:
    adk run providers/google/adk
    adk web providers/google/adk    (browser dev UI)

Requires:
    pip install google-adk
    export GOOGLE_API_KEY=<your Gemini API key>
"""

from google.adk.agents.llm_agent import Agent

from .tools import (
    check_navigation_integrity,
    check_crew_readiness,
    check_fleet_patterns,
    check_compliance_readiness,
    fuse_fleet_risk,
)
from .fallback_model import FallbackGemini

# Each agent gets its OWN FallbackGemini instance - the model attribute
# gets mutated during retries, so sharing one instance across agents that
# might run near-concurrently would let them clobber each other's in-flight
# model choice. Cheap to construct, so one per agent is the safe default.
def new_model():
    return FallbackGemini()

nav_integrity_agent = Agent(
    model=new_model(),
    name="nav_integrity_agent",
    description="Checks GPS/radar/gyro/speed data for navigation integrity anomalies on a vessel.",
    instruction=(
        "You check navigation sensor agreement using the check_navigation_integrity tool. "
        "Never estimate distances or severities yourself - only report what the tool returns, "
        "in one clear sentence plus the key evidence."
    ),
    tools=[check_navigation_integrity],
)

crew_readiness_agent = Agent(
    model=new_model(),
    name="crew_readiness_agent",
    description="Assesses crew fatigue and readiness risk from watch-schedule data.",
    instruction=(
        "You assess crew readiness using the check_crew_readiness tool. "
        "Use only operational watch-schedule data provided to you - never speculate about "
        "individual crew members beyond what the tool reports."
    ),
    tools=[check_crew_readiness],
)

fleet_pattern_agent = Agent(
    model=new_model(),
    name="fleet_pattern_agent",
    description="Scans fleet-wide near-miss reports for recurring cross-vessel patterns.",
    instruction=(
        "You look for recurring patterns across the fleet using the check_fleet_patterns tool. "
        "Report only patterns the tool actually found - do not infer patterns from your own "
        "general knowledge of maritime incidents."
    ),
    tools=[check_fleet_patterns],
)

compliance_readiness_agent = Agent(
    model=new_model(),
    name="compliance_readiness_agent",
    description="Assesses compliance exposure by reasoning about certificate status against the vessel's schedule.",
    instruction=(
        "You assess compliance exposure using the check_compliance_readiness tool. "
        "Explain *why* a certificate timeline matters operationally (e.g. expiry before next "
        "port call), not just that a date is approaching."
    ),
    tools=[check_compliance_readiness],
)

root_agent = Agent(
    model=new_model(),
    name="fleet_conductor",
    description="Orchestrates fleet incident investigation across all specialist agents.",
    instruction=(
        "You are the Fleet Conductor for Manrova, an autonomous maritime fleet operations system. "
        "When a navigation anomaly is reported for a vessel: "
        "1) Delegate to nav_integrity_agent first if navigation data hasn't already been checked. "
        "2) Then gather context from crew_readiness_agent, fleet_pattern_agent, and "
        "compliance_readiness_agent - always consult all three before concluding, even if the "
        "navigation finding alone looks minor. "
        "3) Call fuse_fleet_risk with the four severities to get the overall assessment - never "
        "estimate overall severity yourself. "
        "4) If overall_severity is 'high' or 'critical', clearly state that external notifications "
        "(Master, DPA, Class Society) require human approval before anything is sent - you never "
        "claim to have sent a notification yourself. "
        "5) If overall_severity is 'none' or 'low', say monitoring continues and no notification "
        "is needed. "
        "Always show your reasoning: which specialists you consulted and what each found."
    ),
    tools=[fuse_fleet_risk],
    sub_agents=[
        nav_integrity_agent,
        crew_readiness_agent,
        fleet_pattern_agent,
        compliance_readiness_agent,
    ],
)
