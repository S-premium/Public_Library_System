## storage/book_thumbnail.py  (no shared links; only needs files.content.write + files.content.read)

import logging
import os
import re
import time
import uuid

import dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import WriteMode
from werkzeug.utils import secure_filename

from backup.config import config

ALLOWED = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
COVERS_FOLDER = os.getenv("DROPBOX_COVERS_FOLDER", "/Iloilo_Public_Library_Covers")

NAME_RE = re.compile(r"^[a-f0-9]{32}\.(png|jpg|jpeg|webp|gif)$")
_LINK_TTL = 3 * 3600          # Dropbox temporary links last 4h; refresh at 3h
_link_cache = {}              # name -> (url, expires_at)


def _client():
    return dropbox.Dropbox(
        oauth2_refresh_token=config["dropbox_refresh_token"],
        app_key=config["dropbox_app_key"],
        app_secret=config["dropbox_app_secret"],
    )


def upload_bytes(data, ext):
    """Upload image bytes to Dropbox.

    Returns a local URL like '/cover/<name>' (served by the Flask route that
    redirects to a temporary Dropbox link). Raises ValueError with a specific
    reason on failure.
    """
    ext = (ext or "").lower()
    if ext not in ALLOWED:
        raise ValueError("Unsupported image type.")
    if not data:
        raise ValueError("Empty image file.")
    if len(data) > MAX_BYTES:
        raise ValueError("Cover image must be under 5 MB.")

    name = f"{uuid.uuid4().hex}{ext}"
    try:
        _client().files_upload(data, f"{COVERS_FOLDER}/{name}", mode=WriteMode.add)
    except AuthError:
        logging.exception("Dropbox auth failed")
        raise ValueError("Dropbox authorization failed (token expired or revoked).")
    except ApiError as e:
        logging.exception("Dropbox API error")
        if "missing_scope" in str(e):
            raise ValueError("Dropbox app is missing the files.content.write scope.")
        raise ValueError(f"Dropbox error: {e.error}")
    except Exception as e:
        logging.exception("Dropbox cover upload failed")
        raise ValueError(f"Cover upload failed: {type(e).__name__}")

    return f"/cover/{name}"


def upload_cover(file):
    """Upload a Flask FileStorage. Returns '/cover/<name>' or None if no file."""
    if not file or not file.filename:
        return None
    ext = os.path.splitext(secure_filename(file.filename))[1]
    return upload_bytes(file.read(), ext)

import mimetypes

NAME_RE = re.compile(r"^[a-f0-9]{32}(\.(png|jpg|jpeg|webp|gif))?$")  # extension optional


def download_cover(name):
    """Return (bytes, mimetype) for a stored cover, or None."""
    if not NAME_RE.match(name or ""):
        return None
    try:
        _, res = _client().files_download(f"{COVERS_FOLDER}/{name}")
    except Exception:
        logging.exception("Dropbox download failed for %s", name)
        return None
    mime = mimetypes.guess_type(name)[0] or "image/jpeg"
    return res.content, mime

    