"""
Verify Phase 2 indices and queries work.
Run: python scripts/verify_phase2_data.py
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


def run_esql(query: str) -> dict:
    resp = client.esql.query(query=query)
    return resp


def main():
    print("Verifying Phase 2 data...\n")

    # 1. Drug-food for Warfarin
    q1 = 'FROM drug_food_interactions | WHERE drug_name == "Warfarin" | KEEP drug_name, food, severity, mechanism, recommendation'
    try:
        r1 = run_esql(q1)
        rows = r1.get("values", []) if isinstance(r1, dict) else (getattr(r1, "values", None) or [])
        print(f"1. Drug-food (Warfarin): {len(rows)} row(s)")
        if rows:
            for row in rows:
                print(f"   - {row}")
        else:
            print("   No results. Check index exists and has data.")
    except Exception as e:
        print(f"1. Drug-food: ERROR - {e}")

    # 2. Dose range for Warfarin + atrial_fibrillation
    q2 = 'FROM drug_dose_ranges | WHERE drug_name == "Warfarin" | WHERE indication == "atrial_fibrillation" | KEEP drug_name, indication, min_mg, max_mg, unit'
    try:
        r2 = run_esql(q2)
        rows = r2.get("values", []) if isinstance(r2, dict) else (getattr(r2, "values", None) or [])
        print(f"\n2. Dose range (Warfarin, atrial_fibrillation): {len(rows)} row(s)")
        if rows:
            for row in rows:
                print(f"   - {row}")
        else:
            print("   No results. Check index exists and has data.")
    except Exception as e:
        print(f"2. Dose range: ERROR - {e}")

    # 3. List indices
    print("\n3. Indices in project:")
    try:
        idx = client.cat.indices(format="json")
        for i in idx:
            if "drug" in i.get("index", "") or "interaction" in i.get("index", ""):
                print(f"   - {i.get('index')}")
    except Exception as e:
        print(f"   ERROR: {e}")

    print("\nDone. If 1 and 2 show data, the agent should be able to query it.")
    print("If agent still says 'system limitations', check Agent Builder permissions for these indices.")


if __name__ == "__main__":
    main()
