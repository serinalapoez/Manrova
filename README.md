# Manrova

**The autonomous command layer for fleet operations.**

Four agents watch. The Officer of the Watch acts. The fleet learns.

Manrova is an autonomous fleet operations agent for maritime organizations.
Four specialist agents continuously monitor navigation integrity, crew
readiness, fleet-wide near-miss patterns, and compliance readiness. A
central Officer of the Watch (OOW) correlates their findings, investigates emerging
incidents, gathers context, prepares evidence and response actions, and
tracks each incident through to resolution - only asking a human for
decisions that genuinely require human judgment.

This repo holds one shared product core, submitted to two hackathons with
provider-specific adapters:

- **Agents for Humans Hackathon** (AWS / Strands Agents SDK) - Professional
  Agents track
- **All Things Agentic Hackathon** (Google / Gemini + Google Cloud) -
  Fortified Enterprise Fleet track

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the full end-to-end demo scenario (Scene 1-9)
python3 -m apps.cli.demo_runner

# Run tests
pytest tests/ -q
```

## Repository layout

```
Manrova/
├── core/                   # domain models, state machine, risk fusion - shared
├── agents/                 # 4 specialist agents - deterministic tools + reasoning seam
├── oow/                     # Officer of the Watch - top-level orchestrator
├── data/demo/               # synthetic fleet + incident scenario data
├── apps/cli/                # runnable command-center demo (provider-agnostic)
├── providers/aws/strands/   # AWS/Strands-specific wiring (Agents for Humans)
├── providers/google/adk/    # Google/ADK + Cloud-specific wiring (All Things Agentic)
├── tests/                   # unit tests for state machine, risk fusion, workflow
└── docs/                    # architecture diagram + notes
```

## Design principle: deterministic tools + agentic reasoning

Safety-critical math (position deviation, risk scoring, state transitions)
is deterministic Python, not LLM output. Each specialist agent has a
"reasoning seam" - the point where a Strands or Gemini/ADK call plugs in to
interpret structured evidence and produce narrative output. See
`docs/architecture-overview.md` for the full diagram.

## Status

- [x] Shared core: domain models, incident state machine, risk fusion
- [x] Four specialist agents (deterministic logic, demo-ready)
- [x] Officer of the Watch orchestration, end-to-end incident workflow
- [x] Synthetic demo dataset (MV Atlas scenario) + CLI command-center demo
- [ ] AWS/Strands provider implementation (`providers/aws/strands/`)
- [x] Google/ADK agent wrappers + Cloud Run service (`providers/google/adk/`)
      - see that folder's README for what's left: local `adk web` test,
        actual Cloud Run deployment, and Fortified Enterprise Fleet extras
- [ ] Command-center web UI
- [ ] Agent Registry, Identity, Gateway, Observability (Fortified Enterprise
      Fleet track requirements)

## License

MIT - see [LICENSE](LICENSE).

## Note

This is a hackathon build using synthetic data throughout. It does not
connect to real vessel operational systems and makes no claim of
autonomous control over any vessel.
