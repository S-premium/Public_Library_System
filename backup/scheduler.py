"""
backup/scheduler.py
===================
APScheduler-based backup scheduler.
Frequency is read from the DB system_settings table so the admin
can change it from the UI without restarting the server.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

log = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_JOB_ID = "library_backup"


def _make_trigger(frequency: str) -> CronTrigger:
    """Convert a frequency string to an APScheduler CronTrigger."""
    triggers = {
        "hourly":  CronTrigger(minute=0),
        "daily":   CronTrigger(hour=2, minute=0),
        "weekly":  CronTrigger(day_of_week="sun", hour=2, minute=0),
        "monthly": CronTrigger(day=1, hour=2, minute=0),
    }
    return triggers.get(frequency, CronTrigger(day_of_week="sun", hour=2, minute=0))


def _do_backup():
    """Wrapper called by the scheduler."""
    from backup.backup import run_backup
    run_backup(backup_type="auto", scope="Database + Files")


def start_backup_scheduler(app):
    """Start the background scheduler. Called once at app startup."""
    global _scheduler

    _scheduler = BackgroundScheduler()

    # Read initial frequency from DB (fallback to weekly)
    frequency = "weekly"
    try:
        with app.app_context():
            from helpers import get_system_settings
            settings  = get_system_settings()
            frequency = settings.get("backup_frequency", "weekly")
    except Exception:
        pass

    if frequency != "off":
        _scheduler.add_job(
            _do_backup,
            trigger   = _make_trigger(frequency),
            id        = _JOB_ID,
            replace_existing = True,
        )
        log.info("Backup scheduler started — frequency: %s", frequency)
    else:
        log.info("Backup scheduler: disabled (frequency=off).")

    _scheduler.start()
    return _scheduler


def update_schedule(frequency: str) -> None:
    """
    Called by the admin API when the schedule is changed in the UI.
    Updates the running scheduler without a restart.
    """
    global _scheduler
    if _scheduler is None:
        log.warning("Scheduler not running — cannot update schedule.")
        return

    if frequency == "off":
        if _scheduler.get_job(_JOB_ID):
            _scheduler.remove_job(_JOB_ID)
            log.info("Backup scheduler disabled.")
    else:
        _scheduler.add_job(
            _do_backup,
            trigger          = _make_trigger(frequency),
            id               = _JOB_ID,
            replace_existing = True,
        )
        log.info("Backup schedule updated: %s", frequency)