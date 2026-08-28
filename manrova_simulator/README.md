# Manrova Simulation Environment

A standalone, synthetic maritime simulation layer designed to sit beside the Manrova command-center application.

## What it does

- Runs a deterministic simulation clock.
- Simulates vessels, navigation, weather, traffic, engine health, fuel and crew readiness.
- Streams telemetry through a REST endpoint.
- Injects incidents such as GPS/radar disagreement, engine degradation, poor visibility, route deviation and near-miss risk.
- Produces deterministic risk signals that can be consumed by Manrova's existing specialist agents/OOW.
- Includes a browser UI with a live tactical map, telemetry cards, risk gauge, event timeline and scenario controls.

This simulator intentionally uses synthetic data and does not connect to real vessel operational systems.

## Run

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## Useful API endpoints

- `GET /api/state`
- `POST /api/simulation/start`
- `POST /api/simulation/pause`
- `POST /api/simulation/reset`
- `POST /api/simulation/speed`
- `POST /api/scenarios/{scenario}`
- `GET /api/telemetry`
- `GET /api/events`

Available scenarios:

- `gps_radar_disagreement`
- `engine_degradation`
- `poor_visibility`
- `route_deviation`
- `near_miss`
- `crew_fatigue`
- `compound_incident`

## Manrova integration seam

The simulator's `/api/telemetry` response is deliberately structured as an evidence packet. The existing Manrova navigation/crew/compliance/near-miss agents can consume this packet instead of reading a static demo dataset.

Recommended next integration:

`SimulationEngine -> telemetry packet -> Manrova specialist agents -> OOW -> incident state machine -> UI`

