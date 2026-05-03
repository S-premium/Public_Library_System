"""
errors/error_handlers.py
-------------------------
Registers 403 / 404 / 500 error handlers on the Flask app.
Call register_error_handlers(app) once in app.py.
"""

from flask import render_template
from conn import mysql


def register_error_handlers(app) -> None:

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404), 404

    @app.errorhandler(500)
    def internal_error(e):
        try:
            mysql.connection.rollback()
        except Exception:
            pass
        return render_template("error.html", code=500), 500