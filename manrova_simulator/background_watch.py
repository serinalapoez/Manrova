"""
Manrova Background Watch
===========================
Genuine continuous autonomous monitoring: polls the running simulator
server at a fixed interval and stays silent unless the Officer of the
Watch actually flags something. This is what proves Manrova operates in
the background while a human does something else, rather than only ever
running on demand from a click or a command.

Talks to the FastAPI simulator server (manrova_simulator/app/main.py)
over its existing HTTP endpoints only - it does not import the engine
directly, so it works regardless of the engine's internal implementation.

Setup (two terminals):
    Terminal 1: cd manrova_simulator && uvicorn app.main:app --reload
    Terminal 2: python background_watch.py

While it's running, trigger a scenario from a third terminal (or your
browser) to see it react:
    python background_watch.py --inject gps_radar_disagreement

Available scenarios (from manrova_simulator/README.md):
    gps_radar_disagreement, engine_degradation, poor_visibility,
    route_deviation, near_miss, crew_fatigue, compound_incident
"""

import sys
import time
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime

DEFAULT_HOST = "http://127.0.0.1:8000"
POLL_INTERVAL_SECONDS = 5


def _post(host: str, path: str) -> dict:
    req = urllib.request.Request(f"{host}{path}", method="POST", data=b"{}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def inject_scenario(host: str, scenario: str) -> None:
    try:
        result = _post(host, f"/api/scenarios/{scenario}")
        print(f"[{_timestamp()}] Injected scenario '{scenario}'.")
    except urllib.error.HTTPError as e:
        print(f"[{_timestamp()}] Could not inject '{scenario}': {e.code} {e.reason}")
    except urllib.error.URLError:
        print(f"[{_timestamp()}] Could not reach the simulator at {host}. "
              f"Is 'uvicorn app.main:app' running?")


def watch(host: str, interval: int) -> None:
    print(f"[{_timestamp()}] Manrova background watch started.")
    print(f"[{_timestamp()}] Polling every {interval}s. Silent unless something needs your attention.")
    print(f"[{_timestamp()}] Starting the simulation clock...")

    try:
        _post(host, "/api/simulation/start")
    except urllib.error.URLError:
        print(f"[{_timestamp()}] Could not reach the simulator at {host}. "
              f"Start it first: cd manrova_simulator && uvicorn app.main:app --reload")
        sys.exit(1)

    tick = 0
    try:
        while True:
            time.sleep(interval)
            tick += 1
            try:
                result = _post(host, "/api/simulation/process")
            except urllib.error.URLError:
                print(f"[{_timestamp()}] Lost connection to the simulator. Retrying...")
                continue

            incident_id = result.get("incident_id")
            if not incident_id:
                # Deliberately quiet - this is the point. Nothing worth a
                # human's attention, so nothing is printed beyond a heartbeat.
                print(f"[{_timestamp()}] .", end="\r" if tick % 6 != 0 else "\n", flush=True)
                continue

            print()  # clear the heartbeat line
            print(f"[{_timestamp()}] " + "=" * 50)
            print(f"[{_timestamp()}] INCIDENT DETECTED - {incident_id}")
            print(f"[{_timestamp()}] Severity: {result.get('risk', 'unknown')}")
            print(f"[{_timestamp()}] State: {result.get('state', 'unknown')}")
            for entry in result.get("timeline", [])[-6:]:
                print(f"           {entry.get('actor', '?'):<24} {entry.get('description', '')}")
            print(f"[{_timestamp()}] No external notification sent without human approval.")
            print(f"[{_timestamp()}] " + "=" * 50)
            print(f"[{_timestamp()}] Resuming background watch...")
    except KeyboardInterrupt:
        print(f"\n[{_timestamp()}] Background watch stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manrova background monitoring watcher.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Simulator server URL")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL_SECONDS, help="Seconds between checks")
    parser.add_argument("--inject", metavar="SCENARIO", help="Inject a scenario and exit (run in a separate terminal)")
    args = parser.parse_args()

    if args.inject:
        inject_scenario(args.host, args.inject)
    else:
        watch(args.host, args.interval)
