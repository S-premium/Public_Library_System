"""
QR Code Login System — WhatsApp-style
Routes:
  POST /qr/generate          — Create a new QR token (desktop initiates)
  GET  /qr/check/<token>     — Desktop polls for confirmation status
  GET  /scan-qr              — Mobile scanner page (login required)
  POST /qr/confirm           — Mobile confirms the QR token (login required)
  POST /qr/cleanup           — (internal) remove expired tokens
"""

import uuid
import secrets
from datetime import datetime, timedelta
import qrcode
import io, base64

from flask import (
    Blueprint, render_template, request,
    session, redirect, jsonify, url_for,
)
from conn import mysql, app
from helpers import is_logged_in

qr_bp = Blueprint("qr_bp", __name__)

# ─── Token lifetime (seconds) ─────────────────────────────────────────────
QR_TOKEN_TTL = 60   # QR code expires after 60 seconds
QR_GRACE     = 10   # extra seconds before we hard-delete from DB


# =====================================================================
# HELPERS
# =====================================================================

def _now():
    return datetime.now()


def _create_qr_token():
    """
    Insert a fresh token row into qr_login_tokens and return the token string.
    The token is a URL-safe random string (not a UUID so it's unguessable).
    """
    token      = secrets.token_urlsafe(32)          # 43-char URL-safe string
    expires_at = _now() + timedelta(seconds=QR_TOKEN_TTL)

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO qr_login_tokens (token, user_id, status, created_at, expires_at)
        VALUES (%s, NULL, 'pending', %s, %s)
    """, (token, _now(), expires_at))
    mysql.connection.commit()
    cur.close()
    return token, expires_at


def _get_token_row(token: str):
    """Fetch a single token row by its string value."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, token, user_id, status, expires_at
        FROM qr_login_tokens
        WHERE token = %s
        LIMIT 1
    """, (token,))
    row = cur.fetchone()
    cur.close()
    return row   # (id, token, user_id, status, expires_at) or None


def _expire_old_tokens():
    """
    Hard-delete tokens that have passed their expiry time.
    Confirmed tokens are spared so the active qr_check poll can still
    read them and create the desktop session before they are cleaned up.
    Called lazily on generate/check so we don't need a scheduler.
    """
    cur = mysql.connection.cursor()
    cur.execute("""
        DELETE FROM qr_login_tokens
        WHERE expires_at < %s
          AND status != 'confirmed'
    """, (_now(),))
    mysql.connection.commit()
    cur.close()

@qr_bp.route("/qr/generate", methods=["POST"])
def qr_generate():
    """
    Desktop login page calls this to get a fresh token + QR code image.
    No authentication needed — this is the first step of the flow.
    """
    _expire_old_tokens()

    token, expires_at = _create_qr_token()

    # Build the URL the mobile app will POST to when it scans
    scan_url = request.host_url.rstrip("/") + f"/qr/confirm?token={token}"

    # Generate QR code as base64 PNG using qrcode library
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=2,
        )
        qr.add_data(scan_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0d1a24", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        qr_data_url = f"data:image/png;base64,{b64}"
    except ImportError:
        # Fallback: use a public QR API (works without the qrcode package)
        import urllib.parse
        encoded = urllib.parse.quote(scan_url, safe="")
        qr_data_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={encoded}"

    ttl = int((expires_at - _now()).total_seconds())

    return jsonify({
        "success":    True,
        "token":      token,
        "expires_in": ttl,
        "qr_data_url": qr_data_url,
        "scan_url":   scan_url,
    })

@qr_bp.route("/qr/check/<token>", methods=["GET"])
def qr_check(token):
    """
    Desktop polls this endpoint every ~2 seconds.
    If status == 'confirmed', we log the user in and return a redirect URL.
    """
    _expire_old_tokens()

    row = _get_token_row(token)
    if not row:
        return jsonify({"status": "expired"})

    _id, _token, user_id, status, expires_at = row

    if status == "confirmed" and user_id:
        # Fetch user details for session
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT username, role, is_active, is_approved
            FROM users WHERE id = %s
        """, (user_id,))
        user = cur.fetchone()

        # Clean up the used token immediately
        cur.execute("DELETE FROM qr_login_tokens WHERE id = %s", (_id,))
        cur.execute("""
            UPDATE users SET status='active', last_seen=%s,
                             failed_attempts=0, is_locked=0
            WHERE id = %s
        """, (_now(), user_id))
        mysql.connection.commit()
        cur.close()

        if not user or not user[2] or not user[3]:
            return jsonify({"status": "rejected", "reason": "Account not active or not approved"})

        # Create the desktop session
        session["user_id"]  = user_id
        session["username"] = user[0]
        session["role"]     = user[1]
        session.permanent   = True

        role = user[1]
        redirect_map = {
            "admin":     "/admin/home",
            "librarian": "/librarian/home",
            "user":      "/user/home",
        }
        return jsonify({
            "status":       "confirmed",
            "redirect_url": redirect_map.get(role, "/home"),
        })

    # Token not found after delete means it expired
    remaining = int((expires_at - _now()).total_seconds())
    if remaining <= 0:
        return jsonify({"status": "expired"})

    # Still pending
    return jsonify({"status": "pending", "expires_in": remaining})

@qr_bp.route("/scan-qr")
def scan_qr_page():
    """
    Mobile WebView navigates here. User must already be logged in.
    Shows a camera-based QR code scanner.
    """
    if not is_logged_in():
        return redirect("/?next=/scan-qr")
    return render_template("scan_qr.html")

@qr_bp.route("/qr/confirm", methods=["GET", "POST"])
def qr_confirm():
    """
    Called by the mobile WebView (logged-in user) after scanning.
    GET  — redirect to scanner page with pre-filled token (deep link from QR)
    POST — validate token and mark as confirmed
    """
    if not is_logged_in():
        # Save where we were going so after login we come back
        token = request.args.get("token") or request.form.get("token", "")
        return redirect(f"/?next=/qr/confirm?token={token}")

    mobile_user_id = session["user_id"]

    # ── GET: QR was opened in the WebView browser directly ──────────
    if request.method == "GET":
        token = request.args.get("token", "")
        return render_template("scan_qr.html", prefill_token=token)

    # ── POST: scanner page submits the token ──────────────────────
    data  = request.get_json(silent=True) or {}
    token = data.get("token") or request.form.get("token", "")

    if not token:
        return jsonify({"success": False, "message": "No token provided"}), 400

    _expire_old_tokens()
    row = _get_token_row(token)

    if not row:
        return jsonify({"success": False, "message": "Invalid or expired QR code"}), 404

    _id, _token, existing_user_id, status, expires_at = row

    if expires_at < _now():
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM qr_login_tokens WHERE id=%s", (_id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({"success": False, "message": "QR code expired."}), 410

    if status == "confirmed":
        return jsonify({"success": False, "message": "This QR code has already been used."}), 409

    # ── All checks passed — mark confirmed ───────────────────────
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE qr_login_tokens
        SET user_id = %s, status = 'confirmed'
        WHERE id = %s
    """, (mobile_user_id, _id))
    mysql.connection.commit()
    cur.close()

    return jsonify({"success": True, "message": "Login approved! The desktop session is now active."})