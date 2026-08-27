"""
Manrova Command Center - CLI Demo
====================================
Runs the exact "winning demo scenario" described in the build spec (Section
30), Scene 1 through Scene 9, end to end, using the shared core - no cloud
provider required. This is what you record for the hackathon demo video
before/alongside the AWS or Google-specific deployment.

Run with:  python -m apps.cli.demo_runner
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from data.demo.fleet_data import (
    FLEET_OVERVIEW, HERO_TELEMETRY, CREW_RECORD, COMPLIANCE_RECORD,
    NEAR_MISS_REPORTS, HERO_VESSEL_ID,
)
from oow.officer_of_the_watch import OfficerOfTheWatch


def line(char="-", n=60):
    print(char * n)


def scene1_normal_ops():
    print("\nSCENE 1 - Normal operations")
    line()
    print(f"MANROVA  |  {FLEET_OVERVIEW['total']} VESSELS")
    print(f"  {FLEET_OVERVIEW['normal']}  NORMAL")
    print(f"  {FLEET_OVERVIEW['monitoring']}  MONITORING")
    print(f"  {FLEET_OVERVIEW['incident']}  INCIDENT")
    print("Manrova is running quietly. No human notification required.")


def main():
    scene1_normal_ops()

    print("\nSCENE 2 - Navigation event")
    line()
    print(f"Telemetry tick received for {HERO_VESSEL_ID} (MV Atlas). GPS and radar disagree.")

    oow = OfficerOfTheWatch()
    fleet_context = {
        "crew_record": CREW_RECORD,
        "near_miss_reports": NEAR_MISS_REPORTS,
        "compliance_record": COMPLIANCE_RECORD,
    }

    incident = oow.handle_telemetry(HERO_TELEMETRY, fleet_context)

    if incident is None:
        print("No anomaly above threshold. Manrova remains silent.")
        return

    print("\nSCENE 3-6 - Officer of the Watch activates, gathers context, fuses risk, does the work")
    line()
    for entry in incident.timeline:
        print(f"{entry.timestamp.strftime('%H:%M:%S')}  {entry.actor:<24} {entry.description}")

    print("\nSCENE 5 detail - Risk fusion")
    line()
    r = incident.risk
    print(f"Navigation risk:        {r.nav_risk.value.upper()}")
    print(f"Crew readiness risk:    {r.crew_risk.value.upper()}")
    print(f"Historical similarity:  {r.historical_similarity.value.upper()}")
    print(f"Compliance exposure:    {r.compliance_exposure.value.upper()}")
    print(f"Overall severity:       {r.overall_severity.value.upper()}  ({r.confidence:.0%} confidence)")
    print("Why this was escalated:")
    for reason in r.explanation:
        print(f"  \u2713 {reason}")

    print("\nSCENE 7 - Human decision")
    line()
    pending = [a for a in incident.actions if a.requires_approval]
    print(f"{len(pending)} action(s) require approval:")
    for a in pending:
        print(f"  [ REVIEW ]  [ APPROVE & SEND ]   {a.description}")

    print("\n(simulating human approval by DPA)")
    oow.approve_and_execute(incident, approver="DPA")

    print("\nSCENE 8-9 - Follow-through and fleet learning")
    line()
    for entry in incident.timeline[-8:]:
        print(f"{entry.timestamp.strftime('%H:%M:%S')}  {entry.actor:<24} {entry.description}")

    print("\nIncident resolved:", incident.resolved)
    print("Final state:", incident.state.value)


if __name__ == "__main__":
    main()
