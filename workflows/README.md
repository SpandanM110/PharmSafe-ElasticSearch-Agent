# PharmaSafe Workflows

Two options are supported. Each uses different workflow files.

## Option A: Agent (Real-time)

| File | Purpose |
|------|---------|
| `agent/log_drug_interaction_alert.yaml` | Kibana/Elastic workflow. Import into Kibana when using the Agent. The Agent invokes this when it detects critical/moderate interactions. |
| `log_drug_interaction_alert.yaml` | Legacy path (same content). Kept for backward compatibility with existing GitHub URLs. |

**Import path:** `workflows/agent/log_drug_interaction_alert.yaml` (or `workflows/log_drug_interaction_alert.yaml` for legacy)

---

## Option B: Autonomous Batch

| File | Purpose |
|------|---------|
| `.github/workflows/simulate_prescription.yml` | Adds new prescriptions (e.g. Warfarin for Sarah Mitchell) on schedule or manual trigger. |
| `.github/workflows/log_alert.yml` | Batch-check + process-queue (every 5 min) or manual log-from-inputs. |
| `.github/workflows/batch_process.yml` | Manual trigger for batch-check + process-queue. |

**Location:** `.github/workflows/` (GitHub Actions format)

---

## Summary

| Option | Workflow Location | Trigger |
|--------|-------------------|---------|
| **A: Agent** | `workflows/agent/` | Pharmacist asks in Kibana Chat |
| **B: Batch** | `.github/workflows/` | Schedule or manual Run workflow |
