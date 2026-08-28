from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .engine import SimulationEngine
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from simulation.bridge import SimulationBridge

app = FastAPI(title="Manrova Simulation Environment")
engine = SimulationEngine()
bridge = SimulationBridge()
app.mount("/static", StaticFiles(directory="static"), name="static")

class SpeedRequest(BaseModel):
    multiplier: float

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.get("/api/state")
def state():
    return engine.state.public_dict()

@app.get("/api/telemetry")
def telemetry():
    return engine.telemetry()

@app.get("/api/events")
def events():
    return [e.__dict__ for e in engine.state.events[-80:]]

@app.post("/api/simulation/start")
def start():
    engine.start()
    return {"ok": True}

@app.post("/api/simulation/pause")
def pause():
    engine.pause()
    return {"ok": True}

@app.post("/api/simulation/reset")
def reset():
    engine.reset()
    return {"ok": True}

@app.post("/api/simulation/process")
def process_simulation():
    telemetry = engine.telemetry()
    incident = bridge.process(telemetry)

    if incident is None:
        return {
            "incident": None,
            "message": "No incident detected"
        }

    return {
        "incident_id": incident.incident_id,
        "state": incident.state.value,
        "risk": incident.risk.overall_severity.value if incident.risk else "none",
        "timeline": [
            {
                "actor": entry.actor,
                "description": entry.description,
            }
            for entry in incident.timeline
        ],
    }

@app.post("/api/simulation/speed")
def speed(req: SpeedRequest):
    engine.set_speed(req.multiplier)
    return {"ok": True, "speed_multiplier": engine.state.speed_multiplier}

@app.post("/api/scenarios/{scenario}")
def scenario(scenario: str):
    try:
        engine.inject(scenario)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return engine.state.public_dict()
