"""
Queue a drug interaction alert for cron processing.
Run: python scripts/queue_alert.py --patient-id PT-4821 --new-drug Warfarin --conflicting-drug Aspirin --severity critical --mechanism "..." --recommendation "..." [--prescribing-doctor "Dr. Smith"]

The GitHub Actions cron (every 5 min) will pick up pending requests and log them to interaction_alerts.
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


def queue_alert(patient_id: str, new_drug: str, conflicting_drug: str, severity: str, mechanism: str, recommendation: str, prescribing_doctor: str = None):
    request_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
    doc = {
        "request_id": request_id,
        "patient_id": patient_id,
        "new_drug": new_drug,
        "conflicting_drug": conflicting_drug,
        "severity": severity,
        "mechanism": mechanism,
        "recommendation": recommendation,
        "prescribing_doctor": prescribing_doctor or "",
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    client.index(index="pharmasafe_alert_requests", id=request_id, document=doc)
    return request_id


def main():
    parser = argparse.ArgumentParser(description="Queue alert for cron processing")
    parser.add_argument("--patient-id", required=True)
    parser.add_argument("--new-drug", required=True)
    parser.add_argument("--conflicting-drug", required=True)
    parser.add_argument("--severity", required=True, choices=["critical", "moderate", "low"])
    parser.add_argument("--mechanism", required=True)
    parser.add_argument("--recommendation", required=True)
    parser.add_argument("--prescribing-doctor", default="")
    args = parser.parse_args()

    req_id = queue_alert(
        patient_id=args.patient_id,
        new_drug=args.new_drug,
        conflicting_drug=args.conflicting_drug,
        severity=args.severity,
        mechanism=args.mechanism,
        recommendation=args.recommendation,
        prescribing_doctor=args.prescribing_doctor or None,
    )
    print(f"Queued: {req_id} (status: pending). Cron will process within ~5 min.")


if __name__ == "__main__":
    main()
