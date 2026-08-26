# Google / ADK Provider

This is where the All Things Agentic (Fortified Enterprise Fleet track)
implementation lives, wrapping the same shared core.

## Plan

1. Wrap each specialist agent as a Google ADK agent, calling Gemini 3.5+
   via the Gemini API or Vertex AI for the reasoning step.
2. Wrap `FleetConductor` as the top-level ADK orchestrating agent.
3. Deploy on Cloud Run; use Pub/Sub for event ingestion instead of the
   direct function call `handle_telemetry()` uses in the demo.
4. Persist incidents/fleet memory in Firestore or Cloud SQL instead of
   in-memory `Incident` objects.
5. Fortified Enterprise Fleet track requirements, mapped to this repo:
   - Agent Registry -> `registry/` (Firestore-backed list of the 4 agents +
     Conductor, versioned, with owner/permissions metadata)
   - Agent Runtime -> Cloud Run services running the ADK agents
   - Memory Bank -> Firestore/Cloud SQL persistence layer
   - Agent Identity -> IAM service identities per agent, least-privilege
   - Agent Gateway -> authenticated API layer in front of all tool calls
   - Model Armor -> Google's guardrail layer (or equivalent) in front of
     agent inputs, since fleet reports are treated as untrusted text
   - Agent Observability -> Cloud Logging + Trace on every agent action

## Status

- [ ] ADK Agent wrapper for NavIntegrityAgent
- [ ] ADK Agent wrapper for CrewReadinessAgent
- [ ] ADK Agent wrapper for FleetPatternAgent
- [ ] ADK Agent wrapper for ComplianceReadinessAgent
- [ ] ADK orchestrating agent for FleetConductor
- [ ] Cloud Run deployment
- [ ] Agent Registry page
- [ ] Agent Identity / IAM mapping
- [ ] Agent Gateway
- [ ] Model Armor / guardrail layer
- [ ] Cloud Logging + Trace wiring
