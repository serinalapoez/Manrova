
## Background Watch (continuous autonomous monitoring)

`background_watch.py` proves Manrova can run continuously in the
background rather than only on demand from a click or command - it polls
the running simulator server on an interval and stays silent unless the
Officer of the Watch actually flags something worth a human's attention.

```bash
# Terminal 1: start the simulator server
cd manrova_simulator
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 2: start the background watcher (from the repo root)
python manrova_simulator/background_watch.py
```

It prints a quiet heartbeat every few seconds. In a third terminal (or
your browser), inject a scenario to see it react:

```bash
python manrova_simulator/background_watch.py --inject gps_radar_disagreement
```

Within one polling cycle, the watcher prints the full incident: severity,
state, the relevant timeline entries, and a clear statement that no
external notification was sent without human approval.

Note: the injected anomaly persists in the simulated telemetry until the
scenario is reset, so the watcher will keep re-reporting the same incident
on every poll until you either reset the simulation or stop the watcher
(`Ctrl+C`). For a clean recording, stop it shortly after the first
detection rather than let it repeat.

Available scenarios: `gps_radar_disagreement`, `engine_degradation`,
`poor_visibility`, `route_deviation`, `near_miss`, `crew_fatigue`,
`compound_incident`.
