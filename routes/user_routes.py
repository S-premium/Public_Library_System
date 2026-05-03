"""
routes/user_routes.py
----------------------
Blueprint: user_bp

All authenticated user pages and APIs:
  - Home, Browse, About, Notifications
  - Favorites, Search History, Appearance, Storage
  - Profile / Settings / Change Password
  - Event Calendar, Borrowed Books, Borrow History
  - Account Requests (deactivate / delete / renew)
  - Recent Activity
  - MFA (OTP + PIN)
  - Valid ID Upload & View
"""

import os
import re
from datetime import datetime, timedelta
from PIL import Image
import io

from flask import (
    Blueprint, render_template, request, redirect,
    session, flash, jsonify, send_file, abort,
)
from flask_bcrypt import Bcrypt

from conn import mysql, app
from helpers import (
    is_logged_in, require_role,
    encrypt_data, safe_decrypt, fmt_dt,
    encrypt_pii, safe_decrypt_pii,
    encrypt_email, safe_decrypt_email,
    calc_storage,
    save_search_history,
    BOOK_INVENTORY_QUERY,
    build_book_data,
)
from authentication.authentication import _save_valid_id

bcrypt = Bcrypt(app)

user_bp = Blueprint("user_bp", __name__)


# ── Shared user-data loader ───────────────────────────────────────────

def _load_user(user_id: int) -> dict:
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT firstname, lastname, email_display, phone_number,
               city, province, age, gender,
               school, education_level, occupation, is_government,
               office_phone, created_at, valid_id_path
        FROM users WHERE id=%s
    """, (user_id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        return {}

    city     = safe_decrypt_pii(row[4]) if row[4] else ''
    province = safe_decrypt_pii(row[5]) if row[5] else ''

    return {
        'firstname':       safe_decrypt_pii(row[0]) if row[0] else '',
        'lastname':        safe_decrypt_pii(row[1]) if row[1] else '',
        'email':           safe_decrypt_email(row[2]) if row[2] else '',
        'phone':           safe_decrypt_pii(row[3]) if row[3] else '',
        'city':            city,
        'province':        province,
        'address':         ', '.join(filter(None, [city, province])),
        'age':             safe_decrypt_pii(str(row[6])) if row[6] is not None else '',
        'gender':          safe_decrypt_pii(row[7]) if row[7] else '',
        'school':          safe_decrypt_pii(row[8]) if row[8] else '',
        'education_level': safe_decrypt_pii(row[9]) if row[9] else '',
        'occupation':      safe_decrypt_pii(row[10]) if row[10] else '',
        'is_government':   bool(row[11]) if row[11] is not None else False,
        'office_phone':    safe_decrypt_pii(row[12]) if row[12] else '',
        'member_since':    fmt_dt(row[13], '%B %d, %Y') if row[13] else '—',
        'valid_id_path':   safe_decrypt_pii(row[14]) if row[14] else '',
    }


# =====================================================================
# PAGES
# =====================================================================

@user_bp.route('/user/home')
def user_home():
    if not is_logged_in() or require_role('user'):
        flash("Unauthorized access", "danger")
        return redirect('/')

    show_loader = 'show_loader' in session
    session.pop('show_loader', None)
    return render_template("users/user_home.html",
        active_page='home',
        user=_load_user(session['user_id']),
        show_loader=show_loader
    )


@user_bp.route('/user/browse')
def user_browse():
    if not is_logged_in() or require_role('user'):
        flash("Please login first", "danger")
        return redirect('/')
    return render_template("users/books.html", user=_load_user(session['user_id']))


@user_bp.route('/about')
def about():
    if not is_logged_in() or require_role('user'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template('users/aboutus.html', active_page='about', user=_load_user(session['user_id']))


@user_bp.route('/user/notifications')
def user_notifications():
    if not is_logged_in() or require_role('user'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("users/notification.html", user=_load_user(session['user_id']))


@user_bp.route('/user/event')
def user_event():
    if not is_logged_in() or require_role('user'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("users/calendar_event.html", user=_load_user(session['user_id']))


@user_bp.route('/user/borrowed')
def user_borrowed():
    if not is_logged_in() or require_role('user'):
        flash("Please login first", "danger")
        return redirect('/')
    return render_template("users/borrowed_books.html", active_page='borrowed', user=_load_user(session['user_id']))


@user_bp.route('/user/borrow-history')
def user_borrow_history():
    if not is_logged_in() or require_role('user'):
        flash("Please login first", "danger")
        return redirect('/')
    return render_template("users/borrow_history.html", user=_load_user(session['user_id']))


@user_bp.route('/user/edit_profile')
def edit_profile():
    if not is_logged_in() or require_role('user'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("users/edit_profile.html", user=_load_user(session['user_id']))


@user_bp.route('/user/settings')
def user_settings():
    if not is_logged_in() or require_role('user'):
        flash("Unauthorized access", "danger")
        return redirect('/')

    user_id = session['user_id']
    user    = _load_user(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect('/')

    user['username'] = user.get('email', '')

    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM library_cards WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    user['total_borrowed'] = row[0] if row else 0

    return render_template('users/settings.html', user=user)


# =====================================================================
# VALID ID — UPLOAD & VIEW
# =====================================================================

@user_bp.route('/user/upload_valid_id', methods=['POST'])
def upload_valid_id():
    if not is_logged_in() or require_role('user'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    user_id = session['user_id']
    file    = request.files.get('valid_id')

    if not file or not file.filename:
        return jsonify({'success': False, 'message': 'No file selected.'}), 400

    try:
        raw_path       = _save_valid_id(file)
        encrypted_path = encrypt_pii(raw_path)

        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE users SET valid_id_path=%s WHERE id=%s",
            (encrypted_path, user_id)
        )
        mysql.connection.commit()
        cur.close()

        return jsonify({'success': True, 'message': 'Valid ID uploaded successfully.'}), 200

    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@user_bp.route('/user/valid-id/view')
def view_valid_id():
    if not is_logged_in() or require_role('user'):
        return abort(401)

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT valid_id_path FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()

    if not row or not row[0]:
        return abort(404)

    file_path = safe_decrypt_pii(row[0])
    if not file_path or not os.path.exists(file_path):
        return abort(404)

    return send_file(file_path)


# =====================================================================
# NOTIFICATIONS API
# =====================================================================

@user_bp.route('/api/user/notifications')
def get_user_notifications():
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    cur     = mysql.connection.cursor()
    cur.execute("""
        SELECT a.id, a.title, a.body, a.category, a.pinned, a.author, a.created_at
        FROM announcements a
        WHERE a.id NOT IN (
            SELECT announcement_id FROM notification_reads
            WHERE user_id=%s AND dismissed=1
        )
        ORDER BY a.pinned DESC, a.created_at DESC LIMIT 30
    """, (user_id,))
    rows = cur.fetchall()

    cur.execute("""
        SELECT announcement_id FROM notification_reads WHERE user_id=%s AND dismissed=0
    """, (user_id,))
    read_ids = {r[0] for r in cur.fetchall()}
    cur.close()

    notifications = [
        {
            'id': r[0], 'title': r[1], 'body': r[2], 'category': r[3],
            'pinned': bool(r[4]), 'author': r[5],
            'created_at': r[6].isoformat() if r[6] else '',
            'read': r[0] in read_ids,
        }
        for r in rows
    ]
    return jsonify({
        'notifications': notifications,
        'unread_count': sum(1 for n in notifications if not n['read']),
    })


@user_bp.route('/api/user/notifications/<int:notif_id>/read', methods=['POST'])
def mark_notification_read(notif_id):
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("INSERT IGNORE INTO notification_reads (user_id, announcement_id) VALUES (%s,%s)",
                (user_id, notif_id))
    mysql.connection.commit()
    cur.close()
    return jsonify({'success': True})


@user_bp.route('/api/user/notifications/read-all', methods=['POST'])
def mark_all_notifications_read():
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id FROM announcements WHERE id NOT IN (
            SELECT announcement_id FROM notification_reads WHERE user_id=%s AND dismissed=1
        )
    """, (user_id,))
    for (ann_id,) in cur.fetchall():
        cur.execute("""
            INSERT INTO notification_reads (user_id, announcement_id, dismissed)
            VALUES (%s,%s,0)
            ON DUPLICATE KEY UPDATE read_at=IF(dismissed=0, CURRENT_TIMESTAMP, read_at)
        """, (user_id, ann_id))
    mysql.connection.commit()
    cur.close()
    return jsonify({'success': True})


@user_bp.route('/api/user/notifications/<int:notif_id>/delete', methods=['POST'])
def delete_user_notification(notif_id):
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO notification_reads (user_id, announcement_id, dismissed)
        VALUES (%s,%s,1)
        ON DUPLICATE KEY UPDATE dismissed=1
    """, (user_id, notif_id))
    mysql.connection.commit()
    cur.close()
    return jsonify({'success': True})


@user_bp.route('/api/user/notifications/<int:notif_id>/unread', methods=['POST'])
def mark_notification_unread(notif_id):
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        DELETE FROM notification_reads WHERE user_id=%s AND announcement_id=%s AND dismissed=0
    """, (user_id, notif_id))
    mysql.connection.commit()
    cur.close()
    return jsonify({'success': True})


# =====================================================================
# BOOKS API
# =====================================================================

@user_bp.route('/api/books')
def api_books():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    cursor = mysql.connection.cursor()
    cursor.execute(BOOK_INVENTORY_QUERY)
    rows = cursor.fetchall()
    cursor.close()
    return jsonify({'books': build_book_data(rows)})


# =====================================================================
# FAVORITES
# =====================================================================

@user_bp.route('/api/user/favorites', methods=['GET'])
def get_favorites():
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT book_id FROM user_favorites WHERE user_id=%s ORDER BY created_at ASC", (user_id,))
    rows = cur.fetchall()
    cur.close()
    return jsonify({'favorites': [r[0] for r in rows]})


@user_bp.route('/api/user/favorites/<int:book_id>', methods=['POST'])
def add_favorite(book_id):
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM books WHERE id=%s", (book_id,))
    if not cur.fetchone():
        cur.close()
        return jsonify({'error': 'Book not found'}), 404
    cur.execute("SELECT COUNT(*) FROM user_favorites WHERE user_id=%s", (user_id,))
    if cur.fetchone()[0] >= 5:
        cur.close()
        return jsonify({'error': 'Favorites limit reached (max 5)'}), 400
    try:
        cur.execute("INSERT IGNORE INTO user_favorites (user_id, book_id) VALUES (%s,%s)", (user_id, book_id))
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'error': str(e)}), 500
    cur.close()
    return jsonify({'success': True}), 200


@user_bp.route('/api/user/favorites/<int:book_id>/delete', methods=['POST'])
def remove_favorite(book_id):
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    try:
        cur.execute("DELETE FROM user_favorites WHERE user_id=%s AND book_id=%s", (user_id, book_id))
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'error': str(e)}), 500
    cur.close()
    return jsonify({'success': True}), 200


# =====================================================================
# PROFILE / SETTINGS
# =====================================================================

@user_bp.route('/user/update_profile', methods=['POST'])
def update_user_profile():
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    user_id = session.get('user_id')
    field   = request.form.get('field', '').strip()
    value   = request.form.get('value', '').strip()
    if value in ('—', ''):
        value = None

    pii_fields = {
        'firstName':      'firstname',
        'lastName':       'lastname',
        'phone':          'phone_number',
        'city':           'city',
        'province':       'province',
        'age':            'age',
        'gender':         'gender',
        'school':         'school',
        'educationLevel': 'education_level',
        'occupation':     'occupation',
        'officePhone':    'office_phone',
    }
    bool_fields = {
        'isGovernment': 'is_government',
    }

    try:
        cur = mysql.connection.cursor()

        if field in pii_fields:
            db_col = pii_fields[field]
            encrypted_value = encrypt_pii(value) if value else None
            cur.execute(
                f"UPDATE users SET {db_col}=%s WHERE id=%s",
                (encrypted_value, user_id)
            )

        elif field in bool_fields:
            db_col = bool_fields[field]
            bool_val = 1 if value in ('1', 'true', 'True', 'yes') else 0
            cur.execute(
                f"UPDATE users SET {db_col}=%s WHERE id=%s",
                (bool_val, user_id)
            )

        else:
            cur.close()
            return jsonify({'success': False, 'message': 'Invalid field'}), 400

        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@user_bp.route('/user/change_password', methods=['POST'])
def user_change_password():
    if not is_logged_in() or require_role('user'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    user_id    = session['user_id']
    current_pw = request.form.get('current_password', '').strip()
    new_pw     = request.form.get('new_password',     '').strip()
    confirm_pw = request.form.get('confirm_password', '').strip()

    if not current_pw or not new_pw or not confirm_pw:
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400
    if new_pw != confirm_pw:
        return jsonify({'success': False, 'message': 'New passwords do not match.'}), 400
    if not re.match(
        r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_#^])[A-Za-z\d@$!%*?&_#^]{8,}$',
        new_pw,
    ):
        return jsonify({'success': False,
                        'message': 'Password must be 8+ chars with uppercase, lowercase, number, and special char.'}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT password FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({'success': False, 'message': 'User not found.'}), 404
        if not bcrypt.check_password_hash(row[0], current_pw):
            cur.close()
            return jsonify({'success': False, 'message': 'Current password is incorrect.'}), 400
        if bcrypt.check_password_hash(row[0], new_pw):
            cur.close()
            return jsonify({'success': False, 'message': 'New password cannot be the same as the current one.'}), 400

        hashed = bcrypt.generate_password_hash(new_pw).decode('utf-8')
        cur.execute("""
            UPDATE users SET password=%s, failed_attempts=0, is_locked=0, lock_until=NULL WHERE id=%s
        """, (hashed, user_id))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'message': 'Password updated successfully!'}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@user_bp.route('/user/scan_valid_id', methods=['POST'])
def scan_valid_id():
    if not is_logged_in() or require_role('user'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    file = request.files.get('valid_id')
    if not file or not file.filename:
        return jsonify({'success': False, 'message': 'No file provided.'}), 400

    allowed_types = {'image/png', 'image/jpeg', 'image/jpg', 'image/webp'}
    if file.content_type not in allowed_types:
        return jsonify({'success': False, 'message': 'Invalid file type. Use PNG, JPG, or WEBP.'}), 400

    try:
        file_bytes = file.read()
        file_size  = len(file_bytes)

        # 1. Check file size (max 5MB)
        if file_size > 5 * 1024 * 1024:
            return jsonify({'success': False, 'message': 'File too large. Max 5MB.'}), 400

        # 2. Open and inspect image
        img = Image.open(io.BytesIO(file_bytes))
        width, height = img.size
        mode = img.mode

        checks = {
            'photo_present':     True,
            'name_readable':     None,   # can't read without AI
            'id_number_visible': None,
            'official_markings': None,
            'validity_readable': None,
        }

        flags = []

        # 3. Check minimum resolution (ID should be readable)
        if width < 400 or height < 250:
            flags.append('Image resolution is too low — please use a clearer photo.')
            checks['photo_present'] = False

        # 4. Check aspect ratio (IDs are roughly card-shaped)
        ratio = width / height
        if ratio < 1.2 or ratio > 2.2:
            flags.append('Image proportions do not match a standard ID card shape.')

        # 5. Check it's a color image (not blank/grayscale scan)
        if mode not in ('RGB', 'RGBA'):
            flags.append('Image appears to be grayscale — please upload a color photo.')

        # 6. Check image is not too dark or blank
        import struct
        if mode in ('RGB', 'RGBA'):
            img_rgb    = img.convert('RGB')
            pixels     = list(img_rgb.getdata())
            sample     = pixels[::max(1, len(pixels)//500)]  # sample 500 pixels
            avg_bright = sum((r+g+b)/3 for r,g,b in sample) / len(sample)
            if avg_bright < 30:
                flags.append('Image appears too dark — please retake in better lighting.')
            elif avg_bright > 240:
                flags.append('Image appears overexposed or blank.')

        valid   = len(flags) == 0 and checks['photo_present']
        summary = 'Image passed basic validation. Please ensure it is a valid Philippine government or school ID.' if valid else 'Image did not pass validation.'

        result = {
            'id_category':             'unknown',
            'id_type':                 'Uploaded ID',
            'valid':                   valid,
            'detected_name':           None,
            'detected_number':         None,
            'detected_expiry_or_year': None,
            'detected_institution':    None,
            'checks':                  checks,
            'summary':                 summary,
            'flag':                    flags[0] if flags else None,
        }

        return jsonify({'success': True, 'result': result}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': 'Could not process image. Please try a different file.'}), 500
# =====================================================================
# SEARCH HISTORY
# =====================================================================

@user_bp.route('/api/user/search-history', methods=['GET'])
def api_get_search_history():
    if not is_logged_in() or require_role('user'):
        return jsonify({'success': False, 'history': []}), 401
    user_id = session['user_id']
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT DISTINCT query FROM user_search_history
            WHERE user_id=%s ORDER BY searched_at DESC LIMIT 20
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        seen    = set()
        history = []
        for (q,) in rows:
            if q.lower() not in seen:
                seen.add(q.lower())
                history.append(q)
        return jsonify({'success': True, 'history': history[:20]}), 200
    except Exception as e:
        return jsonify({'success': False, 'history': [], 'error': str(e)}), 500


@user_bp.route('/api/user/search-history', methods=['POST'])
def api_save_search_history():
    if not is_logged_in() or require_role('user'):
        return jsonify({'success': False}), 401
    data    = request.get_json(silent=True) or {}
    query   = (data.get('query') or '').strip()
    user_id = session['user_id']
    if not query:
        return jsonify({'success': False, 'message': 'Empty query'}), 400
    save_search_history(user_id, query)
    return jsonify({'success': True}), 200


@user_bp.route('/user/clear_search_history', methods=['POST'])
def user_clear_search_history():
    if not is_logged_in() or require_role('user'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    user_id = session['user_id']
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM user_search_history WHERE user_id=%s", (user_id,))
        mysql.connection.commit()
        deleted = cur.rowcount
        cur.close()
        return jsonify({'success': True, 'message': f'Cleared {deleted} search record(s).'}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@user_bp.route('/user/clear_favorites', methods=['POST'])
def user_clear_favorites():
    if not is_logged_in() or require_role('user'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    user_id = session['user_id']
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM user_favorites WHERE user_id=%s", (user_id,))
        mysql.connection.commit()
        deleted = cur.rowcount
        cur.close()
        return jsonify({'success': True, 'message': f'Cleared {deleted} favorite(s).'}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# =====================================================================
# APPEARANCE
# =====================================================================

@user_bp.route('/api/user/appearance', methods=['GET'])
def get_user_appearance():
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT theme, language FROM user_appearance WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        return jsonify({'theme': 'ocean', 'language': 'english'})
    return jsonify({'theme': row[0], 'language': row[1]})


@user_bp.route('/api/user/appearance', methods=['POST'])
def save_user_appearance():
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    data    = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    theme    = data.get('theme', 'ocean').lower()
    language = data.get('language', 'english').lower()
    if theme    not in ('ocean', 'midnight', 'forest', 'amber', 'cobalt', 'slate'): theme    = 'ocean'
    if language not in ('english', 'filipino', 'hiligaynon'):                        language = 'english'

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO user_appearance (user_id, theme, language)
            VALUES (%s,%s,%s)
            ON DUPLICATE KEY UPDATE theme=VALUES(theme), language=VALUES(language), updated_at=NOW()
        """, (user_id, theme, language))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'theme': theme, 'language': language}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# =====================================================================
# STORAGE
# =====================================================================

@user_bp.route('/api/user/storage', methods=['GET'])
def api_user_storage():
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    cur     = mysql.connection.cursor()
    stats   = calc_storage(user_id, cur)
    cur.close()
    return jsonify(stats), 200


@user_bp.route('/api/user/storage/check', methods=['GET'])
def api_user_storage_check():
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    cur     = mysql.connection.cursor()
    stats   = calc_storage(user_id, cur)
    cur.close()
    return jsonify({
        'is_full':      stats['is_full'],
        'is_warning':   stats['is_warning'],
        'used_percent': stats['used_percent'],
        'total_bytes':  stats['total_bytes'],
        'limit_bytes':  stats['limit_bytes'],
    }), 200


# =====================================================================
# ACCOUNT REQUESTS (danger zone)
# =====================================================================

@user_bp.route('/user/submit-account-request', methods=['POST'])
def user_submit_account_request():
    if not is_logged_in() or require_role('user'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    user_id  = session['user_id']
    action   = request.form.get('action',   '').strip()
    reason   = request.form.get('reason',   '').strip()
    password = request.form.get('password', '').strip()

    if action not in ('deactivate', 'delete'):
        return jsonify({'success': False, 'message': 'Invalid action.'}), 400
    if len(reason) < 20:
        return jsonify({'success': False, 'message': 'Reason must be at least 20 characters.'}), 400
    if not password:
        return jsonify({'success': False, 'message': 'Password is required.'}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT password, username FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        if not row or not bcrypt.check_password_hash(row[0], password):
            cur.close()
            return jsonify({'success': False, 'message': 'Incorrect password.'}), 400

        username = row[1]
        cur.execute("""
            SELECT id FROM account_requests WHERE user_id=%s AND status='pending'
        """, (user_id,))
        if cur.fetchone():
            cur.close()
            return jsonify({'success': False,
                            'message': 'You already have a pending request.'}), 409

        cur.execute("""
            INSERT INTO account_requests (user_id, username, request_type, reason)
            VALUES (%s,%s,%s,%s)
        """, (user_id, username, action, reason))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'message': 'Request submitted successfully.'}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@user_bp.route('/api/user/account-request/status', methods=['GET'])
def user_account_request_status():
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401
    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT request_type, created_at FROM account_requests
        WHERE user_id=%s AND status='pending' ORDER BY created_at DESC LIMIT 1
    """, (user_id,))
    row = cur.fetchone()
    cur.close()
    if row:
        return jsonify({'pending': True, 'request_type': row[0], 'submitted_at': fmt_dt(row[1])})
    return jsonify({'pending': False})


# =====================================================================
# BORROWED BOOKS & RETURNS
# =====================================================================

@user_bp.route('/api/user/borrowed-books')
def api_user_borrowed_books():
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, card_type_category, firstname, lastname, phone_number, address,
               date_issued, date_return,
               renewal1_checked, renewal1_date, renewal2_checked, renewal2_date,
               card_type, valid_until, photo_path, created_at
        FROM library_cards WHERE user_id=%s ORDER BY created_at DESC
    """, (user_id,))
    rows = cur.fetchall()

    if rows:
        card_ids = [r[0] for r in rows]
        fmt_in   = ','.join(['%s'] * len(card_ids))
        cur.execute(f"""
            SELECT card_id, book_id, book_title, book_author, book_isbn, quantity
            FROM library_card_books WHERE card_id IN ({fmt_in})
        """, card_ids)
        book_rows = cur.fetchall()
    else:
        book_rows = []
    cur.close()

    books_by_card = {}
    for br in book_rows:
        books_by_card.setdefault(br[0], []).append({
            'book_id': br[1], 'title': br[2], 'author': br[3],
            'isbn': br[4] or '', 'quantity': br[5] or 1,
        })

    cards = []
    for r in rows:
        photo_url = ('/' + r[14].replace('\\', '/')) if r[14] else ''
        cards.append({
            'id': r[0], 'type': r[1], 'firstname': r[2], 'lastname': r[3],
            'phone_number': r[4] or '', 'address': r[5] or '',
            'date_issued':      str(r[6])  if r[6]  else '',
            'date_return':      str(r[7])  if r[7]  else '',
            'renewal1_checked': bool(r[8]),
            'renewal1_date':    str(r[9])  if r[9]  else '',
            'renewal2_checked': bool(r[10]),
            'renewal2_date':    str(r[11]) if r[11] else '',
            'card_type': r[12] or '', 'valid_until': r[13] or '',
            'photo_url': photo_url, 'created_at': fmt_dt(r[15]),
            'returned': False,
            'books': books_by_card.get(r[0], []),
        })

    return jsonify({'cards': cards, 'total': len(cards)})


@user_bp.route('/api/user/return-history')
def api_user_return_history():
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT br.id, lc.id, lc.card_type_category, lc.firstname, lc.lastname,
                   lc.date_issued, br.return_date, u.firstname, u.lastname
            FROM book_returns br
            JOIN library_cards lc ON lc.id=br.card_id
            LEFT JOIN users u ON u.id=br.processed_by
            WHERE lc.user_id=%s ORDER BY br.created_at DESC
        """, (user_id,))
        rows = cur.fetchall()

        if rows:
            ret_ids = [r[0] for r in rows]
            fmt_in  = ','.join(['%s'] * len(ret_ids))
            cur.execute(f"""
                SELECT return_id, book_title, book_author, qty_returned
                FROM book_return_items WHERE return_id IN ({fmt_in})
            """, ret_ids)
            item_rows = cur.fetchall()
        else:
            item_rows = []
        cur.close()

        items_by_return = {}
        for ir in item_rows:
            items_by_return.setdefault(ir[0], []).append({
                'title': ir[1], 'author': ir[2], 'qty_returned': ir[3],
            })

        returns = [
            {
                'id': r[0], 'card_id': r[1], 'card_type': r[2],
                'firstname': r[3], 'lastname': r[4],
                'date_issued': str(r[5]) if r[5] else '',
                'return_date': str(r[6]) if r[6] else '',
                'processed_by': f"{r[7] or ''} {r[8] or ''}".strip() or '—',
                'books': items_by_return.get(r[0], []),
            }
            for r in rows
        ]
        return jsonify({'returns': returns}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@user_bp.route('/api/user/renew/<int:card_id>', methods=['POST'])
def api_user_renew_card(card_id):
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    data    = request.get_json(silent=True) or {}

    renewal1_checked = 1 if data.get('renewal1_checked') else 0
    renewal1_date    = data.get('renewal1_date', '').strip() or None
    renewal2_checked = 1 if data.get('renewal2_checked') else 0
    renewal2_date    = data.get('renewal2_date', '').strip() or None
    reason           = data.get('reason', '').strip() or None

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT lc.id, lc.renewal1_checked, lc.renewal2_checked
            FROM library_cards lc WHERE lc.id=%s AND lc.user_id=%s
        """, (card_id, user_id))
        card = cur.fetchone()

        if not card:
            cur.close()
            return jsonify({'error': 'Card not found or access denied.'}), 404
        if card[2]:
            cur.close()
            return jsonify({'error': 'Both renewal slots already used.'}), 400

        cur.execute("""
            SELECT id FROM account_requests
            WHERE user_id=%s AND card_id=%s AND request_type='renew' AND status='pending'
        """, (user_id, card_id))
        if cur.fetchone():
            cur.close()
            return jsonify({'error': 'You already have a pending renewal request for this card.'}), 409

        def parse_date(s):
            if not s:
                return None
            for fmt in ('%b %d, %Y', '%Y-%m-%d', '%m/%d/%Y'):
                try:
                    return datetime.strptime(s, fmt).date()
                except ValueError:
                    continue
            return None

        cur.execute("SELECT username FROM users WHERE id=%s", (user_id,))
        urow     = cur.fetchone()
        username = urow[0] if urow else ''

        cur.execute("""
            INSERT INTO account_requests
                (user_id, username, request_type, reason,
                 card_id, renewal1_checked, renewal1_date,
                 renewal2_checked, renewal2_date)
            VALUES (%s,%s,'renew',%s,%s,%s,%s,%s,%s)
        """, (
            user_id, username, reason or 'No reason provided',
            card_id,
            renewal1_checked, parse_date(renewal1_date),
            renewal2_checked, parse_date(renewal2_date),
        ))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'message': 'Renewal request submitted! Awaiting admin approval.'}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500


# =====================================================================
# RECENT ACTIVITY
# =====================================================================

@user_bp.route('/api/user/recent-activity', methods=['GET'])
def api_user_recent_activity():
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    events  = []

    try:
        cur = mysql.connection.cursor()

        cur.execute("SELECT last_seen FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        if row and row[0]:
            events.append({'type': 'login', 'text': 'Logged in from Iloilo City, PH',
                           'time_dt': row[0], 'color': 'accent'})

        cur.execute("SELECT created_at FROM users WHERE id=%s", (user_id,))
        account_created = cur.fetchone()[0]

        cur.execute("""
            SELECT query, searched_at FROM user_search_history
            WHERE user_id=%s ORDER BY searched_at DESC LIMIT 3
        """, (user_id,))
        for r in cur.fetchall():
            events.append({'type': 'search', 'text': f'Searched for <strong>{r[0]}</strong>',
                           'time_dt': r[1], 'color': 'accent'})

        cur.execute("""
            SELECT COUNT(*), MAX(f.created_at), b.title
            FROM user_favorites f JOIN books b ON b.id=f.book_id
            WHERE f.user_id=%s GROUP BY f.user_id
        """, (user_id,))
        fav_row = cur.fetchone()
        if fav_row and fav_row[0]:
            count = int(fav_row[0])
            title = safe_decrypt(fav_row[2]) if fav_row[2] else 'a book'
            events.append({
                'type':    'favorite',
                'text':    f'Added <strong>{title}</strong> to favorites'
                           + (f' (+{count - 1} more)' if count > 1 else ''),
                'time_dt': fav_row[1],
                'color':   'gold',
            })

        if account_created:
            events.append({'type': 'created', 'text': 'Account created',
                           'time_dt': account_created, 'color': 'accent'})
        cur.close()

        events.sort(key=lambda e: e['time_dt'], reverse=True)
        events = events[:6]

        now    = datetime.now()
        result = []
        for ev in events:
            diff = now - ev['time_dt']
            secs = diff.total_seconds()
            if secs < 60:           label = 'Just now'
            elif secs < 3600:       label = f'{int(secs//60)} min{"s" if secs//60>1 else ""} ago'
            elif secs < 86400:      label = f'{int(secs//3600)} hr{"s" if secs//3600>1 else ""} ago'
            elif diff.days == 1:    label = 'Yesterday'
            elif diff.days < 7:     label = f'{diff.days} days ago'
            elif diff.days < 30:    label = f'{diff.days//7} week{"s" if diff.days//7>1 else ""} ago'
            elif diff.days < 365:   label = f'{diff.days//30} month{"s" if diff.days//30>1 else ""} ago'
            else:                   label = ev['time_dt'].strftime('%b %d, %Y')
            result.append({'type': ev['type'], 'text': ev['text'], 'time': label, 'color': ev['color']})

        return jsonify({'success': True, 'activities': result}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'activities': []}), 500


# =====================================================================
# MFA — STATUS, TOGGLE, PIN SETUP
# =====================================================================

@user_bp.route('/api/user/mfa/status', methods=['GET'])
def get_mfa_status():
    if not is_logged_in() or require_role('user'):
        return jsonify({'error': 'Unauthorized'}), 401

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT otp_enabled, pin_enabled, pin_set_at FROM users WHERE id=%s",
        (session['user_id'],)
    )
    row = cur.fetchone()
    cur.close()

    pin_expired = False
    if row and row[2]:
        pin_expired = (datetime.now() - row[2]) > timedelta(weeks=1)

    return jsonify({
        'otp_enabled': bool(row[0]) if row else False,
        'pin_enabled': bool(row[1]) if row else False,
        'pin_expired': pin_expired,
    })


@user_bp.route('/user/mfa/toggle', methods=['POST'])
def toggle_mfa():
    if not is_logged_in() or require_role('user'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    mfa_type = request.form.get('type', '').strip()
    enabled  = request.form.get('enabled', '0') == '1'

    if mfa_type == 'otp':
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                "UPDATE users SET otp_enabled=%s WHERE id=%s",
                (1 if enabled else 0, session['user_id'])
            )
            mysql.connection.commit()
            cur.close()
            return jsonify({'success': True})
        except Exception as e:
            mysql.connection.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    elif mfa_type == 'pin':
        if not enabled:
            try:
                cur = mysql.connection.cursor()
                cur.execute(
                    "UPDATE users SET pin_enabled=0 WHERE id=%s",
                    (session['user_id'],)
                )
                mysql.connection.commit()
                cur.close()
                return jsonify({'success': True})
            except Exception as e:
                mysql.connection.rollback()
                return jsonify({'success': False, 'message': str(e)}), 500
        else:
            return jsonify({'success': True, 'needs_setup': True})

    return jsonify({'success': False, 'message': 'Invalid type'}), 400


@user_bp.route('/user/mfa/pin/verify-password', methods=['POST'])
def pin_verify_password():
    """Step 1 of PIN setup — verify account password before showing PIN form."""
    if not is_logged_in() or require_role('user'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    password = request.form.get('password', '').strip()
    if not password:
        return jsonify({'success': False, 'message': 'Password is required.'}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT password FROM users WHERE id=%s", (session['user_id'],))
    row = cur.fetchone()
    cur.close()

    if not row or not bcrypt.check_password_hash(row[0], password):
        return jsonify({'success': False, 'message': 'Incorrect password.'}), 400

    return jsonify({'success': True})


@user_bp.route('/user/mfa/set-pin', methods=['POST'])
def set_pin():
    """Step 2 of PIN setup — save the hashed PIN."""
    if not is_logged_in() or require_role('user'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    pin = request.form.get('pin', '').strip()
    if not pin.isdigit() or len(pin) != 6:
        return jsonify({'success': False, 'message': 'PIN must be exactly 6 digits.'}), 400

    hashed = bcrypt.generate_password_hash(pin).decode('utf-8')
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE users
            SET pin_code=%s, pin_enabled=1, pin_set_at=%s
            WHERE id=%s
        """, (hashed, datetime.now(), session['user_id']))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True})
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500