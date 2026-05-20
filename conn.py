"""
conn.py — App + DB initialization
Adds: Security headers (Layer 1), session hardening (Layer 2/3)
"""

import os
from urllib import response
from dotenv import load_dotenv
from flask import Flask
from flask_mysqldb import MySQL

load_dotenv()

app = Flask(__name__)

# ── Layer 3: Strong secret key from .env (never hardcode) ─────────────
app.secret_key = os.getenv('SECRET_KEY')
if not app.secret_key or app.secret_key == os.getenv('SUPER_SECRET_KEY'):
    raise RuntimeError("SECRET_KEY is weak or missing! Set a strong key in .env")

# ── Layer 2: Secure session cookies ───────────────────────────────────
app.config['SESSION_COOKIE_HTTPONLY']  = True   # JS cannot read session cookie
app.config['SESSION_COOKIE_SECURE']   = not app.debug   # Only sent over HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 # Session expires in 1 hour

# ── Layer 4: DB — use limited user from .env ───────────────────────────
app.config['MYSQL_HOST']        = os.getenv('MYSQL_HOST')
app.config['MYSQL_PORT']        = int(os.getenv('MYSQL_PORT', 3306))
app.config['MYSQL_USER']        = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD']    = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB']          = os.getenv('MYSQL_DB')
app.config['MYSQL_CURSORCLASS'] = 'Cursor'

mysql = MySQL(app)

# ── Layer 1: Security Headers ──────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'

    # Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # Force HTTPS
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    # XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Content Security Policy — prevent inline script injection
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://ajax.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob: https://covers.openlibrary.org https://books.google.com; "
        "connect-src 'self' https://cdn.jsdelivr.net; "
        "frame-src https://www.google.com/maps/; "
    )

    # No cache for authenticated pages (already in app.py — kept here as backup)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma']        = 'no-cache'
    response.headers['Expires']       = '0'

    return response
