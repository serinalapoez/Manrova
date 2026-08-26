"""
Synthetic demo fleet data. Not real vessel data - purpose-built for the
hackathon demo scenario described in the build spec (Section 30).
"""

from core.domain.models import Vessel, NavTelemetry

FLEET: list[Vessel] = [Vessel(f"V-{i:03d}", f"Vessel {i}", "bulk-carrier") for i in range(1, 25)]
FLEET[0] = Vessel("V-001", "MV Atlas", "bulk-carrier", status="normal")

HERO_VESSEL_ID = "V-001"

# Scene 2: GPS/radar disagreement on MV Atlas
HERO_TELEMETRY = NavTelemetry(
    vessel_id=HERO_VESSEL_ID,
    gps_position=(1.2900, 103.8500),      # reported GPS fix
    radar_position=(1.3050, 103.8620),    # radar-derived position, ~2.1km off
    gyro_heading=178.4,
    speed_knots=12.1,
)

CREW_RECORD = {
    "role": "Chief Officer",
    "rest_hours_last_24": 4.5,
    "continuous_duty_hours": 13,
    "unusual_rotation": True,
}

COMPLIANCE_RECORD = {
    "radio_cert_expires_in_days": 18,
    "next_port_call_in_days": 11,
    "previous_navigation_deficiency": True,
}

NEAR_MISS_REPORTS = [
    {"vessel_id": "V-004", "description": "steering hesitation reported during night watch"},
    {"vessel_id": "V-011", "description": "rudder response delayed by several seconds"},
    {"vessel_id": "V-017", "description": "intermittent steering response near port approach"},
]

FLEET_OVERVIEW = {
    "total": 24,
    "normal": 21,
    "monitoring": 2,
    "incident": 1,
}
