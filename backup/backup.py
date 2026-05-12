"""
backup/backup.py — Layer 7: Encrypted Backups
==============================================
Changes from original:
  - Added encrypt_backup() — wraps the backup file with Fernet encryption
  - Encrypted file saved as .enc alongside original
  - Original unencrypted file deleted after encryption
  - Everything else unchanged (logging, rotation, alerts, scheduler)
"""

import logging
import os
import shutil
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

from .config import config

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────

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

# ── Layer 7: Backup Encryption ────────────────────────────────────────

def _get_backup_cipher() -> Fernet:
    """Load Fernet cipher from BACKUP_ENCRYPTION_KEY in .env."""
    key = os.getenv('BACKUP_ENCRYPTION_KEY')
    if not key:
        raise RuntimeError(
            "BACKUP_ENCRYPTION_KEY missing from .env — backups will not be encrypted!"
        )
    return Fernet(key.encode())


def encrypt_backup(backup_path: Path) -> Path:
    """
    Encrypt a backup file using Fernet (AES-128-CBC).
    Returns path to the encrypted .enc file.
    Deletes the original unencrypted file afterward.
    """
    if not backup_path.exists():
        log.error("Backup file not found for encryption: %s", backup_path)
        return backup_path

    try:
        cipher      = _get_backup_cipher()
        plaintext   = backup_path.read_bytes()
        ciphertext  = cipher.encrypt(plaintext)

        enc_path = backup_path.with_suffix(backup_path.suffix + '.enc')
        enc_path.write_bytes(ciphertext)

        # Remove the unencrypted original
        backup_path.unlink()

        log.info("Backup encrypted: %s → %s", backup_path.name, enc_path.name)
        return enc_path

    except Exception as e:
        log.error("Backup encryption failed: %s", e)
        # Return original path — better to keep unencrypted than lose the backup
        return backup_path


def decrypt_backup(enc_path: Path, output_path: Path) -> bool:
    """
    Decrypt a backup .enc file back to its original form.
    Use this when you need to restore from backup.

    Example:
        python -c "
        from backup.backup import decrypt_backup
        from pathlib import Path
        decrypt_backup(Path('backups/backup_2025.sql.enc'), Path('restore.sql'))
        "
    """
    try:
        cipher     = _get_backup_cipher()
        ciphertext = enc_path.read_bytes()
        plaintext  = cipher.decrypt(ciphertext)
        output_path.write_bytes(plaintext)
        log.info("Backup decrypted to: %s", output_path)
        return True
    except Exception as e:
        log.error("Backup decryption failed: %s", e)
        return False

# ── Email alert ───────────────────────────────────────────────────────

def send_failure_alert(reason: str) -> None:
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

# ── Helpers ───────────────────────────────────────────────────────────

def rotate_old_backups() -> None:
    backup_dir = config["backup_exe"].parent
    # Include both .exe outputs and .enc encrypted backups in rotation
    backups = sorted(
        list(backup_dir.glob("backup_*")) + list(backup_dir.glob("*.enc")),
        key=lambda p: p.stat().st_mtime
    )
    for old in backups[: -config["max_backups"]]:
        log.info("Rotating old backup: %s", old.name)
        shutil.rmtree(old) if old.is_dir() else old.unlink()


def validate() -> bool:
    exe = config["backup_exe"]
    if not exe.exists():
        log.error("Executable not found: %s", exe)
        return False
    return True

# ── Core ──────────────────────────────────────────────────────────────

def run_backup() -> bool:
    if not validate():
        send_failure_alert(f"Executable not found: {config['backup_exe']}")
        return False

    log.info("Backup started.")
    start = datetime.now()

    try:
        result = subprocess.run(
            [str(config["backup_exe"])],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        elapsed = (datetime.now() - start).seconds
        log.info("Backup completed in %ds.", elapsed)

        # ── Layer 7: Encrypt the backup output ────────────────────────
        # Find the most recently modified backup file
        backup_dir    = config["backup_exe"].parent
        backup_files  = [
            f for f in backup_dir.iterdir()
            if f.is_file() and not f.suffix == '.enc' and f.name != config["backup_exe"].name
        ]
        if backup_files:
            latest = max(backup_files, key=lambda f: f.stat().st_mtime)
            encrypt_backup(latest)
            log.info("Layer 7: Backup encrypted successfully.")
        else:
            log.warning("Layer 7: No backup file found to encrypt.")

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
