"""
Update the status of an interaction alert.
Run: python scripts/update_alert_status.py --alert-id ALR-XXXXXXXX --status reviewed --reviewed-by "Dr. Smith"
"""
import argparse
import os
import sys
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


def main():
    parser = argparse.ArgumentParser(description="Update interaction alert status")
    parser.add_argument("--alert-id", required=True, help="Alert ID (e.g. ALR-XXXXXXXX)")
    parser.add_argument("--status", required=True, choices=["pending_review", "acknowledged", "reviewed", "dispensed_anyway", "blocked"])
    parser.add_argument("--reviewed-by", help="Pharmacist/doctor who reviewed")
    args = parser.parse_args()

    try:
        doc = client.get(index="interaction_alerts", id=args.alert_id)
    except Exception as e:
        if "404" in str(e) or "NotFoundError" in type(e).__name__:
            print(f"Alert {args.alert_id} not found. Run: python scripts/list_alerts.py to see available alerts.")
        else:
            raise
        sys.exit(1)
    source = doc["_source"]
    source["status"] = args.status
    if args.reviewed_by:
        source["reviewed_by"] = args.reviewed_by

    client.index(index="interaction_alerts", id=args.alert_id, document=source)
    print(f"Alert {args.alert_id} updated: status={args.status}")


if __name__ == "__main__":
    main()
