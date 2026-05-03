import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

config = {
    "backup_exe":       Path(os.getenv("BACKUP_EXE_PATH", "backups/backup_library.exe")),
    "log_path":         Path(os.getenv("BACKUP_LOG_PATH", "logs/backup.log")),
    "max_backups":      int(os.getenv("MAX_BACKUPS", 5)),

    "smtp_host":        os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "smtp_port":        int(os.getenv("SMTP_PORT", 587)),
    "smtp_user":        os.getenv("SMTP_USER"),
    "smtp_password":    os.getenv("SMTP_PASSWORD"),
    "alert_recipient":  os.getenv("ALERT_RECIPIENT"),
}