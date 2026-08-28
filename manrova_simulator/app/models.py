from dataclasses import dataclass, field, asdict
from typing import Dict, List
import math

@dataclass
class Vessel:
    vessel_id: str
    name: str
    vessel_class: str
    lat: float
    lon: float
    heading: float = 90.0
    speed_kn: float = 12.0
    engine_health: float = 100.0
    fuel_pct: float = 78.0
    crew_readiness: float = 96.0
    gps_lat: float = 0.0
    gps_lon: float = 0.0
    radar_lat: float = 0.0
    radar_lon: float = 0.0
    route_deviation_nm: float = 0.0
    ais_ok: bool = True
    nav_integrity: float = 100.0
    risk: float = 8.0

    def __post_init__(self):
        self.gps_lat = self.lat
        self.gps_lon = self.lon
        self.radar_lat = self.lat
        self.radar_lon = self.lon

@dataclass
class Environment:
    visibility_nm: float = 8.0
    wind_kn: float = 14.0
    sea_state: float = 2.0
    traffic_density: float = 0.55
    current_kn: float = 1.2

@dataclass
class SimEvent:
    sim_minute: float
    severity: str
    title: str
    detail: str

@dataclass
class SimulationState:
    running: bool = False
    speed_multiplier: float = 10.0
    sim_minute: float = 0.0
    environment: Environment = field(default_factory=Environment)
    vessels: Dict[str, Vessel] = field(default_factory=dict)
    events: List[SimEvent] = field(default_factory=list)
    active_scenarios: List[str] = field(default_factory=list)

    def public_dict(self):
        return {
            "running": self.running,
            "speed_multiplier": self.speed_multiplier,
            "sim_minute": round(self.sim_minute, 1),
            "environment": asdict(self.environment),
            "vessels": {k: asdict(v) for k, v in self.vessels.items()},
            "events": [asdict(e) for e in self.events[-80:]],
            "active_scenarios": self.active_scenarios,
        }
