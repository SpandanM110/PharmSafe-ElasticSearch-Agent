"""
Create PharmaSafe indices in Elasticsearch.
Run: python scripts/create_indices.py
Requires: .env with ES_ENDPOINT and ES_API_KEY
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
    print("Missing ES_ENDPOINT or ES_API_KEY. Copy .env.example to .env and fill values.")
    sys.exit(1)

client = Elasticsearch(ES_ENDPOINT, api_key=ES_API_KEY)

# Index 1: patients
patients_mapping = {
    "mappings": {
        "properties": {
            "patient_id": {"type": "keyword"},
            "full_name": {"type": "text"},
            "date_of_birth": {"type": "date"},
            "age": {"type": "integer"},
            "allergies": {"type": "keyword"},
            "chronic_conditions": {"type": "keyword"},
            "primary_care_doctor": {"type": "text"},
            "last_visit_date": {"type": "date"},
        }
    }
}

# Index 2: medications
medications_mapping = {
    "mappings": {
        "properties": {
            "medication_id": {"type": "keyword"},
            "patient_id": {"type": "keyword"},
            "drug_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "drug_class": {"type": "keyword"},
            "dosage_mg": {"type": "float"},
            "frequency": {"type": "keyword"},
            "prescribing_doctor": {"type": "text"},
            "prescribed_date": {"type": "date"},
            "status": {"type": "keyword"},
            "indication": {"type": "text"},
            "source": {"type": "keyword"},
            "interaction_checked": {"type": "boolean"},
        }
    }
}

# Index 3: drug_interactions (lookup index for LOOKUP JOIN)
# Note: index.mode=lookup requires Stack 8.18+. Serverless does not support lookup mode or number_of_shards.
drug_interactions_mapping = {
    "settings": {
        "index.mode": "lookup",
    },
    "mappings": {
        "properties": {
            "interaction_id": {"type": "keyword"},
            "drug_a": {"type": "keyword"},
            "drug_b": {"type": "keyword"},
            "pair_key": {"type": "keyword"},
            "class_a": {"type": "keyword"},
            "class_b": {"type": "keyword"},
            "severity": {"type": "keyword"},
            "mechanism": {"type": "text"},
            "clinical_effect": {"type": "text"},
            "recommendation": {"type": "text"},
            "evidence_level": {"type": "keyword"},
        }
    },
}

# Index 4: interaction_alerts
# Index 5: drug_food_interactions (Phase 2.1)
# Index 6: drug_contraindications (Phase 2.2)
# Index 7: drug_dose_ranges (Phase 2.3)

drug_food_interactions_mapping = {
    "mappings": {
        "properties": {
            "food_id": {"type": "keyword"},
            "drug_name": {"type": "keyword"},
            "food": {"type": "keyword"},
            "severity": {"type": "keyword"},
            "mechanism": {"type": "text"},
            "clinical_effect": {"type": "text"},
            "recommendation": {"type": "text"},
        }
    }
}

drug_contraindications_mapping = {
    "mappings": {
        "properties": {
            "contra_id": {"type": "keyword"},
            "drug_name": {"type": "keyword"},
            "drug_class": {"type": "keyword"},
            "condition": {"type": "keyword"},
            "severity": {"type": "keyword"},
            "recommendation": {"type": "text"},
        }
    }
}

drug_dose_ranges_mapping = {
    "mappings": {
        "properties": {
            "dose_id": {"type": "keyword"},
            "drug_name": {"type": "keyword"},
            "indication": {"type": "keyword"},
            "min_mg": {"type": "float"},
            "max_mg": {"type": "float"},
            "frequency": {"type": "keyword"},
            "unit": {"type": "keyword"},
        }
    }
}

# Phase 3.1: Beers criteria (elderly patients age 65+)
beers_criteria_mapping = {
    "mappings": {
        "properties": {
            "beers_id": {"type": "keyword"},
            "drug_name": {"type": "keyword"},
            "drug_class": {"type": "keyword"},
            "concern": {"type": "text"},
            "recommendation": {"type": "text"},
            "severity": {"type": "keyword"},
        }
    }
}

interaction_alerts_mapping = {
    "mappings": {
        "properties": {
            "alert_id": {"type": "keyword"},
            "patient_id": {"type": "keyword"},
            "new_drug": {"type": "keyword"},
            "conflicting_drug": {"type": "keyword"},
            "severity": {"type": "keyword"},
            "mechanism": {"type": "text"},
            "recommendation": {"type": "text"},
            "status": {"type": "keyword"},
            "flagged_at": {"type": "date"},
            "reviewed_by": {"type": "text"},
            "prescribing_doctor": {"type": "keyword"},
        }
    }
}

# Queue for cron-based alert processing (GitHub Actions)
pharmasafe_alert_requests_mapping = {
    "mappings": {
        "properties": {
            "request_id": {"type": "keyword"},
            "patient_id": {"type": "keyword"},
            "new_drug": {"type": "keyword"},
            "conflicting_drug": {"type": "keyword"},
            "severity": {"type": "keyword"},
            "mechanism": {"type": "text"},
            "recommendation": {"type": "text"},
            "prescribing_doctor": {"type": "keyword"},
            "status": {"type": "keyword"},
            "created_at": {"type": "date"},
        }
    }
}

indices = [
    ("patients", patients_mapping),
    ("medications", medications_mapping),
    ("drug_interactions", drug_interactions_mapping),
    ("interaction_alerts", interaction_alerts_mapping),
    ("drug_food_interactions", drug_food_interactions_mapping),
    ("drug_contraindications", drug_contraindications_mapping),
    ("drug_dose_ranges", drug_dose_ranges_mapping),
    ("beers_criteria", beers_criteria_mapping),
    ("pharmasafe_alert_requests", pharmasafe_alert_requests_mapping),
]


def main():
    for name, body in indices:
        try:
            if client.indices.exists(index=name):
                print(f"Index '{name}' already exists. Skipping.")
                continue
            client.indices.create(index=name, body=body)
            print(f"Created index: {name}")
        except Exception as e:
            err = str(e).lower()
            if "index.mode" in err or "lookup" in err or "number_of_shards" in err or "serverless" in err:
                print(f"Lookup/shard settings not supported for {name}. Creating as regular index (mappings only).")
                body_fallback = {"mappings": body["mappings"]}
                client.indices.create(index=name, body=body_fallback)
                print(f"Created index (regular): {name}")
            else:
                raise
    print("Done.")


if __name__ == "__main__":
    main()
