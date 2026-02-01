"""
Process pending alert requests from pharmasafe_alert_requests → interaction_alerts.

Run by cron (Render or GitHub Actions). For each pending request:
  1. Index to interaction_alerts
  2. Update request status to processed
"""
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


def main():
    resp = client.search(
        index="pharmasafe_alert_requests",
        body={
            "query": {"term": {"status": "pending"}},
            "size": 50,
            "sort": [{"created_at": "asc"}],
        },
    )
    hits = resp["hits"]["hits"]
    if not hits:
        print("No pending requests.")
        return

    print(f"Processing {len(hits)} pending request(s)...")
    for hit in hits:
        req_id = hit["_id"]
        src = hit["_source"]
        alert_id = f"ALR-{uuid.uuid4().hex[:8].upper()}"
        doc = {
            "alert_id": alert_id,
            "patient_id": src.get("patient_id", ""),
            "new_drug": src.get("new_drug", ""),
            "conflicting_drug": src.get("conflicting_drug", ""),
            "severity": src.get("severity", ""),
            "mechanism": src.get("mechanism", ""),
            "recommendation": src.get("recommendation", ""),
            "status": "pending_review",
            "flagged_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "reviewed_by": None,
            "prescribing_doctor": src.get("prescribing_doctor", "") or "",
        }
        client.index(index="interaction_alerts", id=alert_id, document=doc)
        client.update(
            index="pharmasafe_alert_requests",
            id=req_id,
            body={"doc": {"status": "processed"}},
        )
        print(f"  Processed {req_id} -> {alert_id}")

    print("Done. Kibana rule will send email for critical alerts.")


if __name__ == "__main__":
    main()
