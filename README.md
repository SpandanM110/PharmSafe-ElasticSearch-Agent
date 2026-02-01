# PharmaSafe — Drug Interaction & Patient Risk Agent

An AI agent that checks new prescriptions against a patient's full medication history for dangerous interactions. Built on Elasticsearch, Kibana Agent Builder, and ES|QL.

---

## Overview

PharmaSafe sits at the point of dispensing. When a new prescription comes in, it pulls the patient's full medication history, cross-references every active drug against a known interaction database, classifies severity, and alerts the pharmacist — all before the prescription is filled.

**Flow:** Pharmacist asks → Agent finds patient → Agent checks interactions → Agent logs alerts → Kibana rule sends email

**Fully autonomous flow (no manual steps):** Simulate prescription (every 6 h) → Batch check (every 5 min) → Process queue → Kibana rule → Email

---

## How Everything Connects

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ELASTICSEARCH (data store)                         │
│  patients | medications | drug_interactions | interaction_alerts | ...      │
└─────────────────────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
    ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
    │ Kibana  │          │ Render  │          │ GitHub  │
    │ Rule    │          │ API     │          │ Actions │
    │         │          │         │          │         │
    │ Email   │          │ POST    │          │ simulate│
    │ on alert│          │ /alert  │          │ + batch │
    └─────────┘          └─────────┘          └─────────┘
    every 1 min          pharmasafe-api       every 6h + 5min
```

| Component | Connects to Elasticsearch via | Purpose |
|-----------|-------------------------------|---------|
| **GitHub Actions** | `ES_ENDPOINT` + `ES_API_KEY` (GitHub secrets) | Simulate prescription (every 6 h), batch-check (every 5 min), process-queue |
| **Kibana Rule** | Same Elastic project | Query `interaction_alerts`, send email when critical |
| **Render API** | `ES_ENDPOINT` + `ES_API_KEY` (Render env vars) | Optional: log alerts via HTTP (POST /alert) |
| **Kibana Agent** | Same Elastic project | Optional: chat, run checks (ad-hoc queries) |

---

## Connect Kibana Agent to Elasticsearch

The Kibana Agent runs inside Kibana and uses the **same Elasticsearch project** Kibana is connected to. No extra credentials are needed — Kibana already talks to Elasticsearch.

### Prerequisites

1. **Indices exist** — Run locally first:
   ```powershell
   python scripts/create_indices.py
   python scripts/seed_data.py
   ```
2. **Same Elastic project** — Use Kibana from the same Elastic Cloud project where you ran the scripts (same `ES_ENDPOINT`).

### Step-by-step

1. **Open Kibana** — Use the Kibana URL from your Elastic Cloud project (Help → Connection Details).
2. **Go to Agents** — In Kibana, use the **global search** (top bar) and search for **"Agents"** or **"Agent Builder"**, or check **Machine Learning** → **Agents** / **AI Assistant** → **Agents** (menu varies by Elastic version).
3. **Create agent** — Click **Create agent**.
4. **Name** — e.g. "PharmaSafe".
5. **Instructions** — Copy from `config/agent_tools.json` (field `instructions`).
6. **Add tools** — Create and assign these tools (see Agent Builder Setup below).
7. **Save** — The agent will use Kibana’s connection to Elasticsearch.

### Verify connection

- In Agent Chat, ask: *"Check Warfarin for Sarah Mitchell"*
- The agent should search `patients`, query `medications` and `drug_interactions`, and return results.

If the agent says "patient not found" or returns no data, check:
- Indices exist: Kibana → **Discover** → create data views for `patients`, `medications`, `drug_interactions`
- You’re in the correct Elastic project (same deployment as where you ran `create_indices.py`)

---

## Connect Render API to Elasticsearch

The Render API at **https://pharmasafe-api.onrender.com** must have Elasticsearch credentials to log alerts.

1. Go to [Render Dashboard](https://dashboard.render.com) → **pharmasafe-api** → **Environment**
2. Add (or verify) these variables:

| Key | Value |
|-----|-------|
| `ES_ENDPOINT` | Your Elasticsearch URL (e.g. `https://xxxxx.es.us-east-1.aws.elastic.cloud:443`) |
| `ES_API_KEY` | Your Elasticsearch API key (same as in `.env`) |

3. **Save** — Render will redeploy the service.
4. Test: `https://pharmasafe-api.onrender.com/health` → `{"status":"ok"}`

**Test POST /alert:** Use [Swagger UI](https://pharmasafe-api.onrender.com/docs) → POST /alert → Try it out.

---

## Prerequisites

- Elasticsearch (Cloud Serverless or Hosted) 8.18+
- Kibana with Agent Builder (Enterprise)
- Python 3.10+

---

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env: add ES_ENDPOINT and ES_API_KEY

# 2. Install and create indices
pip install -r requirements.txt
python scripts/create_indices.py
python scripts/seed_data.py

# 3. Add GitHub secrets: ES_ENDPOINT, ES_API_KEY

# 4. Create Kibana rule (Elasticsearch query on interaction_alerts, email connector)

# 5. Push to GitHub — autonomous flow runs: simulate (6h) + batch (5min) → email
```

**Optional:** Set up Kibana Agent for ad-hoc chat queries (see Agent Builder section).

---

## Elasticsearch Configuration

### Where to Get Credentials

| What | Where |
|------|-------|
| **Elasticsearch endpoint** | Kibana → Help (?) → Connection Details → Endpoints tab |
| **API key** | Project home → Create API key (or Project settings → Management → API keys) |

Copy the API key immediately — it is shown only once.

### .env

```
ES_ENDPOINT=https://xxxxx.es.us-east-1.aws.elastic.cloud:443
ES_API_KEY=your_base64_encoded_api_key
```

---

## Agent Builder Setup (Kibana)

1. Open Kibana → **Agents** (or search "Agents")
2. Create a new agent; use instructions from `config/agent_tools.json`
3. Create and assign these tools:

### Tool 1: Index Search — `search_patient_by_name`
- Type: **Index Search**
- Index: `patients`
- Description: *"Searches the patient registry to find a patient by name, ID, or other identifying details. Use this first whenever a user mentions a patient."*

### Tool 2: ES|QL — `find_active_medications`
- Type: **ES|QL**
- Query:
```
FROM medications
| WHERE patient_id == ?patient_id
| WHERE status == "active"
| KEEP drug_name, drug_class, dosage_mg, frequency, prescribing_doctor, prescribed_date, indication
| SORT prescribed_date DESC
| LIMIT 20
```
- Parameter: `patient_id` (keyword, required)

### Tool 3: ES|QL — `check_drug_interactions`
- Type: **ES|QL**
- Query:
```
FROM medications
| WHERE patient_id == ?patient_id
| WHERE status == "active"
| EVAL pair_key = CASE(drug_name.keyword < ?new_drug_name, CONCAT(drug_name.keyword, "|", ?new_drug_name), CONCAT(?new_drug_name, "|", drug_name.keyword))
| LOOKUP JOIN drug_interactions ON pair_key
| WHERE severity IS NOT NULL
| KEEP drug_name, drug_class, severity, mechanism, clinical_effect, recommendation, evidence_level
| SORT severity ASC
| LIMIT 15
```
- Parameters: `patient_id`, `new_drug_name`, `new_drug_class` (all keyword, required)

### Tool 4: Workflow — `log_interaction_alert` (optional)
- Type: **Workflow**
- Workflow: `log_drug_interaction_alert` (import from `workflows/log_drug_interaction_alert.yaml` if Workflows available)

### Agent Instructions (Copy to Kibana Custom Instructions)

Copy the instructions from `config/agent_tools.json` (field `instructions`) or use the Phase 3 instructions: allergy check, duplicate therapy, contraindications, Beers criteria (age 65+), drug interactions, drug–food, dose validation, historical alerts, patient summary. Full text is in the `instructions` field of `config/agent_tools.json`.

---

## Alert Workflow

When the agent detects critical/moderate interactions, alerts can be logged via:

| Option | How |
|--------|-----|
| **Manual** | `python scripts/log_alert.py --patient-id PT-4821 --new-drug Warfarin --conflicting-drug Aspirin --severity critical --mechanism "..." --recommendation "..."` |
| **API** | `uvicorn api.alert_api:app --port 8000` then `POST /alert` |
| **Elastic Workflow** | If Workflows available: agent calls `log_interaction_alert` tool |
| **Fully autonomous** | Render or GitHub Actions cron (see below) |

---

## Fully Autonomous (No Manual Steps)

The system runs end-to-end without human intervention:

| Step | Workflow | Schedule | What it does |
|------|----------|----------|--------------|
| 1 | **Simulate prescription** | Every 6 h | Adds Warfarin for Sarah Mitchell (PT-4821) → triggers Aspirin+Warfarin (critical) |
| 2 | **Batch check** | Every 5 min | Finds unchecked meds, runs ES|QL interaction checks, queues critical/moderate alerts |
| 3 | **Process queue** | Every 5 min | Indexes queued alerts → `interaction_alerts` |
| 4 | **Kibana rule** | Every 1 min | Queries `interaction_alerts`, sends email when count > 0 |

### Setup (One-Time)

1. **GitHub secrets:** `ES_ENDPOINT`, `ES_API_KEY`
2. **Kibana rule:** Elasticsearch query on `interaction_alerts`, email connector
3. **Indices + seed data:** Run `create_indices.py` and `seed_data.py` once

After that, no manual steps — alerts and emails run automatically.

### GitHub Actions Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **Simulate prescription** | Every 6 h, or manual | Adds new prescription (Warfarin) → batch picks it up |
| **Log Drug Interaction Alert** | Every 5 min (cron), or manual | batch-check → process-queue |
| **Run batch processor** | Manual only | Same as cron, on demand |

### Render (API — Optional)

Per [Render's free tier](https://render.com/docs/free), only Web Services support Free instances. Cron jobs require a paid plan.

1. Push repo to GitHub
2. [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint**
3. Connect repo; Render detects `render.yaml`
4. Add `ES_ENDPOINT` and `ES_API_KEY` to **pharmasafe-api**
5. **Apply**

**Deploys:** Web API (POST /alert, GET /health) — **free**. Spins down after 15 min idle. Use for external systems that POST alerts directly.

### Local Test (Optional)

```bash
# Simulate: add prescription
python scripts/add_prescription.py --patient-id PT-4821 --drug Warfarin --drug-class anticoagulant

# Run batch + process (simulates cron)
python scripts/cron_runner.py
```

### Existing Deployments

```bash
# One-time: mark existing meds as checked
python scripts/backfill_interaction_checked.py
```

---

## Kibana Dashboard

1. **Stack Management** → **Data Views** → Create data view: `interaction_alerts`, timestamp `flagged_at`
2. **Discover** → Add columns: `alert_id`, `patient_id`, `new_drug`, `conflicting_drug`, `severity`, `status`, `flagged_at`
3. **Dashboard** → Create → Add Lens panels: Alerts by Status, Alerts by Severity, Recent Alerts table

---

## Prescriber Notification (Kibana Rule)

1. **Stack Management** → **Rules and Connectors** → Create connector (Email/Slack/Webhook)
2. **Rules** → **Create rule** → **Elasticsearch query**
3. Index: `interaction_alerts`
4. Query: `{"query": {"bool": {"filter": [{"term": {"severity": "critical"}}, {"term": {"status": "pending_review"}}]}}}`
5. Check every: 1 min | Notify when: count > 0
6. Add action: Email/Slack with `{{context.hits}}` template

**Troubleshooting:** If "Could not locate field: kibana.alert.group.value", set **Over** (not "Grouped Over") with no grouping field.

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `create_indices.py` | Create Elasticsearch indices |
| `seed_data.py` | Load synthetic patients, medications, interactions |
| `add_prescription.py` | Add new prescription (interaction_checked: false) for batch testing |
| `batch_check_interactions.py` | Find unchecked meds, run ES|QL checks, queue alerts |
| `process_alert_queue.py` | Process pending requests → interaction_alerts |
| `cron_runner.py` | Run batch + process (Render cron / local test) |
| `queue_alert.py` | Manually queue single alert |
| `log_alert.py` | Log alert directly to interaction_alerts |
| `update_alert_status.py` | Update alert status (reviewed, dispensed_anyway, blocked) |
| `list_alerts.py` | List alerts |
| `backfill_interaction_checked.py` | Mark all existing meds as checked (one-time) |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Service info |
| GET | /health | Health check |
| GET | /docs | OpenAPI docs |
| POST | /alert | Log drug interaction alert |

**POST /alert** body: `{ patient_id, new_drug, conflicting_drug, severity, mechanism, recommendation, prescribing_doctor? }`

---

## Test Query

In Agent Chat:

> Check Warfarin for Sarah Mitchell

Expected: Critical (Warfarin + Aspirin), moderate (Warfarin + Atorvastatin). Alerts logged.

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| Agent doesn't call workflow | Workflow tool assigned? Instructions mention it? |
| No email | Kibana rule threshold "above 0"? Rule runs every 1 min? |
| API fails on Render | ES_ENDPOINT and ES_API_KEY set? |
| Cron not running | Render: plan starter or higher. GitHub: secrets set? |
| LOOKUP JOIN fails | Elasticsearch 8.18+? drug_interactions in lookup mode? |

---

## Notes

- **LOOKUP JOIN** needs Elasticsearch 8.18+ and `drug_interactions` in lookup mode. Serverless may create a regular index; LOOKUP may not work until supported.
- **Agent Builder** requires Enterprise subscription on Elastic Cloud.
- **Render free tier:** Web service spins down after 15 min inactivity. For free autonomous cron, use GitHub Actions.
