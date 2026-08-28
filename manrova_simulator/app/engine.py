import random
import threading
import time
from .models import SimulationState, Vessel, SimEvent

class SimulationEngine:
    def __init__(self):
        self.state = SimulationState()
        self.state.vessels["V-001"] = Vessel(
            "V-001", "MV Atlas", "bulk carrier",
            1.235, 103.810, heading=82, speed_kn=12.4
        )
        self.state.vessels["V-002"] = Vessel(
            "V-002", "MV Meridian", "container ship",
            1.245, 103.825, heading=258, speed_kn=10.8
        )
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def start(self):
        with self._lock:
            self.state.running = True
            self._event("INFO", "Simulation started", "Synthetic fleet clock is running.")

    def pause(self):
        with self._lock:
            self.state.running = False
            self._event("INFO", "Simulation paused", "Clock frozen; scenario state preserved.")

    def reset(self):
        with self._lock:
            self.state = SimulationState()
            self.state.vessels["V-001"] = Vessel("V-001", "MV Atlas", "bulk carrier", 1.235, 103.810, 82, 12.4)
            self.state.vessels["V-002"] = Vessel("V-002", "MV Meridian", "container ship", 1.245, 103.825, 258, 10.8)
            self._event("INFO", "Simulation reset", "All synthetic telemetry returned to baseline.")

    def set_speed(self, multiplier):
        with self._lock:
            self.state.speed_multiplier = max(0.25, min(float(multiplier), 100))
            self._event("INFO", "Clock speed changed", f"Simulation speed set to {self.state.speed_multiplier:g}x.")

    def inject(self, scenario):
        with self._lock:
            scenarios = {
                "gps_radar_disagreement": self._gps_radar,
                "engine_degradation": self._engine,
                "poor_visibility": self._visibility,
                "route_deviation": self._route,
                "near_miss": self._near_miss,
                "crew_fatigue": self._fatigue,
                "compound_incident": self._compound,
            }
            fn = scenarios.get(scenario)
            if not fn:
                raise ValueError("Unknown scenario")
            fn()
            if scenario not in self.state.active_scenarios:
                self.state.active_scenarios.append(scenario)

    def telemetry(self):
        with self._lock:
            atlas = self.state.vessels["V-001"]
            return {
                "timestamp_sim_minute": round(self.state.sim_minute, 1),
                "vessel_id": atlas.vessel_id,
                "vessel": atlas.name,
                "navigation": {
                    "position": {"lat": atlas.lat, "lon": atlas.lon},
                    "gps_position": {"lat": atlas.gps_lat, "lon": atlas.gps_lon},
                    "radar_position": {"lat": atlas.radar_lat, "lon": atlas.radar_lon},
                    "heading_deg": atlas.heading,
                    "speed_kn": atlas.speed_kn,
                    "route_deviation_nm": round(atlas.route_deviation_nm, 3),
                    "ais_ok": atlas.ais_ok,
                    "nav_integrity": round(atlas.nav_integrity, 1),
                },
                "engineering": {
                    "engine_health": round(atlas.engine_health, 1),
                    "fuel_pct": round(atlas.fuel_pct, 1),
                },
                "crew": {"readiness": round(atlas.crew_readiness, 1)},
                "environment": self.state.environment.__dict__,
                "risk": round(atlas.risk, 1),
            }

    def _loop(self):
        last = time.time()
        while True:
            time.sleep(0.1)
            now = time.time()
            dt = now - last
            last = now
            with self._lock:
                if not self.state.running:
                    continue
                # One real second = 1 simulated minute at 1x.
                self._tick(dt * self.state.speed_multiplier)

    def _tick(self, sim_minutes):
        self.state.sim_minute += sim_minutes
        env = self.state.environment

        # Slow environmental drift.
        env.wind_kn = max(4, min(42, env.wind_kn + random.uniform(-0.15, 0.15) * sim_minutes))
        env.current_kn = max(0.1, min(3.5, env.current_kn + random.uniform(-0.03, 0.03) * sim_minutes))

        for vessel in self.state.vessels.values():
            vessel.fuel_pct = max(0, vessel.fuel_pct - 0.002 * vessel.speed_kn * sim_minutes)
            vessel.lat += (vessel.speed_kn * sim_minutes / 60 / 60) * 0.00035
            vessel.lon += (vessel.speed_kn * sim_minutes / 60 / 60) * 0.0007
            vessel.gps_lat = vessel.lat
            vessel.gps_lon = vessel.lon
            vessel.radar_lat = vessel.lat
            vessel.radar_lon = vessel.lon

        self._recompute_risk()

    def _recompute_risk(self):
        env = self.state.environment
        for v in self.state.vessels.values():
            risk = 8.0
            risk += max(0, (4 - env.visibility_nm) * 5)
            risk += max(0, (v.route_deviation_nm - 0.3) * 15)
            risk += max(0, (85 - v.engine_health) * 0.3)
            risk += max(0, (85 - v.crew_readiness) * 0.35)
            risk += max(0, (v.nav_integrity - 100) * -0.1)
            if not v.ais_ok:
                risk += 12
            if abs(v.gps_lat - v.radar_lat) + abs(v.gps_lon - v.radar_lon) > 0.003:
                risk += 32
            risk += max(0, (env.traffic_density - 0.65) * 35)
            v.risk = max(0, min(100, risk))

    def _event(self, severity, title, detail):
        self.state.events.append(SimEvent(round(self.state.sim_minute, 1), severity, title, detail))

    def _gps_radar(self):
        v = self.state.vessels["V-001"]
        v.gps_lat += 0.012
        v.gps_lon -= 0.016
        v.nav_integrity = 61
        self._event("HIGH", "GPS / radar disagreement", "Atlas GPS position diverged from radar track. Navigation agent should correlate independent evidence.")

    def _engine(self):
        v = self.state.vessels["V-001"]
        v.engine_health = 58
        v.speed_kn = 8.2
        self._event("HIGH", "Engine degradation", "Propulsion health fell below the watch threshold; speed reduced in the synthetic model.")

    def _visibility(self):
        self.state.environment.visibility_nm = 1.8
        self.state.environment.sea_state = 4.0
        self._event("MEDIUM", "Visibility deterioration", "Synthetic visibility dropped to 1.8 NM and sea state increased.")

    def _route(self):
        v = self.state.vessels["V-001"]
        v.route_deviation_nm = 1.6
        v.heading += 14
        self._event("MEDIUM", "Route deviation", "Atlas is 1.6 NM off its nominal route corridor.")

    def _near_miss(self):
        self.state.environment.traffic_density = 0.92
        self.state.vessels["V-002"].lat = 1.236
        self.state.vessels["V-002"].lon = 103.812
        self.state.vessels["V-002"].speed_kn = 13.8
        self.state.vessels["V-001"].speed_kn = 13.2
        self._event("CRITICAL", "Near-miss developing", "Traffic density and relative geometry indicate a high-risk encounter for the synthetic scenario.")

    def _fatigue(self):
        v = self.state.vessels["V-001"]
        v.crew_readiness = 54
        self._event("MEDIUM", "Crew readiness degradation", "Synthetic watch-team readiness dropped to 54%.")

    def _compound(self):
        self._gps_radar()
        self._visibility()
        self._route()
        self._fatigue()
        self._near_miss()
        self._event("CRITICAL", "Compound incident", "Multiple independent weak signals now overlap; OOW correlation is required.")
