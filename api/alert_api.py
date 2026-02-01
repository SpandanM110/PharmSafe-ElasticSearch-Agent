"""
PharmaSafe Alert API — Log drug interaction alerts via HTTP.

Local: uvicorn api.alert_api:app --reload --port 8000
Render: uses PORT from env (set automatically)

POST /alert with JSON: { patient_id, new_drug, conflicting_drug, severity, mechanism, recommendation, prescribing_doctor? }
"""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys_path = str(Path(__file__).resolve().parent.parent)
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_path)

from dotenv import load_dotenv

load_dotenv()

from elasticsearch import Elasticsearch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ES_ENDPOINT = os.getenv("ES_ENDPOINT")
ES_API_KEY = os.getenv("ES_API_KEY")

if not ES_ENDPOINT or not ES_API_KEY:
    raise RuntimeError("Missing ES_ENDPOINT or ES_API_KEY in .env")

client = Elasticsearch(ES_ENDPOINT, api_key=ES_API_KEY)

app = FastAPI(title="PharmaSafe Alert API", version="1.0")


class AlertRequest(BaseModel):
    patient_id: str
    new_drug: str
    conflicting_drug: str
    severity: str
    mechanism: str
    recommendation: str
    prescribing_doctor: str | None = None


class AlertResponse(BaseModel):
    alert_id: str
    status: str


@app.post("/alert", response_model=AlertResponse)
def log_alert(req: AlertRequest):
    if req.severity not in ("critical", "moderate", "low"):
        raise HTTPException(400, "severity must be critical, moderate, or low")
    alert_id = f"ALR-{uuid.uuid4().hex[:8].upper()}"
    doc = {
        "alert_id": alert_id,
        "patient_id": req.patient_id,
        "new_drug": req.new_drug,
        "conflicting_drug": req.conflicting_drug,
        "severity": req.severity,
        "mechanism": req.mechanism,
        "recommendation": req.recommendation,
        "status": "pending_review",
        "flagged_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "reviewed_by": None,
        "prescribing_doctor": req.prescribing_doctor,
    }
    client.index(index="interaction_alerts", id=alert_id, document=doc)
    return AlertResponse(alert_id=alert_id, status="pending_review")


@app.get("/")
def root():
    return {"service": "PharmaSafe Alert API", "version": "1.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
