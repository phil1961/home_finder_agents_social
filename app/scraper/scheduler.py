# v20260309-1
"""Background scheduler — runs the scraper pipeline on an interval."""
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

log = logging.getLogger(__name__)

_scheduler = None


def start_scheduler(app):
    """
    Start the background scheduler that runs the pipeline
    every FETCH_INTERVAL_HOURS.

    Call this once at app startup (e.g. in run.py).
    """
    global _scheduler

    if _scheduler is not None:
        log.warning("Scheduler already running.")
        return

    hours = int(os.environ.get("FETCH_INTERVAL_HOURS", 6))

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        func=_run_with_context,
        args=[app],
        trigger=IntervalTrigger(hours=hours),
        id="listing_pipeline",
        name=f"Fetch listings every {hours}h",
        replace_existing=True,
        next_run_time=None,  # Don't run immediately on startup
    )
    _scheduler.start()
    log.info(f"Scheduler started — pipeline runs every {hours} hours.")


def _run_with_context(app):
    """Execute the pipeline inside the Flask app context."""
    from app.scraper.pipeline import run_pipeline
    try:
        count = run_pipeline(app)
        log.info(f"Scheduled run complete: {count} listings processed.")
    except Exception as e:
        log.error(f"Scheduled pipeline failed: {e}", exc_info=True)


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("Scheduler stopped.")
