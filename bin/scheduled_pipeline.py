# ─────────────────────────────────────────────
# File: bin/scheduled_pipeline.py
# App Version: 2026.03.11 | File Version: 1.1.0
# Last Modified: 2026-03-11
# ─────────────────────────────────────────────
"""
bin/scheduled_pipeline.py
─────────────────────────
Nightly pipeline runner for Windows Task Scheduler.

Iterates all active, non-paused sites in the registry, runs the pipeline
for each, and logs results to ApiCallLog with trigger='scheduled'.

Usage (Task Scheduler action):
    Program: D:/Projects/home_finder_agents/.venv/Scripts/python.exe
    Arguments: bin/scheduled_pipeline.py
    Start in: D:/Projects/home_finder_agents
"""
import os
import sys
import logging

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("scheduled_pipeline")


def main():
    from app import create_app
    from app.services.registry import get_all_sites

    app = create_app()

    sites = [s for s in get_all_sites() if s.get("active")]
    log.info(f"Scheduled pipeline starting — {len(sites)} active site(s)")

    for site in sites:
        key = site["site_key"]

        if site.get("scheduler_locked") or site.get("scheduler_paused"):
            reason = "LOCKED by master" if site.get("scheduler_locked") else "PAUSED"
            log.info(f"  {key}: {reason} — skipping")
            continue

        try:
            with app.app_context():
                from app.scraper.pipeline import run_pipeline

                count = run_pipeline(app, site_key=key)
                # Individual API calls are logged by the scraper modules
                log.info(f"  {key}: {count} listings processed")

        except Exception as exc:
            log.error(f"  {key}: FAILED — {exc}")

    log.info("Scheduled pipeline complete.")


if __name__ == "__main__":
    main()
