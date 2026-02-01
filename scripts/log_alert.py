"""
Log a drug interaction alert to the interaction_alerts index.
Run: python scripts/log_alert.py --patient-id PT-4821 --new-drug Warfarin --conflicting-drug Aspirin --severity critical --mechanism "Both inhibit platelet function" --recommendation "Do not dispense" [--prescribing-doctor "Dr. Smith"]
"""
import argparse
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv

load_dotenv()

from elasticsearch import Elasticsearch

ES_ENDPOINT = os.getenv("ES_ENDPOINT")
ES_API_KEY = os.getenv("ES_API_KEY")

if not ES_ENDPOINT or not ES_API_KEY:
    print("Missing ES_ENDPOINT or ES_API_KEY in .env")
    sys.exit(1)

client = Elasticsearch(ES_ENDPOINT, api_key=ES_API_KEY)


def log_alert(patient_id: str, new_drug: str, conflicting_drug: str, severity: str, mechanism: str, recommendation: str, prescribing_doctor: str = None):
    alert_id = f"ALR-{uuid.uuid4().hex[:8].upper()}"
    doc = {
        "alert_id": alert_id,
        "patient_id": patient_id,
        "new_drug": new_drug,
        "conflicting_drug": conflicting_drug,
        "severity": severity,
        "mechanism": mechanism,
        "recommendation": recommendation,
        "status": "pending_review",
        "flagged_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "reviewed_by": None,
        "prescribing_doctor": prescribing_doctor,
    }
    client.index(index="interaction_alerts", id=alert_id, document=doc)
    return alert_id


def main():
    parser = argparse.ArgumentParser(description="Log drug interaction alert to interaction_alerts")
    parser.add_argument("--patient-id", required=True, help="Patient ID (e.g. PT-4821)")
    parser.add_argument("--new-drug", required=True, help="New drug being prescribed")
    parser.add_argument("--conflicting-drug", required=True, help="Existing drug that conflicts")
    parser.add_argument("--severity", required=True, choices=["critical", "moderate", "low"])
    parser.add_argument("--mechanism", required=True, help="Mechanism of interaction")
    parser.add_argument("--recommendation", required=True, help="Recommended action")
    parser.add_argument("--prescribing-doctor", help="Prescribing physician name or email (for targeted notifications)")
    args = parser.parse_args()

    alert_id = log_alert(
        patient_id=args.patient_id,
        new_drug=args.new_drug,
        conflicting_drug=args.conflicting_drug,
        severity=args.severity,
        mechanism=args.mechanism,
        recommendation=args.recommendation,
        prescribing_doctor=args.prescribing_doctor,
    )
    print(f"Alert logged: {alert_id} (status: pending_review)")


if __name__ == "__main__":
    main()
