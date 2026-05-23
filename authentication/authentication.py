"""
authentication/authentication.py
---------------------------------
Blueprint: auth_bp

Routes:
  GET  /login
  POST /login            — credential check → CAPTCHA
  POST /verify_captcha   — CAPTCHA → OTP or PIN or dashboard
  POST /verify_otp       — OTP → PIN or dashboard
  POST /verify_pin       — PIN → dashboard
  POST /resend_otp
  GET  /api/check_email  — live email availability check
  POST /signup
  POST /forgot_password
  GET  /reset_password/<token>
  POST /reset_password
  GET  /reset-pin/<token>
  POST /reset-pin
  GET  /logout
  GET  /home             — role-based redirect
"""

import random
import re
import string
import uuid
import os
from datetime import datetime, timedelta

from flask import (
    Blueprint, render_template, request, redirect,
    session, flash, jsonify, url_for,
)
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from apscheduler.schedulers.background import BackgroundScheduler

from conn import mysql, app
from helpers import (
    is_logged_in, require_role,
    encrypt_pii, decrypt_pii,
    encrypt_email, store_email, safe_decrypt_email,
)
from email_config import (
    send_otp_email,
    send_reset_email,
    notify_admins_new_registration,
    send_registration_decision_email,
    send_pin_expiry_email,
)
from task_queue import enqueue   # ← background task queue

bcrypt = Bcrypt(app)

auth_bp = Blueprint("auth_bp", __name__)

SECURITY_PASSWORD_SALT = os.getenv('SECURITY_PASSWORD_SALT', 'iloilo-library-reset-salt-2024')
PIN_RESET_SALT         = os.getenv('PIN_RESET_SALT', 'iloilo-library-pin-reset-salt-2024')
PIN_EXPIRY_DAYS        = 7


# =====================================================================
# SECURE VALID-ID VAULT
# =====================================================================

_VAULT_DIR = os.environ.get(
    'VALID_ID_VAULT',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'valid_id_vault')
)
_ALLOWED_EXTS  = {'jpg', 'jpeg', 'png', 'webp', 'pdf'}
_ALLOWED_MIMES = {'image/jpeg', 'image/png', 'image/webp', 'application/pdf'}
_MAX_ID_BYTES  = 5 * 1024 * 1024   # 5 MB


def _ensure_vault():
    os.makedirs(_VAULT_DIR, exist_ok=True)
    try:
        os.chmod(_VAULT_DIR, 0o700)
    except OSError:
        pass


def _detect_mime(filepath: str) -> str:
    """
    Detect MIME type by reading the file's magic bytes directly.
    No third-party library required — works on any platform.
    Supports: JPEG, PNG, WEBP, PDF.
    Falls back to mimetypes (extension-based) for anything else.
    """
    _SIGNATURES = {
        b'\xff\xd8\xff':          'image/jpeg',
        b'\x89PNG\r\n\x1a\n':    'image/png',
        b'RIFF':                  'image/webp',   # checked further below
        b'%PDF':                  'application/pdf',
    }
    try:
        with open(filepath, 'rb') as f:
            header = f.read(12)
        # WEBP: bytes 0-3 == RIFF and bytes 8-11 == WEBP
        if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
            return 'image/webp'
        for sig, mime in _SIGNATURES.items():
            if sig == b'RIFF':
                continue          # already handled above
            if header[:len(sig)] == sig:
                return mime
    except OSError:
        pass

    # Extension-based fallback
    import mimetypes
    guessed, _ = mimetypes.guess_type(filepath)
    return guessed or 'application/octet-stream'


def _save_valid_id(file_storage) -> str:
    """
    Validate + save uploaded valid-ID file to the secure vault.
    Returns the raw on-disk path (caller must encrypt_pii() before DB).
    Raises ValueError on any validation failure.
    """
    _ensure_vault()

    if not file_storage or not file_storage.filename:
        raise ValueError("No file provided.")

    ext = file_storage.filename.rsplit('.', 1)[-1].lower() if '.' in file_storage.filename else ''
    if ext not in _ALLOWED_EXTS:
        raise ValueError(f"Type '.{ext}' not allowed. Use JPG, PNG, WEBP, or PDF.")

    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > _MAX_ID_BYTES:
        raise ValueError("File too large (max 5 MB).")

    random_name = f"{uuid.uuid4().hex}.{ext}"
    dest        = os.path.join(_VAULT_DIR, random_name)
    file_storage.save(dest)

    try:
        os.chmod(dest, 0o600)
    except OSError:
        pass

    detected = _detect_mime(dest)
    if detected not in _ALLOWED_MIMES:
        os.remove(dest)
        raise ValueError(
            f"File content type '{detected}' is not permitted. "
            "Upload a genuine image or PDF."
        )

    return dest


# =====================================================================
# OTP GENERATION  (3 uppercase letters + 3 digits, e.g. "XKB492")
# =====================================================================

def generate_otp() -> str:
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    digits  = ''.join(random.choices(string.digits, k=3))
    return letters + digits


# =====================================================================
# CAPTCHA GENERATION
# =====================================================================

def generate_captcha() -> dict:
    questions = [
        {
            'q': 'What is the most famous festival of Iloilo City celebrated every January?',
            'a': 'Dinagyang Festival',
            'choices': ['Dinagyang Festival', 'Ati-Atihan Festival', 'MassKara Festival', 'Sinulog Festival'],
        },
        {
            'q': 'The Dinagyang Festival is held in honor of which image of the Child Jesus?',
            'a': 'Santo Niño',
            'choices': ['Santo Niño', 'Black Nazarene', 'Our Lady of Fatima', 'Our Lady of Peñafrancia'],
        },
        {
            'q': 'What is the most famous noodle soup dish from Iloilo?',
            'a': 'La Paz Batchoy',
            'choices': ['La Paz Batchoy', 'Bulalo', 'Sinigang', 'Mami'],
        },
        {
            'q': 'Which district in Iloilo is the origin of Batchoy?',
            'a': 'La Paz',
            'choices': ['La Paz', 'Jaro', 'Molo', 'Mandurriao'],
        },
        {
            'q': 'What famous pancit dish from Iloilo is known for its rich broth and toppings?',
            'a': 'Pancit Molo',
            'choices': ['Pancit Molo', 'Pancit Canton', 'Pancit Habhab', 'Pancit Malabon'],
        },
        {
            'q': 'What Iloilo restaurant is well-known for traditional Filipino dishes and heritage vibes?',
            'a': 'Breakthrough Restaurant',
            'choices': ["Breakthrough Restaurant", "Roberto's", "Netong's Original La Paz Batchoy", "Deco's La Paz Batchoy"],
        },
        {
            'q': 'Which restaurant is famous for its seafood and is located near the coastal area of Iloilo?',
            'a': "Tatoy's Manokan and Seafood",
            'choices': ["Tatoy's Manokan and Seafood", 'JD Bakery Café', 'Spring Palace', 'Monkey Grounds Coffee'],
        },
        {
            'q': 'What popular fast-food chain known for chicken inasal started in Iloilo City?',
            'a': 'Mang Inasal',
            'choices': ['Mang Inasal', 'Jollibee', 'Chowking', 'Greenwich'],
        },
        {
            'q': 'What famous toasted bread delicacy from Iloilo is a popular pasalubong?',
            'a': 'Biscocho',
            'choices': ['Biscocho', 'Ensaymada', 'Pianono', 'Hopia'],
        },
        {
            'q': 'What is the name of the heritage street in Iloilo known for old ancestral houses and historic buildings?',
            'a': 'Calle Real',
            'choices': ['Calle Real', 'Escolta Street', 'Session Road', 'Rizal Street'],
        },
        {
            'q': 'Which district in Iloilo is famous for its heritage mansions and old churches?',
            'a': 'Jaro',
            'choices': ['Jaro', 'Molo', 'Arevalo', 'Lapuz'],
        },
        {
            'q': 'What famous cathedral in Iloilo is also known as the National Shrine of Our Lady of the Candles?',
            'a': 'Jaro Cathedral',
            'choices': ['Jaro Cathedral', 'Molo Church', 'Miagao Church', 'St. Anne Parish'],
        },
        {
            'q': 'What bell tower located across Jaro Cathedral is one of Iloilo\'s iconic heritage landmarks?',
            'a': 'Jaro Belfry',
            'choices': ['Jaro Belfry', 'Molo Belfry', 'Miagao Belfry', 'Santa Barbara Belfry'],
        },
        {
            'q': 'What old mansion in Iloilo is known for its preserved Spanish-era architecture?',
            'a': 'Nelly Garden Mansion',
            'choices': ['Nelly Garden Mansion', 'Molo Mansion', 'Balay na Bato', 'Casa Mariquit'],
        },
        {
            'q': 'What do you call someone from Iloilo?',
            'a': 'Ilonggo',
            'choices': ['Ilonggo', 'Bisaya', 'Waray', 'Kapampangan'],
        },
        {
            'q': 'What language is widely spoken in Iloilo?',
            'a': 'Hiligaynon (Ilonggo)',
            'choices': ['Hiligaynon (Ilonggo)', 'Cebuano', 'Waray', 'Kapampangan'],
        },
        {
            'q': 'Iloilo is often called the "Heart of" what region?',
            'a': 'Western Visayas',
            'choices': ['Western Visayas', 'Luzon', 'Southern Mindanao', 'Northern Visayas'],
        },
    ]
    item = random.choice(questions)
    random.shuffle(item['choices'])
    return {'question': item['q'], 'options': item['choices'], 'answer': item['a']}


# =====================================================================
# PASSWORD RESET TOKEN
# =====================================================================

def generate_reset_token(email: str) -> str:
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return s.dumps(email, salt=SECURITY_PASSWORD_SALT)


def verify_reset_token(token: str, expiration: int = 3600):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        return s.loads(token, salt=SECURITY_PASSWORD_SALT, max_age=expiration)
    except (SignatureExpired, BadSignature):
        return None


# =====================================================================
# PIN RESET TOKEN
# =====================================================================

def generate_pin_reset_token(user_id: int) -> str:
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return s.dumps(user_id, salt=PIN_RESET_SALT)


def verify_pin_reset_token(token: str, expiration: int = 3600):
    s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        return s.loads(token, salt=PIN_RESET_SALT, max_age=expiration)
    except (SignatureExpired, BadSignature):
        return None


# =====================================================================
# PIN EXPIRY EMAIL HELPER
# =====================================================================

def _send_pin_expiry_email_for_user(user_id: int):
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT email_display, firstname FROM users WHERE id=%s", (user_id,)
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            return

        email_enc, firstname_enc = row
        token        = generate_pin_reset_token(user_id)
        token_expiry = datetime.now() + timedelta(hours=1)

        cur.execute("""
            UPDATE users
            SET pin_reset_token=%s, pin_reset_token_expiry=%s
            WHERE id=%s
        """, (token, token_expiry, user_id))
        mysql.connection.commit()
        cur.close()

        from helpers import safe_decrypt_email, safe_decrypt_pii
        email     = safe_decrypt_email(email_enc)
        firstname = safe_decrypt_pii(firstname_enc)

        reset_link = url_for('auth_bp.reset_pin_form', token=token, _external=True)
        # Fire email in background — don't block the login flow
        enqueue(send_pin_expiry_email, email, firstname, reset_link)

    except Exception as e:
        print(f"[PIN Expiry Email] Error: {e}")


# =====================================================================
# PIN CHECK HELPER
# =====================================================================

def _check_pin_after_auth(user_id: int):
    """
    Returns a Flask response object if PIN verification is needed,
    or None if no PIN is set / PIN has expired (expired → email sent, skip PIN).
    """
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT pin_enabled, pin_code, pin_set_at FROM users WHERE id=%s",
        (user_id,)
    )
    pin_row = cur.fetchone()
    cur.close()

    pin_enabled = bool(pin_row[0]) if pin_row else False
    pin_code    = pin_row[1]       if pin_row else None
    pin_set_at  = pin_row[2]       if pin_row else None

    if not pin_enabled or not pin_code:
        return None

    pin_expired = (
        pin_set_at is None or
        (datetime.now() - pin_set_at) > timedelta(days=PIN_EXPIRY_DAYS)
    )

    if pin_expired:
        _send_pin_expiry_email_for_user(user_id)
        return None

    # Store user_id so /verify_pin can find it, then show PIN prompt
    session["pin_user"] = user_id
    return render_template('admins/login.html', show_pin_modal=True)


# =====================================================================
# OTP CLEANUP SCHEDULER
# =====================================================================

def cleanup_expired_otps():
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE users
            SET otp_code = NULL, otp_expiry = NULL
            WHERE otp_expiry IS NOT NULL AND otp_expiry < %s
        """, (datetime.now(),))
        mysql.connection.commit()
        cur.close()
        print(f"[OTP Cleanup] Done at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"[OTP Cleanup] Error: {e}")
        try:
            mysql.connection.rollback()
        except Exception:
            pass


if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup_expired_otps, "interval", minutes=1)
    scheduler.start()


# =====================================================================
# ACTIVE STATUS HOOK
# =====================================================================

@app.before_request
def update_last_seen():
    if "user_id" in session:
        # Run in background — don't block the current request
        enqueue(_do_update_last_seen, session["user_id"])


def _do_update_last_seen(user_id: int):
    """Background worker: update last_seen + status without blocking HTTP."""
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE users SET last_seen=%s, status=%s WHERE id=%s",
            (datetime.now(), "active", user_id),
        )
        mysql.connection.commit()
        cur.close()
    except Exception:
        pass


# =====================================================================
# LOGIN
# =====================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect('/home')

    if request.method == 'POST' and 'email' in request.form:
        email    = request.form['email'].strip().lower()
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id, username, firstname, lastname, password,
                   failed_attempts, is_locked, lock_until, created_at, role, is_approved
            FROM users WHERE username=%s
        """, (encrypt_email(email),))
        user = cur.fetchone()
        cur.close()

        if not user:
            flash("Invalid email or password!", "danger")
            return redirect('/login')

        # FIX: column index 10 = is_approved
        if not user[10]:
            return render_template('admins/login.html', show_pending_modal=True)

        user_id         = user[0]
        hashed_password = user[4]
        failed_attempts = user[5]
        is_locked       = user[6]
        lock_until      = user[7]

        # Lock check
        if is_locked and lock_until:
            if isinstance(lock_until, str):
                try:
                    lock_until = datetime.strptime(lock_until, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    lock_until = None
            if isinstance(lock_until, datetime) and lock_until > datetime.now():
                flash("Account locked due to multiple failed attempts. Try again later.", "danger")
                return redirect('/login')
            else:
                # Lock expired — reset it
                cur = mysql.connection.cursor()
                cur.execute(
                    "UPDATE users SET is_locked=0, failed_attempts=0, lock_until=NULL WHERE id=%s",
                    (user_id,),
                )
                mysql.connection.commit()
                cur.close()
                failed_attempts = 0

        if not bcrypt.check_password_hash(hashed_password, password):
            failed_attempts = int(failed_attempts or 0) + 1
            cur = mysql.connection.cursor()
            if failed_attempts >= 5:
                new_lock_until = datetime.now() + timedelta(minutes=15)
                cur.execute("""
                    UPDATE users SET failed_attempts=%s, is_locked=1, lock_until=%s WHERE id=%s
                """, (failed_attempts, new_lock_until, user_id))
                flash("Too many failed attempts. Account locked for 15 minutes.", "danger")
            else:
                cur.execute(
                    "UPDATE users SET failed_attempts=%s WHERE id=%s",
                    (failed_attempts, user_id),
                )
                flash("Invalid email or password!", "danger")
            mysql.connection.commit()
            cur.close()
            return redirect('/login')

        # Credentials OK → show CAPTCHA
        session['captcha_user']   = user_id
        session['captcha_email']  = email
        captcha = generate_captcha()
        session['captcha_answer'] = str(captcha['answer'])

        flash("Please complete the CAPTCHA verification", "info")
        return render_template('admins/login.html', show_captcha_modal=True, captcha=captcha)

    return render_template('admins/login.html')


# =====================================================================
# CAPTCHA VERIFICATION
# =====================================================================

@auth_bp.route("/verify_captcha", methods=["POST"])
def verify_captcha():
    if "captcha_user" not in session:
        flash("Session expired. Please login again.", "danger")
        return redirect('/login')

    captcha_answer = request.form.get("captcha_answer", "").strip()
    correct_answer = session.get("captcha_answer", "")
    user_id        = session["captcha_user"]
    email          = session["captcha_email"]

    if captcha_answer != correct_answer:
        captcha = generate_captcha()
        session['captcha_answer'] = str(captcha['answer'])
        flash("Incorrect CAPTCHA. Please try again.", "danger")
        return render_template('admins/login.html', show_captcha_modal=True, captcha=captcha)

    # Check if user has OTP enabled
    cur = mysql.connection.cursor()
    cur.execute("SELECT otp_enabled FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    otp_enabled = bool(row[0]) if row else False

    # Store for resend support
    session["resend_user"]  = user_id
    session["resend_email"] = email

    # Reset lock/attempts on successful CAPTCHA
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE users SET failed_attempts=0, is_locked=0, lock_until=NULL WHERE id=%s
    """, (user_id,))
    mysql.connection.commit()
    cur.close()

    # Clear CAPTCHA session keys
    session.pop("captcha_user",   None)
    session.pop("captcha_email",  None)
    session.pop("captcha_answer", None)

    if otp_enabled:
        otp        = generate_otp()
        expiry     = datetime.now() + timedelta(minutes=5)
        hashed_otp = bcrypt.generate_password_hash(otp).decode('utf-8')

        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE users SET otp_code=%s, otp_expiry=%s WHERE id=%s",
            (hashed_otp, expiry, user_id)
        )
        mysql.connection.commit()
        cur.close()

        # Enqueue email in background — response returns immediately
        enqueue(send_otp_email, email, otp)
        session["otp_user"]  = user_id
        session["otp_email"] = email
        flash("OTP sent to your email!", "success")
        return render_template('admins/login.html', show_otp_modal=True)

    # OTP disabled — check PIN or go straight to dashboard
    pin_response = _check_pin_after_auth(user_id)
    if pin_response:
        return pin_response

    cur = mysql.connection.cursor()
    cur.execute("SELECT username, role FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()

    session["user_id"]     = user_id
    session["username"]    = row[0]
    session["role"]        = row[1]
    session.permanent      = True
    session["show_loader"] = True

    return redirect('/home')


# =====================================================================
# OTP VERIFICATION
# =====================================================================

@auth_bp.route("/verify_otp", methods=["POST"])
def verify_otp():
    if "otp_user" not in session:
        flash("Session expired. Please login again.", "danger")
        return redirect('/login')

    otp_input = request.form.get("otp", "").strip().upper()
    user_id   = session["otp_user"]

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT otp_code, otp_expiry, username, role, is_active, is_approved
        FROM users WHERE id=%s
    """, (user_id,))
    data = cur.fetchone()
    cur.close()

    if not data:
        flash("Invalid session.", "danger")
        return redirect('/login')

    otp_code, otp_expiry, username, role, is_active, is_approved = data

    if not is_approved:
        flash("Your account is still pending admin approval.", "warning")
        session.pop("otp_user", None)
        session.pop("otp_email", None)
        return redirect('/login')

    if not is_active:
        flash("Your account has been deactivated. Contact the library to reactivate.", "danger")
        session.pop("otp_user", None)
        session.pop("otp_email", None)
        return redirect('/login')

    if otp_code is None or otp_expiry is None:
        session.pop("otp_user", None)
        return render_template('admins/login.html', show_otp_modal=True, otp_expired=True)

    if isinstance(otp_expiry, str):
        otp_expiry = datetime.fromisoformat(otp_expiry)

    if otp_expiry < datetime.now():
        cur = mysql.connection.cursor()
        cur.execute("UPDATE users SET otp_code=NULL, otp_expiry=NULL WHERE id=%s", (user_id,))
        mysql.connection.commit()
        cur.close()
        session.pop("otp_user", None)
        return render_template('admins/login.html', show_otp_modal=True, otp_expired=True)

    if not bcrypt.check_password_hash(otp_code, otp_input):
        flash("Invalid OTP. Please try again.", "danger")
        return render_template('admins/login.html', show_otp_modal=True)

    # OTP valid — clear it
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE users
        SET failed_attempts=0, is_locked=0,
            otp_code=NULL, otp_expiry=NULL,
            status=%s, last_seen=%s
        WHERE id=%s
    """, ("active", datetime.now(), user_id))
    mysql.connection.commit()
    cur.close()

    session.pop("otp_user",  None)
    session.pop("otp_email", None)

    pin_response = _check_pin_after_auth(user_id)
    if pin_response:
        return pin_response

    session["user_id"]     = user_id
    session["username"]    = username
    session["role"]        = role
    session.permanent      = True
    session["show_loader"] = True

    return redirect('/home')


# =====================================================================
# PIN VERIFICATION
# =====================================================================

@auth_bp.route('/verify_pin', methods=['POST'])
def verify_pin():
    data    = request.get_json(silent=True) or {}
    pin_in  = str(data.get('pin', '')).strip()
    user_id = session.get('pin_user')

    if not user_id:
        return jsonify({'success': False, 'message': 'Session expired. Please login again.'}), 400

    if not pin_in or len(pin_in) != 6 or not pin_in.isdigit():
        return jsonify({'success': False, 'message': 'PIN must be exactly 6 digits.'}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT pin_code, username, role FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()

    if not row or not row[0]:
        return jsonify({'success': False, 'message': 'PIN not configured.'}), 400

    if not bcrypt.check_password_hash(row[0], pin_in):
        return jsonify({'success': False, 'message': 'Incorrect PIN. Please try again.'})

    session.pop('pin_user', None)
    session["user_id"]     = user_id
    session["username"]    = row[1]
    session["role"]        = row[2]
    session.permanent      = True
    session["show_loader"] = True

    return jsonify({'success': True, 'redirect': '/home'})


# =====================================================================
# RESEND OTP
# =====================================================================

@auth_bp.route("/resend_otp", methods=["POST"])
def resend_otp():
    user_id = session.get("resend_user")
    email   = session.get("resend_email")
    if not user_id or not email:
        return jsonify({'success': False, 'message': 'Session expired. Please login again.'}), 400

    otp        = generate_otp()
    expiry     = datetime.now() + timedelta(minutes=5)
    hashed_otp = bcrypt.generate_password_hash(otp).decode('utf-8')

    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE users SET otp_code=%s, otp_expiry=%s WHERE id=%s",
        (hashed_otp, expiry, user_id)
    )
    mysql.connection.commit()
    cur.close()

    # Enqueue email — respond immediately
    enqueue(send_otp_email, email, otp)
    session["otp_user"]  = user_id
    session["otp_email"] = email
    return jsonify({'success': True})


# =====================================================================
# EMAIL AVAILABILITY CHECK
# =====================================================================

@auth_bp.route('/api/check_email')
def check_email():
    """Live availability check used by the signup form (debounced)."""
    email = request.args.get('email', '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'taken': False})
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (encrypt_email(email),))
    taken = cur.fetchone() is not None
    cur.close()
    return jsonify({'taken': taken})


# =====================================================================
# SIGNUP
# =====================================================================

@auth_bp.route('/signup', methods=['POST'])
def signup():
    # ── 1. Collect all wizard fields ──────────────────────────────────
    firstname       = request.form.get('firstname',       '').strip()
    lastname        = request.form.get('lastname',        '').strip()
    email           = request.form.get('email',           '').strip().lower()
    password        = request.form.get('password',        '').strip()
    gender          = request.form.get('gender',          '').strip()
    phone           = request.form.get('phone',           '').strip()
    school          = request.form.get('school',          '').strip()
    city            = request.form.get('city',            '').strip()
    province        = request.form.get('province',        '').strip()
    education_level = request.form.get('education_level', '').strip()
    occupation      = request.form.get('occupation',      '').strip()
    is_government   = 1 if request.form.get('is_government') == '1' else 0
    office_phone    = request.form.get('office_phone',    '').strip()
    role            = request.form.get('role', 'user').strip()
    age             = request.form.get('age', '').strip()
    if role not in ('admin', 'librarian', 'user'):
        role = 'user'

    # ── 2. Admin / librarian path ──────────────────────────────────────
    if role in ('admin', 'librarian'):
        if session.get('role') != 'admin':
            flash("Unauthorized: Only admins can create staff accounts.", "danger")
            return redirect('/')

        hashed         = bcrypt.generate_password_hash(password).decode('utf-8')
        enc_username   = encrypt_email(email)
        enc_email_disp = store_email(email)
        enc_firstname  = encrypt_pii(firstname)
        enc_lastname   = encrypt_pii(lastname)

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s", (enc_username,))
        if cur.fetchone():
            cur.close()
            flash("Email already exists!", "danger")
            return redirect('/admin/home')

        cur.execute("""
            INSERT INTO users
                (username, email_display, firstname, lastname, password, role,
                 failed_attempts, is_locked, status, is_active, is_approved)
            VALUES (%s,%s,%s,%s,%s,%s,0,0,'offline',1,1)
        """, (enc_username, enc_email_disp, enc_firstname, enc_lastname, hashed, role))
        mysql.connection.commit()
        cur.close()
        flash(f"{role.capitalize()} account created successfully!", "success")
        return redirect('/admin/home')

    # ── 3. Server-side validation ──────────────────────────────────────
    PW_PATTERN = (
        r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)'
        r'(?=.*[@$!%*?&_#^])[A-Za-z\d@$!%*?&_#^]{8,}$'
    )

    def _err(msg, email_err=False):
        flash(msg, "danger")
        return render_template(
            'admins/login.html',
            show_signup_modal=True,
            signup_email_error=email_err,
            prefill_email=email,
        )

    if len(firstname) < 2:
        return _err("First name must be at least 2 characters.")
    if len(lastname) < 2:
        return _err("Last name must be at least 2 characters.")
    if not gender:
        return _err("Please select a gender.")
    if not phone:
        return _err("Phone number is required.")
    if not email or '@' not in email:
        return _err("A valid email address is required.", email_err=True)
    if not password or not re.match(PW_PATTERN, password):
        return _err(
            "Password must be ≥8 characters and contain uppercase, "
            "lowercase, a number, and a special character (@$!%*?&_#^)."
        )

    # ── 4. Valid ID upload ─────────────────────────────────────────────
    valid_id_path_enc = None
    id_file = request.files.get('valid_id')

    if id_file and id_file.filename:
        try:
            raw_path = _save_valid_id(id_file)
            valid_id_path_enc = encrypt_pii(raw_path)
        except ValueError as exc:
            return _err(f"ID upload error: {exc}")
        except Exception as exc:
            app.logger.error(f"[Signup] ID upload failed: {exc}")
            return _err("Could not save your ID file. Please try again.")

    # ── 5. Duplicate email check ───────────────────────────────────────
    enc_username   = encrypt_email(email)
    enc_email_disp = store_email(email)

    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (enc_username,))
    if cur.fetchone():
        cur.close()
        # Clean up uploaded file — account won't be created
        if valid_id_path_enc:
            try:
                raw = decrypt_pii(valid_id_path_enc)
                if raw and os.path.isfile(raw):
                    os.remove(raw)
            except Exception:
                pass
        return render_template(
            'admins/login.html',
            show_signup_modal=True,
            signup_email_error=True,
            prefill_email=email,
        )

    # ── 6. Encrypt ALL PII fields ──────────────────────────────────────
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')

    enc_firstname  = encrypt_pii(firstname)
    enc_lastname   = encrypt_pii(lastname)
    enc_gender     = encrypt_pii(gender)          if gender          else None
    enc_phone      = encrypt_pii(phone)            if phone           else None
    enc_school     = encrypt_pii(school)           if school          else None
    enc_city       = encrypt_pii(city)             if city            else None
    enc_province   = encrypt_pii(province)         if province        else None
    enc_education  = encrypt_pii(education_level)  if education_level else None
    enc_occupation = encrypt_pii(occupation)       if occupation      else None
    enc_off_phone  = encrypt_pii(office_phone)     if office_phone    else None
    enc_age        = encrypt_pii(age)              if age             else None  # FIX: was missing

    # ── 7. Insert user ─────────────────────────────────────────────────
    cur.execute("""
        INSERT INTO users (
            username,
            email_display,
            firstname,
            lastname,
            password,
            role,
            failed_attempts,
            is_locked,
            status,
            is_active,
            is_approved,
            gender,
            phone_number,
            school,
            city,
            province,
            education_level,
            occupation,
            is_government,
            office_phone,
            valid_id_path,
            age
        ) VALUES (
            %s, %s, %s, %s, %s,
            'user', 0, 0, 'offline', 0, 0,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s
        )
    """, (
        enc_username,
        enc_email_disp,
        enc_firstname,
        enc_lastname,
        hashed,
        enc_gender,
        enc_phone,
        enc_school,
        enc_city,
        enc_province,
        enc_education,
        enc_occupation,
        is_government,
        enc_off_phone,
        valid_id_path_enc,
        enc_age,
    ))
    mysql.connection.commit()
    new_user_id = cur.lastrowid
    # Store blind indexes for fast search
    from helpers import name_blind_index, phone_blind_index
    _n_hash = name_blind_index(firstname, lastname)
    _p_hash = phone_blind_index(phone) if phone else None
    cur.execute(
        "UPDATE users SET name_index=%s, phone_index=%s WHERE id=%s",
        (_n_hash, _p_hash, new_user_id)
    )
    mysql.connection.commit()
    
    # ── 8. Pending approval record ─────────────────────────────────────
    cur.execute("""
        INSERT INTO account_requests
            (user_id, username, request_type, reason, status)
        VALUES (%s, %s, 'register',
                'New user registration awaiting admin approval.', 'pending')
    """, (new_user_id, enc_username))
    mysql.connection.commit()
    cur.close()

    # ── 9. Notify admins in background (non-fatal) ─────────────────────
    enqueue(notify_admins_new_registration, firstname, lastname, email)

    return render_template('admins/login.html', show_pending_modal=True)


# =====================================================================
# FORGOT / RESET PASSWORD
# =====================================================================

@auth_bp.route('/forgot_password', methods=['POST'])
def forgot_password():
    email = request.form.get('email', '').strip().lower()

    if not email:
        flash("Please enter your email address.", "danger")
        return redirect('/login')

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT id, email_display FROM users WHERE username = %s",
        (encrypt_email(email),)
    )
    user = cur.fetchone()

    if not user:
        cur.close()
        flash("If that email is registered, a reset link has been sent.", "info")
        return redirect('/login')

    user_id      = user[0]
    raw_email    = safe_decrypt_email(user[1]) or email
    token        = generate_reset_token(raw_email)
    token_expiry = datetime.now() + timedelta(hours=1)

    cur.execute("""
        UPDATE users SET reset_token=%s, reset_token_expiry=%s WHERE id=%s
    """, (token, token_expiry, user_id))
    mysql.connection.commit()
    cur.close()

    reset_link = url_for('auth_bp.reset_password_form', token=token, _external=True)

    # Enqueue email — respond immediately regardless
    enqueue(send_reset_email, raw_email, reset_link)
    flash("If that email is registered, a reset link has been sent.", "info")
    return redirect('/login')


@auth_bp.route('/reset_password/<token>', methods=['GET'])
def reset_password_form(token):
    email = verify_reset_token(token, expiration=3600)
    if not email:
        flash("This password reset link is invalid or has expired.", "danger")
        return redirect('/login')

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id FROM users
        WHERE username=%s AND reset_token=%s AND reset_token_expiry > %s
    """, (encrypt_email(email), token, datetime.now()))
    user = cur.fetchone()
    cur.close()

    if not user:
        flash("This password reset link is invalid or has already been used.", "danger")
        return redirect('/login')

    return render_template('reset_password.html', token=token, email=email)


@auth_bp.route('/reset_password', methods=['POST'])
def reset_password():
    token        = request.form.get('token', '').strip()
    new_password = request.form.get('new_password', '').strip()
    confirm_pwd  = request.form.get('confirm_password', '').strip()

    email = verify_reset_token(token, expiration=3600)
    if not email:
        flash("Invalid or expired reset link.", "danger")
        return redirect('/login')

    if new_password != confirm_pwd:
        flash("Passwords do not match.", "danger")
        return render_template('reset_password.html', token=token, email=email)

    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_#^])[A-Za-z\d@$!%*?&_#^]{8,}$'
    if not re.match(pattern, new_password):
        flash(
            "Password must be at least 8 characters and contain uppercase, "
            "lowercase, number, and special character.",
            "danger",
        )
        return render_template('reset_password.html', token=token, email=email)

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id FROM users
        WHERE username=%s AND reset_token=%s AND reset_token_expiry > %s
    """, (encrypt_email(email), token, datetime.now()))
    user = cur.fetchone()

    if not user:
        cur.close()
        flash("This reset link has already been used or has expired.", "danger")
        return redirect('/login')

    hashed = bcrypt.generate_password_hash(new_password).decode('utf-8')
    cur.execute("""
        UPDATE users SET password=%s, reset_token=NULL, reset_token_expiry=NULL,
               failed_attempts=0, is_locked=0, lock_until=NULL
        WHERE id=%s
    """, (hashed, user[0]))
    mysql.connection.commit()
    cur.close()

    flash("Your password has been reset successfully! You can now log in.", "success")
    return redirect('/login')


# =====================================================================
# PIN RESET (via expiry email link)
# =====================================================================

@auth_bp.route('/reset-pin/<token>', methods=['GET'])
def reset_pin_form(token):
    user_id = verify_pin_reset_token(token)
    if not user_id:
        flash("This PIN reset link is invalid or has expired.", "danger")
        return redirect('/login')

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id FROM users
        WHERE id=%s AND pin_reset_token=%s AND pin_reset_token_expiry > %s
    """, (user_id, token, datetime.now()))
    user = cur.fetchone()
    cur.close()

    if not user:
        flash("This PIN reset link has already been used or expired.", "danger")
        return redirect('/login')

    return render_template('reset_pin.html', token=token)


@auth_bp.route('/reset-pin', methods=['POST'])
def reset_pin():
    token   = request.form.get('token', '').strip()
    new_pin = request.form.get('pin', '').strip()

    user_id = verify_pin_reset_token(token)
    if not user_id:
        flash("Invalid or expired PIN reset link.", "danger")
        return redirect('/login')

    if not new_pin.isdigit() or len(new_pin) != 6:
        flash("PIN must be exactly 6 digits.", "danger")
        return render_template('reset_pin.html', token=token)

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id FROM users
        WHERE id=%s AND pin_reset_token=%s AND pin_reset_token_expiry > %s
    """, (user_id, token, datetime.now()))
    user = cur.fetchone()

    if not user:
        cur.close()
        flash("This link has already been used or expired.", "danger")
        return redirect('/login')

    hashed = bcrypt.generate_password_hash(new_pin).decode('utf-8')
    cur.execute("""
        UPDATE users
        SET pin_code=%s, pin_set_at=%s,
            pin_reset_token=NULL, pin_reset_token_expiry=NULL,
            pin_enabled=1
        WHERE id=%s
    """, (hashed, datetime.now(), user_id))
    mysql.connection.commit()
    cur.close()

    flash("PIN updated successfully! You can now log in.", "success")
    return redirect('/login')


# =====================================================================
# FORGOT PIN — 3-step flow on login page (password → OTP → new PIN)
# =====================================================================

@auth_bp.route('/forgot_pin/verify_password', methods=['POST'])
def forgot_pin_verify_password():
    user_id = session.get('pin_user')
    if not user_id:
        return jsonify({'success': False, 'message': 'Session expired. Please log in again.'}), 400

    data     = request.get_json(silent=True) or {}
    password = data.get('password', '').strip()

    if not password:
        return jsonify({'success': False, 'message': 'Password is required.'}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT password, email_display FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()

    if not row or not bcrypt.check_password_hash(row[0], password):
        return jsonify({'success': False, 'message': 'Incorrect password.'}), 400

    otp        = generate_otp()
    expiry     = datetime.now() + timedelta(minutes=5)
    hashed_otp = bcrypt.generate_password_hash(otp).decode('utf-8')

    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE users SET otp_code=%s, otp_expiry=%s WHERE id=%s",
        (hashed_otp, expiry, user_id)
    )
    mysql.connection.commit()
    cur.close()

    email = safe_decrypt_email(row[1])
    # Enqueue email — return response immediately
    enqueue(send_otp_email, email, otp)
    session['fp_otp_user'] = user_id
    at   = email.find('@')
    hint = email[:2] + '***' + email[at:] if at > 2 else email
    return jsonify({'success': True, 'email_hint': hint})


@auth_bp.route('/forgot_pin/verify_otp', methods=['POST'])
def forgot_pin_verify_otp():
    user_id = session.get('fp_otp_user')
    if not user_id:
        return jsonify({'success': False, 'message': 'Session expired.'}), 400

    data      = request.get_json(silent=True) or {}
    otp_input = data.get('otp', '').strip().upper()

    cur = mysql.connection.cursor()
    cur.execute("SELECT otp_code, otp_expiry FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()

    if not row or not row[0]:
        return jsonify({'success': False, 'message': 'OTP not found. Please resend.'}), 400

    otp_code, otp_expiry = row
    if isinstance(otp_expiry, str):
        otp_expiry = datetime.fromisoformat(otp_expiry)

    if otp_expiry < datetime.now():
        return jsonify({'success': False, 'message': 'OTP has expired. Please start over.'}), 400

    if not bcrypt.check_password_hash(otp_code, otp_input):
        return jsonify({'success': False, 'message': 'Invalid OTP. Please try again.'}), 400

    cur = mysql.connection.cursor()
    cur.execute("UPDATE users SET otp_code=NULL, otp_expiry=NULL WHERE id=%s", (user_id,))
    mysql.connection.commit()
    cur.close()

    session['fp_pin_verified'] = user_id
    return jsonify({'success': True})


@auth_bp.route('/forgot_pin/set_new', methods=['POST'])
def forgot_pin_set_new():
    user_id = session.get('fp_pin_verified')
    if not user_id:
        return jsonify({'success': False, 'message': 'Session expired or OTP not verified.'}), 400

    data    = request.get_json(silent=True) or {}
    new_pin = str(data.get('pin', '')).strip()

    if not new_pin.isdigit() or len(new_pin) != 6:
        return jsonify({'success': False, 'message': 'PIN must be exactly 6 digits.'}), 400

    hashed = bcrypt.generate_password_hash(new_pin).decode('utf-8')
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE users
            SET pin_code=%s, pin_enabled=1, pin_set_at=%s,
                pin_reset_token=NULL, pin_reset_token_expiry=NULL
            WHERE id=%s
        """, (hashed, datetime.now(), user_id))
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

    session.pop('fp_otp_user',     None)
    session.pop('fp_pin_verified', None)

    return jsonify({'success': True})


# =====================================================================
# LOGOUT  &  HOME ROUTER
# =====================================================================

@auth_bp.route('/logout')
def logout():
    if "user_id" in session:
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                "UPDATE users SET status=%s, last_seen=%s WHERE id=%s",
                ("offline", datetime.now(), session["user_id"]),
            )
            mysql.connection.commit()
            cur.close()
        except Exception:
            pass
    session.clear()
    flash("Logged out successfully", "success")
    return redirect('/login')


@auth_bp.route('/home')
def home():
    if not is_logged_in():
        flash("Please login first", "danger")
        return redirect('/login')

    role = session.get('role')
    if role == 'admin':
        return redirect('/admin/home')
    elif role == 'librarian':
        return redirect('/librarian/home')
    elif role == 'user':
        return redirect('/user/home')
    else:
        flash("Unknown role. Please contact the administrator.", "danger")
        return redirect('/logout')