"""
Batch processor: find unchecked prescriptions, run interaction checks, queue critical/moderate alerts.

Runs on schedule (e.g. GitHub Actions cron every 5 min). Flow:
  1. Query medications where interaction_checked != true
  2. For each: run ES|QL interaction check
  3. For each critical/moderate interaction: queue to pharmasafe_alert_requests
  4. Mark medication as interaction_checked = true

The existing process-queue job then picks up pending requests and logs to interaction_alerts.
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


def find_unchecked_medications(limit: int = 50):
    """Find medications that haven't been checked for interactions."""
    resp = client.search(
        index="medications",
        body={
            "query": {
                "bool": {
                    "must": [{"term": {"status": "active"}}],
                    "must_not": [{"term": {"interaction_checked": True}}],
                }
            },
            "size": limit,
            "sort": [{"prescribed_date": "asc"}],
        },
    )
    return [hit for hit in resp["hits"]["hits"]]


def run_interaction_check(patient_id: str, new_drug: str, new_drug_class: str):
    """Run ES|QL interaction check for new_drug vs patient's active meds."""
    # Escape double quotes for ES|QL string literals
    def esc(s):
        return (s or "").replace('"', '\\"')

    pid, nd, ndc = esc(patient_id), esc(new_drug), esc(new_drug_class)
    query = f'''
FROM medications
| WHERE patient_id == "{pid}"
| WHERE status == "active"
| EVAL pair_key = CASE(drug_name.keyword < "{nd}", CONCAT(drug_name.keyword, "|", "{nd}"), CONCAT("{nd}", "|", drug_name.keyword))
| LOOKUP JOIN drug_interactions ON pair_key
| WHERE severity IS NOT NULL
| KEEP drug_name, drug_class, severity, mechanism, clinical_effect, recommendation, evidence_level
| SORT severity ASC
| LIMIT 15
'''
    try:
        resp = client.esql.query(query=query.strip())
    except Exception as e:
        print(f"  ES|QL error for {patient_id}/{new_drug}: {e}")
        return []

    columns = [c["name"] for c in resp.get("columns", [])]
    values = resp.get("values", [])
    rows = []
    for row_vals in values:
        rows.append(dict(zip(columns, row_vals)))
    return rows


def queue_alert(patient_id: str, new_drug: str, conflicting_drug: str, severity: str, mechanism: str, recommendation: str, prescribing_doctor: str = ""):
    """Queue alert to pharmasafe_alert_requests for cron processing."""
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
    unchecked = find_unchecked_medications()
    if not unchecked:
        print("No unchecked medications.")
        return

    print(f"Processing {len(unchecked)} unchecked medication(s)...")
    queued = 0

    for hit in unchecked:
        med_id = hit["_id"]
        src = hit["_source"]
        patient_id = src.get("patient_id", "")
        new_drug = src.get("drug_name", "")
        new_drug_class = src.get("drug_class", "")
        prescribing_doctor = src.get("prescribing_doctor", "") or ""

        if not patient_id or not new_drug:
            continue

        interactions = run_interaction_check(patient_id, new_drug, new_drug_class)

        for ia in interactions:
            severity = (ia.get("severity") or "").lower()
            if severity not in ("critical", "moderate"):
                continue

            conflicting_drug = ia.get("drug_name") or ""
            mechanism = ia.get("mechanism") or ""
            recommendation = ia.get("recommendation") or ""

            req_id = queue_alert(
                patient_id=patient_id,
                new_drug=new_drug,
                conflicting_drug=conflicting_drug,
                severity=severity,
                mechanism=mechanism,
                recommendation=recommendation,
                prescribing_doctor=prescribing_doctor,
            )
            queued += 1
            print(f"  Queued {req_id}: {patient_id} {new_drug} + {conflicting_drug} ({severity})")

        # Mark as checked
        client.update(
            index="medications",
            id=med_id,
            body={"doc": {"interaction_checked": True}},
        )

    print(f"Done. Queued {queued} alert(s). Cron will process within ~5 min.")


if __name__ == "__main__":
    main()
