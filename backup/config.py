import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

config = {
    # ── Paths ─────────────────────────────────────────────────────────
    "backup_dir":       BASE_DIR / os.getenv("BACKUP_DIR", "backups"),
    "log_path":         BASE_DIR / os.getenv("BACKUP_LOG_PATH", "logs/backup.log"),
    "max_backups":      int(os.getenv("MAX_BACKUPS", 5)),

    # ── Folders to include in file archive ────────────────────────────
    "backup_folders": [
        "static/uploads",
        "static/images",
        "static/models",
        "valid_id_vault",
        "logs",
    ],

    # ── MySQL connection (reuse from .env) ────────────────────────────
    "db_host":          os.getenv("MYSQL_HOST", "127.0.0.1"),
    "db_port":          os.getenv("MYSQL_PORT", "3306"),
    "db_user":          os.getenv("MYSQL_USER"),
    "db_password":      os.getenv("MYSQL_PASSWORD"),
    "db_name":          os.getenv("MYSQL_DB"),

    # ── Dropbox ───────────────────────────────────────────────────────
    "dropbox_app_key":      os.getenv("DROPBOX_APP_KEY"),
    "dropbox_app_secret":   os.getenv("DROPBOX_APP_SECRET"),
    "dropbox_refresh_token":os.getenv("DROPBOX_REFRESH_TOKEN"),
    "dropbox_folder":       os.getenv("DROPBOX_FOLDER", "/Iloilo_Public_Library_Backups"),

    # ── Email alerts ──────────────────────────────────────────────────
    "smtp_host":        os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "smtp_port":        int(os.getenv("SMTP_PORT", 587)),
    "smtp_user":        os.getenv("SMTP_USER"),
    "smtp_password":    os.getenv("SMTP_PASSWORD"),
    "alert_recipient":  os.getenv("ALERT_RECIPIENT"),
}