"""Re-export so `adk run providers/google/adk` and `adk web` find root_agent
the way the ADK CLI expects (a module named agent.py exposing root_agent)."""

from .agents import root_agent  # noqa: F401
