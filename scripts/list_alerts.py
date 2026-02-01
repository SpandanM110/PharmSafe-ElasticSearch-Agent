"""
List interaction alerts from the interaction_alerts index.
Run: python scripts/list_alerts.py
"""
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
    resp = client.search(
        index="interaction_alerts",
        body={
            "size": 20,
            "sort": [{"flagged_at": "desc"}],
            "_source": ["alert_id", "patient_id", "new_drug", "conflicting_drug", "severity", "status", "flagged_at", "prescribing_doctor"],
        },
    )
    hits = resp.get("hits", {}).get("hits", [])
    if not hits:
        print("No alerts found. Run: python scripts/log_alert.py --patient-id PT-4821 --new-drug Warfarin ...")
        return
    print(f"Found {len(hits)} alert(s). Use --alert-id with the alert_id below:\n")
    for h in hits:
        s = h["_source"]
        aid = s.get("alert_id") or h["_id"]
        prescriber = s.get("prescribing_doctor") or "-"
        print(f"  {aid}  | {s.get('patient_id')} | {s.get('new_drug')} + {s.get('conflicting_drug')} | {s.get('severity')} | {s.get('status')} | prescriber: {prescriber}")


if __name__ == "__main__":
    main()
