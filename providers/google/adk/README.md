# Google / ADK Provider

This is where the All Things Agentic (Fortified Enterprise Fleet track)
implementation lives, wrapping the same shared core.

## What's here

- `tools.py` - plain functions ADK calls as tools, each wrapping one
  deterministic core agent. Math/scoring never happens in the LLM layer.
- `agents.py` - four specialist `Agent`s (one tool each) plus `root_agent`
  ("officer_of_the_watch"), an orchestrating agent with all four as `sub_agents`.
- `agent.py` / `__init__.py` - re-exports so `adk run` / `adk web` find
  `root_agent` the way the ADK CLI expects.
- `main.py` - FastAPI service for Cloud Run: `/telemetry` runs the
  deterministic fast path directly (no LLM call on every tick), `/approve`
  executes pending actions once a human signs off.
- `Dockerfile` - Cloud Run image, built from repo root.

## Run it locally

```bash
cd Manrova
pip install -r providers/google/adk/requirements-google.txt
cp providers/google/adk/.env.example providers/google/adk/.env
# edit .env with a real Gemini API key from Google AI Studio

export GOOGLE_API_KEY=$(grep GOOGLE_API_KEY providers/google/adk/.env | cut -d= -f2)
adk web providers/google/adk        # browser dev UI, or:
adk run providers/google/adk        # terminal chat
```

Try: *"MV Atlas is reporting GPS at 1.290,103.850 and radar at
1.305,103.862, gyro 178.4, speed 12.1 knots - investigate."* The Officer of the Watch
should delegate to nav_integrity_agent, then the other three specialists,
then call `fuse_fleet_risk`, and tell you human approval is needed before
any notification goes out.

## Deploy to Cloud Run

```bash
gcloud run deploy manrova \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

(Uses `providers/google/adk/Dockerfile` if you point `--source` at the repo
root; `gcloud` will pick it up via `cloudbuild.yaml` or you can build/push
manually with `docker build -f providers/google/adk/Dockerfile`.)

## Note on the ADK import path

`google-adk` moves fast - as of mid-2026 the working import is
`from google.adk.agents.llm_agent import Agent` (also re-exported as
`from google.adk import Agent`). If a `pip install google-adk` in your
Codespace pulls a version where that import fails, check
`google.github.io/adk-docs` for the current path and update `agents.py`
accordingly - the rest of the code doesn't need to change.

## Plan

1. Wrap each specialist agent as a Google ADK agent, calling Gemini 3.5+
   via the Gemini API or Vertex AI for the reasoning step.
2. Wrap `OfficerOfTheWatch` as the top-level ADK orchestrating agent.
3. Deploy on Cloud Run; use Pub/Sub for event ingestion instead of the
   direct function call `handle_telemetry()` uses in the demo.
4. Persist incidents/fleet memory in Firestore or Cloud SQL instead of
   in-memory `Incident` objects.
5. Fortified Enterprise Fleet track requirements, mapped to this repo:
   - Agent Registry -> `registry/` (Firestore-backed list of the 4 agents +
     Officer of the Watch, versioned, with owner/permissions metadata)
   - Agent Runtime -> Cloud Run services running the ADK agents
   - Memory Bank -> Firestore/Cloud SQL persistence layer
   - Agent Identity -> IAM service identities per agent, least-privilege
   - Agent Gateway -> authenticated API layer in front of all tool calls
   - Model Armor -> Google's guardrail layer (or equivalent) in front of
     agent inputs, since fleet reports are treated as untrusted text
   - Agent Observability -> Cloud Logging + Trace on every agent action

## Status

- [x] ADK Agent wrapper for NavIntegrityAgent
- [x] ADK Agent wrapper for CrewReadinessAgent
- [x] ADK Agent wrapper for FleetPatternAgent
- [x] ADK Agent wrapper for ComplianceReadinessAgent
- [x] ADK orchestrating agent for Officer of the Watch (`root_agent` in `agents.py`)
- [x] FastAPI service + Dockerfile for Cloud Run (`main.py`) - not yet deployed
- [ ] Actually run `adk web` locally and confirm the model follows the
      "consult all four before fusing risk" instruction reliably
- [ ] Deploy to Cloud Run and get a live URL for the submission
- [ ] Agent Registry page
- [ ] Agent Identity / IAM mapping
- [ ] Agent Gateway
- [ ] Model Armor / guardrail layer
- [ ] Cloud Logging + Trace wiring
- [ ] Swap in-memory `_incident_store` in `main.py` for Firestore/Cloud SQL
