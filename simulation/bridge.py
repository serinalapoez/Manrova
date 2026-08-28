from datetime import datetime

from core.domain.models import NavTelemetry
from oow.officer_of_the_watch import OfficerOfTheWatch


class SimulationBridge:
    def __init__(self):
        self.oow = OfficerOfTheWatch()
        self.incidents = []

    def process(self, telemetry):
        nav = telemetry["navigation"]

        nav_telemetry = NavTelemetry(
            vessel_id=telemetry["vessel_id"],
            gps_position=(
                nav["gps_position"]["lat"],
                nav["gps_position"]["lon"],
            ),
            radar_position=(
                nav["radar_position"]["lat"],
                nav["radar_position"]["lon"],
            ),
            gyro_heading=nav["heading_deg"],
            speed_knots=nav["speed_kn"],
            timestamp=datetime.utcnow(),
        )

        fleet_context = {
            "crew_record": {
                "rest_hours_last_24": 8 if telemetry["crew"]["readiness"] >= 70 else 5,
                "continuous_duty_hours": 8 if telemetry["crew"]["readiness"] >= 70 else 12,
                "unusual_rotation": telemetry["crew"]["readiness"] < 70,
                "role": "watch team",
            },
            "near_miss_reports": [],
            "compliance_record": {
                "radio_cert_expires_in_days": 180,
                "next_port_call_in_days": 14,
                "previous_navigation_deficiency": False,
            },
        }

        incident = self.oow.handle_telemetry(
            nav_telemetry,
            fleet_context,
        )

        if incident:
            self.incidents.append(incident)

        return incident
