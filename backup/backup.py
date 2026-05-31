"""
backup/backup.py
================
Full backup implementation:
  1. MySQL dump  → <name>.sql
  2. Files archive → <name>_files.zip  (uploads, images, vault, logs)
  3. Bundle both  → backup_<timestamp>.zip
  4. Encrypt      → backup_<timestamp>.zip.enc  (Fernet / AES-128)
  5. Upload       → Dropbox  /Iloilo_Public_Library_Backups/
  6. Rotate       → keep only MAX_BACKUPS on Dropbox
  7. Log result   → DB table  backup_logs
  8. Alert        → email on failure
"""

import io
import json
import logging
import os
import shutil
import smtplib
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

import requests
from cryptography.fernet import Fernet
from dotenv import load_dotenv

from .config import config

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────

config["log_path"].parent.mkdir(parents=True, exist_ok=True)
config["backup_dir"].mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config["log_path"]),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# DROPBOX HELPERS
# ══════════════════════════════════════════════════════════════════════

def _dropbox_access_token() -> str:
    """Exchange the stored refresh token for a fresh short-lived access token."""
    resp = requests.post(
        "https://api.dropbox.com/oauth2/token",
        data={
            "grant_type":    "refresh_token",
            "refresh_token": config["dropbox_refresh_token"],
            "client_id":     config["dropbox_app_key"],
            "client_secret": config["dropbox_app_secret"],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _dropbox_upload(local_path: Path, access_token: str) -> str:
    """
    Upload a file to Dropbox using the upload-session API (handles >150 MB).
    Returns the Dropbox path of the uploaded file.
    """
    dest_path = f"{config['dropbox_folder']}/{local_path.name}"
    file_size  = local_path.stat().st_size
    CHUNK      = 150 * 1024 * 1024   # 150 MB chunks

    headers_base = {
        "Authorization":  f"Bearer {access_token}",
        "Content-Type":   "application/octet-stream",
    }

    with open(local_path, "rb") as f:
        if file_size <= CHUNK:
            # Simple single-request upload
            headers = {
                **headers_base,
                "Dropbox-API-Arg": json.dumps({
                    "path":       dest_path,
                    "mode":       "overwrite",
                    "autorename": False,
                }),
            }
            r = requests.post(
                "https://content.dropboxapi.com/2/files/upload",
                headers=headers,
                data=f.read(),
                timeout=120,
            )
            r.raise_for_status()
        else:
            # Upload session for large files
            # Start session
            r = requests.post(
                "https://content.dropboxapi.com/2/files/upload_session/start",
                headers={
                    **headers_base,
                    "Dropbox-API-Arg": json.dumps({"close": False}),
                },
                data=f.read(CHUNK),
                timeout=120,
            )
            r.raise_for_status()
            session_id = r.json()["session_id"]
            offset     = CHUNK

            # Append chunks
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                remaining = file_size - f.tell()
                if remaining <= 0:
                    # This is the last chunk — finish
                    r = requests.post(
                        "https://content.dropboxapi.com/2/files/upload_session/finish",
                        headers={
                            **headers_base,
                            "Dropbox-API-Arg": json.dumps({
                                "cursor": {"session_id": session_id, "offset": offset},
                                "commit": {
                                    "path":       dest_path,
                                    "mode":       "overwrite",
                                    "autorename": False,
                                },
                            }),
                        },
                        data=chunk,
                        timeout=120,
                    )
                    r.raise_for_status()
                    break
                else:
                    r = requests.post(
                        "https://content.dropboxapi.com/2/files/upload_session/append_v2",
                        headers={
                            **headers_base,
                            "Dropbox-API-Arg": json.dumps({
                                "cursor": {"session_id": session_id, "offset": offset},
                                "close":  False,
                            }),
                        },
                        data=chunk,
                        timeout=120,
                    )
                    r.raise_for_status()
                    offset += len(chunk)

    log.info("Uploaded to Dropbox: %s", dest_path)
    return dest_path


def _dropbox_list_and_rotate(access_token: str) -> None:
    """List backup files on Dropbox and delete oldest if over MAX_BACKUPS."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json",
    }
    r = requests.post(
        "https://api.dropboxapi.com/2/files/list_folder",
        headers=headers,
        json={"path": config["dropbox_folder"], "limit": 200},
        timeout=30,
    )
    if r.status_code == 409:
        # Folder doesn't exist yet — nothing to rotate
        return
    r.raise_for_status()

    entries = [
        e for e in r.json().get("entries", [])
        if e[".tag"] == "file" and e["name"].startswith("backup_")
    ]
    # Sort oldest first by server_modified
    entries.sort(key=lambda e: e.get("server_modified", ""))

    to_delete = entries[: max(0, len(entries) - config["max_backups"])]
    for entry in to_delete:
        requests.post(
            "https://api.dropboxapi.com/2/files/delete_v2",
            headers=headers,
            json={"path": entry["path_lower"]},
            timeout=30,
        )
        log.info("Rotated old Dropbox backup: %s", entry["name"])


# ══════════════════════════════════════════════════════════════════════
# ENCRYPTION
# ══════════════════════════════════════════════════════════════════════

def _fernet() -> Fernet:
    key = os.getenv("BACKUP_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("BACKUP_ENCRYPTION_KEY missing from .env")
    return Fernet(key.encode())


def encrypt_file(src: Path) -> Path:
    """Encrypt src → src.enc, delete src. Returns encrypted path."""
    enc_path   = src.with_suffix(src.suffix + ".enc")
    plaintext  = src.read_bytes()
    ciphertext = _fernet().encrypt(plaintext)
    enc_path.write_bytes(ciphertext)
    src.unlink()
    log.info("Encrypted: %s → %s", src.name, enc_path.name)
    return enc_path


def decrypt_backup(enc_path: Path, output_path: Path) -> bool:
    """
    Decrypt a .enc backup for restore.
    Usage:
        python -c "
        from backup.backup import decrypt_backup
        from pathlib import Path
        decrypt_backup(Path('backup_2026-05-30.zip.enc'), Path('restore.zip'))
        "
    """
    try:
        ciphertext = enc_path.read_bytes()
        plaintext  = _fernet().decrypt(ciphertext)
        output_path.write_bytes(plaintext)
        log.info("Decrypted to: %s", output_path)
        return True
    except Exception as e:
        log.error("Decryption failed: %s", e)
        return False


# ══════════════════════════════════════════════════════════════════════
# DB DUMP
# ══════════════════════════════════════════════════════════════════════

def _find_mysqldump() -> str:
    """
    Find mysqldump executable.
    Checks PATH first, then common Windows MySQL install locations.
    """
    import shutil as _shutil
    # Try PATH first
    found = _shutil.which("mysqldump")
    if found:
        return found

    # Common Windows install paths
    win_paths = [
        r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe",
        r"C:\Program Files\MySQL\MySQL Server 5.7\bin\mysqldump.exe",
        r"C:\xampp\mysql\bin\mysqldump.exe",
        r"C:\wamp64\bin\mysql\mysql8.0\bin\mysqldump.exe",
        r"C:\wamp\bin\mysql\mysql8.0\bin\mysqldump.exe",
        r"C:\laragon\bin\mysql\mysql-8.0\bin\mysqldump.exe",
    ]
    for p in win_paths:
        if Path(p).exists():
            log.info("Found mysqldump at: %s", p)
            return p

    raise FileNotFoundError(
        "mysqldump not found. Add MySQL bin directory to your system PATH.\n"
        "Usually at: C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin"
    )


def _dump_database(dest_dir: Path, ts: str) -> Path | None:
    """Run mysqldump and write <dest_dir>/db_<ts>.sql. Returns path or None."""
    sql_path = dest_dir / f"db_{ts}.sql"

    try:
        mysqldump_exe = _find_mysqldump()
    except FileNotFoundError as e:
        log.error(str(e))
        return None

    # Build mysqldump command
    cmd = [
        mysqldump_exe,
        f"--host={config['db_host']}",
        f"--port={config['db_port']}",
        f"--user={config['db_user']}",
        f"--password={config['db_password']}",
        "--single-transaction",
        "--routines",
        "--triggers",
        config["db_name"],
    ]

    try:
        with open(sql_path, "w", encoding="utf-8") as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300,
            )
        stderr = result.stderr.strip()
        # mysqldump prints warnings to stderr even on success — only fail on error
        if result.returncode != 0:
            log.error("mysqldump failed (exit %d): %s", result.returncode, stderr)
            sql_path.unlink(missing_ok=True)
            return None
        if stderr and "error" in stderr.lower():
            log.warning("mysqldump warning: %s", stderr)

        log.info("DB dump: %s (%.1f KB)", sql_path.name, sql_path.stat().st_size / 1024)
        return sql_path

    except subprocess.TimeoutExpired:
        log.error("mysqldump timed out.")
        sql_path.unlink(missing_ok=True)
        return None
    except Exception as e:
        log.error("mysqldump error: %s", e)
        sql_path.unlink(missing_ok=True)
        return None


# ══════════════════════════════════════════════════════════════════════
# FILES ARCHIVE
# ══════════════════════════════════════════════════════════════════════

def _archive_files(dest_dir: Path, ts: str, base_dir: Path) -> Path:
    """
    Zip configured folders into <dest_dir>/files_<ts>.zip.
    Skips folders that don't exist.
    """
    zip_path = dest_dir / f"files_{ts}.zip"
    added    = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for folder in config["backup_folders"]:
            folder_path = base_dir / folder
            if not folder_path.exists():
                log.warning("Skipping missing folder: %s", folder)
                continue
            for file_path in folder_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(base_dir)
                    zf.write(file_path, arcname)
                    added += 1

    log.info(
        "Files archive: %s — %d files (%.1f KB)",
        zip_path.name, added, zip_path.stat().st_size / 1024,
    )
    return zip_path


# ══════════════════════════════════════════════════════════════════════
# BUNDLE  (db + files → single zip)
# ══════════════════════════════════════════════════════════════════════

def _bundle(dest_dir: Path, ts: str, sql_path: Path | None, files_zip: Path | None) -> Path:
    """Combine sql dump + files zip into one backup_<ts>.zip."""
    bundle_path = dest_dir / f"backup_{ts}.zip"

    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if sql_path and sql_path.exists():
            zf.write(sql_path, sql_path.name)
        if files_zip and files_zip.exists():
            zf.write(files_zip, files_zip.name)

    # Clean up intermediate files
    if sql_path and sql_path.exists():
        sql_path.unlink()
    if files_zip and files_zip.exists():
        files_zip.unlink()

    log.info(
        "Bundle: %s (%.2f MB)",
        bundle_path.name, bundle_path.stat().st_size / (1024 * 1024),
    )
    return bundle_path


# ══════════════════════════════════════════════════════════════════════
# DB LOG
# ══════════════════════════════════════════════════════════════════════

def _log_to_db(
    backup_type: str,
    scope: str,
    file_name: str,
    file_size_bytes: int,
    dropbox_path: str,
    status: str,
    error_message: str = "",
) -> None:
    """Insert a row into backup_logs. Silently skips if DB unavailable."""
    try:
        from conn import mysql, app
        with app.app_context():
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO backup_logs
                    (backup_type, scope, file_name, file_size_bytes,
                     dropbox_path, status, error_message, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (backup_type, scope, file_name, file_size_bytes,
                  dropbox_path, status, error_message))
            mysql.connection.commit()
            cur.close()
    except Exception as e:
        log.warning("Could not write backup log to DB: %s", e)


# ══════════════════════════════════════════════════════════════════════
# EMAIL ALERT
# ══════════════════════════════════════════════════════════════════════

def send_failure_alert(reason: str) -> None:
    if not all([config["smtp_user"], config["smtp_password"], config["alert_recipient"]]):
        log.warning("Email not configured — skipping alert.")
        return

    msg             = MIMEText(
        f"Backup failed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n\nReason:\n{reason}"
    )
    msg["Subject"]  = "⚠️ Iloilo Public Library — Backup Failed"
    msg["From"]     = config["smtp_user"]
    msg["To"]       = config["alert_recipient"]

    try:
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as smtp:
            smtp.starttls()
            smtp.login(config["smtp_user"], config["smtp_password"])
            smtp.send_message(msg)
        log.info("Failure alert sent to %s.", config["alert_recipient"])
    except Exception as e:
        log.error("Could not send alert email: %s", e)


# ══════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def run_backup(backup_type: str = "auto", scope: str = "Database + Files") -> bool:
    """
    Full backup pipeline:
      dump DB → archive files → bundle → encrypt → upload Dropbox → rotate → log

    Args:
        backup_type: 'auto' (scheduler) or 'manual' (admin triggered)
        scope:       human-readable description e.g. 'Database + Files'

    Returns True on success, False on failure.
    """
    log.info("=== Backup started [%s] ===", backup_type)
    start  = datetime.now()
    ts     = start.strftime("%Y-%m-%d_%H-%M-%S")

    # Work in a temp subdirectory to avoid leftover files on failure
    work_dir = config["backup_dir"] / f"_tmp_{ts}"
    work_dir.mkdir(parents=True, exist_ok=True)

    # BASE_DIR = project root (two levels up from backup/)
    base_dir = Path(__file__).resolve().parent.parent

    bundle_path = None
    enc_path    = None

    # Parse scope — what the admin checked in the UI
    do_database = "database" in scope.lower()
    do_files    = "file" in scope.lower() or "system" in scope.lower()

    # Auto backup always does everything
    if backup_type == "auto":
        do_database = True
        do_files    = True

    log.info("Scope: database=%s, files=%s", do_database, do_files)

    try:
        # ── 1. DB dump ────────────────────────────────────────────────
        sql_path = _dump_database(work_dir, ts) if do_database else None
        if do_database and sql_path is None:
            log.warning("DB dump failed — backup will contain files only.")

        # ── 2. Files archive ──────────────────────────────────────────
        files_zip = _archive_files(work_dir, ts, base_dir) if do_files else None

        # ── 3. Bundle ─────────────────────────────────────────────────
        bundle_path = _bundle(work_dir, ts, sql_path, files_zip)

        # ── 4. Encrypt ────────────────────────────────────────────────
        enc_path = encrypt_file(bundle_path)
        bundle_path = None   # now encrypted, original gone

        # ── 5. Upload to Dropbox ──────────────────────────────────────
        access_token  = _dropbox_access_token()
        dropbox_path  = _dropbox_upload(enc_path, access_token)

        # ── 6. Rotate old backups on Dropbox ──────────────────────────
        _dropbox_list_and_rotate(access_token)

        # ── 7. Log success ────────────────────────────────────────────
        elapsed   = (datetime.now() - start).seconds
        file_size = enc_path.stat().st_size
        log.info("=== Backup complete in %ds — %s ===", elapsed, enc_path.name)

        _log_to_db(
            backup_type  = backup_type,
            scope        = scope,
            file_name    = enc_path.name,
            file_size_bytes = file_size,
            dropbox_path = dropbox_path,
            status       = "success",
        )
        return True

    except Exception as e:
        reason = str(e)
        log.error("Backup failed: %s", reason)
        send_failure_alert(reason)
        _log_to_db(
            backup_type     = backup_type,
            scope           = scope,
            file_name       = enc_path.name if enc_path else f"backup_{ts}",
            file_size_bytes = enc_path.stat().st_size if enc_path and enc_path.exists() else 0,
            dropbox_path    = "",
            status          = "failed",
            error_message   = reason,
        )
        return False

    finally:
        # Clean up temp work dir regardless of success/failure
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(0 if run_backup(backup_type="manual") else 1)

