# AWS / Strands Provider

This is where the Agents for Humans (Strands Agents SDK) implementation
lives. It wraps the shared core in `core/`, `agents/`, and `conductor/` -
it does not reimplement business logic.

## Plan

1. Wrap each specialist agent class (`agents/*/agent.py`) as a Strands Tool,
   keeping the deterministic `.analyze()` / `.assess()` methods as the tool
   function and adding a Strands `Agent` on top for the reasoning step.
2. Wrap `FleetConductor` as the top-level Strands orchestrating agent.
3. Deploy via AWS AgentCore Runtime (optional but strengthens the
   Technological Implementation score per the judging criteria).
4. Swap `data/demo/fleet_data.py` for a real event source (e.g. an
   EventBridge rule or a simple ingestion Lambda) when moving past the demo.

## Status

- [ ] Strands Agent wrapper for NavIntegrityAgent
- [ ] Strands Agent wrapper for CrewReadinessAgent
- [ ] Strands Agent wrapper for FleetPatternAgent
- [ ] Strands Agent wrapper for ComplianceReadinessAgent
- [ ] Strands orchestrating agent for FleetConductor
- [ ] AgentCore Runtime deployment
- [ ] AWS Builder ID attached to submission
