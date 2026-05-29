"""
Entry point.  Only contains:
  1. App + DB init
  2. Blueprint registrations
  3. Error handler registration
  4. Startup side-effects (backup)
  5. Dev server run
"""

from conn import app, mysql
import os
import sys
import io
from flask import jsonify, session as flask_session, send_from_directory
from backup.scheduler import start_backup_scheduler
from task_queue import enqueue   # ensure workers start at boot

app.debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    start_backup_scheduler(app)

from errors import register_error_handlers
register_error_handlers(app)

# ── Queue health endpoint (admin only) ────────────────────────────────────────
from task_queue.queue_worker import get_stats, task_queue as _tq

@app.route('/api/queue/stats')
def queue_stats():
    if flask_session.get('role') != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    stats = get_stats()
    stats['pending'] = _tq.qsize()
    return jsonify(stats)

# ── Explicitly serve static model files ───────────────────────────────────────
@app.route('/static/models/<path:filename>')
def serve_model(filename):
    models_dir = os.path.join(app.root_path, 'static', 'models')
    return send_from_directory(models_dir, filename)

from landing         import landing_bp
from authentication  import auth_bp
from routes          import admin_bp, librarian_bp, isbn_bp, user_bp
from authentication.qr_auth import qr_bp

app.register_blueprint(landing_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(qr_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(librarian_bp)
app.register_blueprint(isbn_bp)
app.register_blueprint(user_bp)

# ── Prevent browser from caching authenticated pages ──────────────────────────
@app.after_request
def set_no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# =====================================================================
# MAINTENANCE / LOCKDOWN GATE
# =====================================================================

from flask import render_template as _render_template

# Paths that are ALWAYS accessible (never blocked)
_ALWAYS_ALLOWED = (
    '/login', '/logout', '/maintenance',
    '/verify_captcha', '/verify_otp', '/verify_pin',
    '/resend_otp', '/api/check_email', '/signup',
    '/forgot_password', '/reset_password', '/reset-pin',
    '/download/apk', '/api/admin/system-settings',
)


@app.before_request
def check_system_mode():
    from flask import request, session, redirect
    from helpers import get_system_settings

    path = request.path

    # Always allow static files
    if path.startswith('/static') or path.startswith('/favicon'):
        return None

    # Always allow the maintenance page itself (avoid redirect loop)
    if path == '/maintenance':
        return None

    # Always allow auth endpoints so admins can log in / out
    if path in _ALWAYS_ALLOWED:
        return None

    try:
        settings = get_system_settings()
    except Exception:
        return None   # DB not ready yet — don't block

    role = session.get('role', '')

    # ── LOCKDOWN takes priority ───────────────────────────────────────
    if settings['lockdown_enabled']:
        if role == 'admin':
            return None   # admins always pass

        # Logged-in non-admin → force logout then redirect to login
        if role in ('librarian', 'user'):
            session.clear()
            return redirect('/login?reason=lockdown')

        # Unauthenticated visitors → show lockdown page
        return _render_template(
            'maintenance.html',
            mode='lockdown',
            message='The system is temporarily locked for security reasons. Please try again later or contact an administrator.',
        ), 503

    # ── MAINTENANCE MODE ─────────────────────────────────────────────
    if settings['maintenance_enabled']:
        bypass = settings['bypass_role']   # 'admin' or 'admin_librarian'

        if role == 'admin':
            return None
        if role == 'librarian' and bypass == 'admin_librarian':
            return None

        # Librarian is logged in but bypass is admin-only → force logout
        if role == 'librarian' and bypass == 'admin':
            session.clear()
            return redirect('/login?reason=maintenance')

        # Member/user is logged in → force logout
        if role == 'user':
            session.clear()
            return redirect('/login?reason=maintenance')

        # Unauthenticated visitors → show maintenance page
        return _render_template(
            'maintenance.html',
            mode='maintenance',
            message=settings['maintenance_message'],
        ), 503

    return None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.debug)