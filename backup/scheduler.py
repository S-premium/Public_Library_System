from apscheduler.schedulers.background import BackgroundScheduler
from backup.backup import run_backup
import logging

log = logging.getLogger(__name__)

def start_backup_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_backup, "cron", hour=2, minute=0)  # daily 2:00 AM
    scheduler.start()
    log.info("Backup scheduler running — daily at 2:00 AM.")
    return scheduler