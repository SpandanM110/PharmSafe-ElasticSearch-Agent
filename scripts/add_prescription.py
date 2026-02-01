"""
Add a new prescription to medications (for testing the batch processor).

New prescriptions have interaction_checked: false so the batch processor will
check them for interactions and queue critical/moderate alerts.

Run: python scripts/add_prescription.py --patient-id PT-4821 --drug Warfarin --drug-class anticoagulant [--prescribing-doctor "Dr. Smith"]

Example: Add Warfarin for Sarah Mitchell → batch will find Aspirin+Warfarin (critical) and queue alert.
"""
import argparse
import os
import sys
import uuid
from datetime import date
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


def add_prescription(patient_id: str, drug_name: str, drug_class: str, prescribing_doctor: str = ""):
    med_id = f"MED-{uuid.uuid4().hex[:8].upper()}"
    doc = {
        "medication_id": med_id,
        "patient_id": patient_id,
        "drug_name": drug_name,
        "drug_class": drug_class,
        "dosage_mg": None,
        "frequency": "once_daily",
        "prescribing_doctor": prescribing_doctor or "",
        "prescribed_date": date.today().isoformat(),
        "status": "active",
        "indication": "",
        "source": "prescription",
        "interaction_checked": False,
    }
    client.index(index="medications", id=med_id, document=doc)
    return med_id


def main():
    parser = argparse.ArgumentParser(description="Add new prescription for batch processor testing")
    parser.add_argument("--patient-id", required=True, help="Patient ID (e.g. PT-4821)")
    parser.add_argument("--drug", required=True, help="Drug name (e.g. Warfarin)")
    parser.add_argument("--drug-class", required=True, help="Drug class (e.g. anticoagulant)")
    parser.add_argument("--prescribing-doctor", default="")
    args = parser.parse_args()

    med_id = add_prescription(
        patient_id=args.patient_id,
        drug_name=args.drug,
        drug_class=args.drug_class,
        prescribing_doctor=args.prescribing_doctor or None,
    )
    print(f"Added {args.drug} for {args.patient_id} (medication_id={med_id})")
    print("Batch processor will check within ~5 min. Run batch_check_interactions.py locally to process immediately.")


if __name__ == "__main__":
    main()
