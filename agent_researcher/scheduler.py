from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


def _run_job() -> None:
    """Wrapper to run the async pipeline from APScheduler."""
    from agent_researcher.runner import run

    logger.info("Scheduled run starting...")
    asyncio.run(run())
    logger.info("Scheduled run complete.")


def start_scheduler(hour: int = 7, minute: int = 30) -> None:
    """Start the blocking scheduler for daily runs."""
    scheduler = BlockingScheduler()

    trigger = CronTrigger(hour=hour, minute=minute)
    scheduler.add_job(_run_job, trigger, id="daily_brief", name="Daily Comedy Brief")

    logger.info("Scheduler started — daily run at %02d:%02d", hour, minute)
    print(f"Scheduler running. Next brief at {hour:02d}:{minute:02d} daily. Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
