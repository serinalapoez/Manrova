"""
Strands Agents
================
Wires the deterministic core into a Strands multi-agent system using the
"agents as tools" pattern: each specialist is its own Strands Agent with one
tool, then wrapped as a @tool the Officer of the Watch agent can call. This
mirrors providers/google/adk/agents.py's sub_agents composition, adapted to
Strands' idiom.

Run locally:
    python providers/aws/strands/agents.py

Requires:
    pip install -r providers/aws/strands/requirements-aws.txt
    AWS credentials configured with Bedrock model access for Claude
    (default provider - see strandsagents.com/docs for other providers)
"""

from strands import Agent, tool

from .tools import (
    check_navigation_integrity,
    check_crew_readiness,
    check_fleet_patterns,
    check_compliance_readiness,
    fuse_fleet_risk,
)

# --- Specialist agents: narrow, single-tool, cannot freelance beyond what
# their one tool exposes. ---

nav_integrity_agent = Agent(
    tools=[check_navigation_integrity],
    system_prompt=(
        "You check navigation sensor agreement using the check_navigation_integrity tool. "
        "Never estimate distances or severities yourself - only report what the tool returns, "
        "in one clear sentence plus the key evidence."
    ),
)

crew_readiness_agent = Agent(
    tools=[check_crew_readiness],
    system_prompt=(
        "You assess crew readiness using the check_crew_readiness tool. "
        "Use only operational watch-schedule data provided to you - never speculate about "
        "individual crew members beyond what the tool reports."
    ),
)

fleet_pattern_agent = Agent(
    tools=[check_fleet_patterns],
    system_prompt=(
        "You look for recurring patterns across the fleet using the check_fleet_patterns tool. "
        "Report only patterns the tool actually found - do not infer patterns from your own "
        "general knowledge of maritime incidents."
    ),
)

compliance_readiness_agent = Agent(
    tools=[check_compliance_readiness],
    system_prompt=(
        "You assess compliance exposure using the check_compliance_readiness tool. "
        "Explain *why* a certificate timeline matters operationally (e.g. expiry before next "
        "port call), not just that a date is approaching."
    ),
)


# --- Wrap each specialist agent as a tool the Officer of the Watch can call. This is
# Strands' documented "agents as tools" pattern for multi-agent systems. ---

@tool
def consult_nav_integrity(query: str) -> str:
    """Consult the Navigation Integrity specialist about a vessel's sensor
    data. Pass the vessel ID and its GPS/radar/gyro/speed readings in the
    query text.
    """
    return str(nav_integrity_agent(query))


@tool
def consult_crew_readiness(query: str) -> str:
    """Consult the Crew Readiness specialist about a vessel's watch-schedule
    and fatigue data. Pass the vessel ID and rest/duty-hours data in the
    query text.
    """
    return str(crew_readiness_agent(query))


@tool
def consult_fleet_pattern(query: str) -> str:
    """Consult the Fleet Pattern specialist for recurring cross-vessel
    near-miss patterns relevant to the vessel under investigation.
    """
    return str(fleet_pattern_agent(query))


@tool
def consult_compliance_readiness(query: str) -> str:
    """Consult the Compliance Readiness specialist about a vessel's
    certificate and deficiency status relative to its schedule.
    """
    return str(compliance_readiness_agent(query))


# --- Officer of the Watch (OOW): the root orchestrating agent. ---

officer_of_the_watch = Agent(
    tools=[
        consult_nav_integrity,
        consult_crew_readiness,
        consult_fleet_pattern,
        consult_compliance_readiness,
        fuse_fleet_risk,
    ],
    system_prompt=(
        "You are the Officer of the Watch for Manrova, an autonomous maritime fleet operations system. "
        "When a navigation anomaly is reported for a vessel: "
        "1) Consult the navigation integrity specialist first if navigation data hasn't already "
        "been checked. "
        "2) Then gather context from the crew readiness, fleet pattern, and compliance readiness "
        "specialists - always consult all three before concluding, even if the navigation finding "
        "alone looks minor. "
        "3) Call fuse_fleet_risk with the four severities to get the overall assessment - never "
        "estimate overall severity yourself. "
        "4) If overall_severity is 'high' or 'critical', clearly state that external notifications "
        "(Master, DPA, Class Society) require human approval before anything is sent - you never "
        "claim to have sent a notification yourself. "
        "5) If overall_severity is 'none' or 'low', say monitoring continues and no notification "
        "is needed. "
        "Always show your reasoning: which specialists you consulted and what each found."
    ),
)


if __name__ == "__main__":
    # Quick local smoke test - mirrors the MV Atlas demo scenario.
    result = officer_of_the_watch(
        "MV Atlas (V-001) is reporting GPS at 1.290,103.850 and radar at "
        "1.305,103.862, gyro heading 178.4, speed 12.1 knots - investigate this."
    )
    print(result)
