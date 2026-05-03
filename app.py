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
from backup.scheduler import start_backup_scheduler

app.debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    start_backup_scheduler(app)

from errors import register_error_handlers
register_error_handlers(app)

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
# Without this, hitting the back button after logout shows cached pages,
# making the user appear still logged in.
@app.after_request
def set_no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=app.debug)