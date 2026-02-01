"""
One-time backfill: mark all existing medications as interaction_checked: true.

Use when you have existing data before the batch processor was added.
Prevents the batch from re-processing historical prescriptions.

Run: python scripts/backfill_interaction_checked.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv

load_dotenv()

from elasticsearch import Elasticsearch
from elasticsearch import helpers

ES_ENDPOINT = os.getenv("ES_ENDPOINT")
ES_API_KEY = os.getenv("ES_API_KEY")

if not ES_ENDPOINT or not ES_API_KEY:
    print("Missing ES_ENDPOINT or ES_API_KEY in .env")
    sys.exit(1)

client = Elasticsearch(ES_ENDPOINT, api_key=ES_API_KEY)


def main():
    resp = client.search(
        index="medications",
        body={
            "query": {"bool": {"must_not": [{"term": {"interaction_checked": True}}]}},
            "size": 500,
            "_source": False,
        },
    )
    hits = resp["hits"]["hits"]
    if not hits:
        print("No medications to backfill.")
        return

    actions = [
        {
            "_op_type": "update",
            "_index": "medications",
            "_id": h["_id"],
            "doc": {"interaction_checked": True},
        }
        for h in hits
    ]
    helpers.bulk(client, actions, raise_on_error=True)
    print(f"Backfilled {len(actions)} medication(s) with interaction_checked: true.")


if __name__ == "__main__":
    main()
