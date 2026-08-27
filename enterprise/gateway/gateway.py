"""
Agent Gateway
===============
Unified routing and policy enforcement point, per the Fortified Enterprise
Fleet track requirement. Every tool call any agent makes passes through
here first - this is the single place that checks an agent is calling only
what it's permitted to (per the Agent Registry's `permissions` field)
before the call is allowed through, and logs every call for audit.

This is our own lightweight implementation of the pattern - not Google's
managed API Gateway product, which would sit in front of a deployed Cloud
Run service. In a production deployment, this module's policy-check logic
is what you'd port into an API Gateway config or a service mesh policy.
"""

from __future__ import annotations
from datetime import datetime, timezone
from enterprise.registry.seed_registry import AGENTS

_PERMISSIONS_BY_AGENT = {a["agent_id"]: set(a["permissions"]) for a in AGENTS}

_call_log: list[dict] = []


class GatewayDeniedError(Exception):
    """Raised when an agent attempts a call outside its registered permissions."""


def route_call(caller_agent_id: str, action: str, payload: dict | None = None) -> dict:
    """Every agent-to-agent or agent-to-tool call goes through here.

    Args:
        caller_agent_id: registry ID of the agent making the call, e.g.
            "officer-of-the-watch".
        action: the permission string being exercised, e.g.
            "invoke:nav-integrity-agent" or "read:vessel_telemetry".
        payload: optional call payload, logged for audit (not inspected here).

    Returns:
        A log entry dict describing the routed call.

    Raises:
        GatewayDeniedError: if the caller isn't registered, or the action
            isn't in that agent's granted permissions.
    """
    allowed = _PERMISSIONS_BY_AGENT.get(caller_agent_id)
    if allowed is None:
        raise GatewayDeniedError(f"Unknown agent '{caller_agent_id}' - not in registry.")
    if action not in allowed:
        raise GatewayDeniedError(
            f"Agent '{caller_agent_id}' is not permitted to perform '{action}'. "
            f"Granted: {sorted(allowed)}"
        )

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "caller": caller_agent_id,
        "action": action,
        "payload_keys": list(payload.keys()) if payload else [],
        "status": "allowed",
    }
    _call_log.append(entry)
    return entry


def get_call_log() -> list[dict]:
    """Returns the in-process audit log of all routed calls this run."""
    return list(_call_log)
