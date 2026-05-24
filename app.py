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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.debug)