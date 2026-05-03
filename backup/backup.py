import logging
import shutil
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from .config import config

# ── Logging ──────────────────────────────────────────────────────────────────

config["log_path"].parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config["log_path"]),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Email alert ───────────────────────────────────────────────────────────────

def send_failure_alert(reason: str) -> None:
    """Send an email when backup fails."""
    if not all([config["smtp_user"], config["smtp_password"], config["alert_recipient"]]):
        log.warning("Email not configured — skipping alert.")
        return

    msg = MIMEText(
        f"Backup failed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n\nReason:\n{reason}"
    )
    msg["Subject"] = "⚠️ Library Backup Failed"
    msg["From"]    = config["smtp_user"]
    msg["To"]      = config["alert_recipient"]

    try:
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as smtp:
            smtp.starttls()
            smtp.login(config["smtp_user"], config["smtp_password"])
            smtp.send_message(msg)
        log.info("Failure alert sent to %s.", config["alert_recipient"])
    except Exception as e:
        log.error("Could not send alert email: %s", e)

# ── Helpers ───────────────────────────────────────────────────────────────────

def rotate_old_backups() -> None:
    backup_dir = config["backup_exe"].parent
    backups = sorted(backup_dir.glob("backup_*"), key=lambda p: p.stat().st_mtime)
    for old in backups[: -config["max_backups"]]:
        log.info("Rotating old backup: %s", old.name)
        shutil.rmtree(old) if old.is_dir() else old.unlink()


def validate() -> bool:
    exe = config["backup_exe"]
    if not exe.exists():
        log.error("Executable not found: %s", exe)
        return False
    return True

# ── Core ──────────────────────────────────────────────────────────────────────

def run_backup() -> bool:
    if not validate():
        send_failure_alert(f"Executable not found: {config['backup_exe']}")
        return False

    log.info("Backup started.")
    start = datetime.now()

    try:
        result = subprocess.run(
            [str(config["backup_exe"])],  # list form — no shell=True
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        elapsed = (datetime.now() - start).seconds
        log.info("Backup completed in %ds.", elapsed)
        rotate_old_backups()
        return True

    except subprocess.TimeoutExpired:
        reason = "Backup process timed out after 5 minutes."
    except subprocess.CalledProcessError as e:
        reason = f"Exit code {e.returncode}.\nstderr: {e.stderr.strip()}"
    except Exception as e:
        reason = f"Unexpected error: {e}"

    log.error(reason)
    send_failure_alert(reason)
    return False


if __name__ == "__main__":
    sys.exit(0 if run_backup() else 1)