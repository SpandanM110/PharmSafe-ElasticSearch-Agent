"""
Cron runner: batch-check + process-queue in one job.

Runs on schedule (Render Cron or GitHub Actions). Flow:
  1. batch_check_interactions: find unchecked meds, run ES|QL, queue critical/moderate alerts
  2. process_alert_queue: process pending requests → interaction_alerts → Kibana rule → email
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    for script in ["batch_check_interactions", "process_alert_queue"]:
        path = ROOT / "scripts" / f"{script}.py"
        print(f"--- Running {script} ---")
        rc = subprocess.call([sys.executable, str(path)], cwd=str(ROOT))
        if rc != 0:
            sys.exit(rc)
    print("--- Cron run complete ---")


if __name__ == "__main__":
    main()
