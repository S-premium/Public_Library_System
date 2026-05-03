"""
routes/admin_routes.py
-----------------------
Blueprint: admin_bp  (url_prefix not set — routes keep their original paths)
"""

import json
import os
import uuid
from datetime import datetime, date, timedelta

from flask import (
    Blueprint, abort, render_template, request, redirect, send_file,
    session, flash, jsonify, url_for,
)
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename

from conn import mysql, app
from helpers import (
    is_logged_in, require_role,
    encrypt_data, safe_decrypt, fmt_dt,
    encrypt_pii, safe_decrypt_pii,
    encrypt_email, safe_decrypt_email,
    store_email, decrypt_email,
    build_users_data,
    build_book_data, BOOK_INVENTORY_QUERY,
    save_card_photo, resolve_book_snapshots,
    insert_card_books, update_inventory_on_borrow,
    event_to_dict,
)
from email_config import send_registration_decision_email

bcrypt = Bcrypt(app)

admin_bp = Blueprint("admin_bp", __name__)

# ── Event upload config ───────────────────────────────────────────────
VALID_CATEGORIES = {'general', 'urgent', 'event', 'reminder', 'holiday', 'meeting'}
UPLOAD_FOLDER    = os.path.join('static', 'uploads', 'events')
ALLOWED_EXT      = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
MAX_IMAGE_BYTES  = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


# =====================================================================
# PAGES
# =====================================================================

@admin_bp.route('/admin/home')
def admin_home():
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("admins/admin_home.html")


@admin_bp.route('/dashboard')
def dashboard():
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("admins/dashboard.html")


@admin_bp.route('/admin/inventory')
def admin_inventory():
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("admins/inventory_status.html")


# =====================================================================
# DASHBOARD STATS
# =====================================================================

@admin_bp.route('/dashboard/stats')
def dashboard_stats():
    if not is_logged_in() or require_role('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    cur = mysql.connection.cursor()

    cur.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
    role_map = {'admin': 0, 'librarian': 0, 'user': 0}
    for row in cur.fetchall():
        if row[0] in role_map:
            role_map[row[0]] = row[1]

    cur.execute("""
        SELECT
            SUM(CASE WHEN last_seen >= NOW() - INTERVAL 5 MINUTE THEN 1 ELSE 0 END),
            SUM(CASE WHEN last_seen < NOW() - INTERVAL 5 MINUTE OR last_seen IS NULL THEN 1 ELSE 0 END)
        FROM users
    """)
    r             = cur.fetchone()
    active_count  = int(r[0]) if r[0] else 0
    offline_count = int(r[1]) if r[1] else 0

    cur.execute("""
        SELECT DATE(created_at) AS day, COUNT(*) AS total
        FROM books WHERE created_at >= CURDATE() - INTERVAL 6 DAY
        GROUP BY DATE(created_at) ORDER BY day ASC
    """)
    book_rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM books")
    total_books = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE is_locked = 1")
    total_locked = cur.fetchone()[0]
    cur.close()

    from datetime import timedelta
    today    = date.today()
    days_map = {today - timedelta(days=i): 0 for i in range(6, -1, -1)}
    for row in book_rows:
        d = row[0] if isinstance(row[0], date) else row[0].date()
        if d in days_map:
            days_map[d] = int(row[1])

    return jsonify({
        'roles':        {'labels': ['Admins', 'Librarians', 'Users'],
                         'data':   [role_map['admin'], role_map['librarian'], role_map['user']]},
        'status':       {'active': active_count, 'offline': offline_count},
        'books_per_day':{'labels': [d.strftime('%a %d') for d in sorted(days_map)],
                         'data':   [days_map[d] for d in sorted(days_map)]},
        'totals':       {'books': total_books, 'users': total_users, 'locked': total_locked},
    })


# =====================================================================
# BOOK MANAGEMENT
# =====================================================================

@admin_bp.route('/book_management')
def book_management():
    if not is_logged_in() or require_role('admin', 'librarian'):
        flash("Unauthorized access", "danger")
        return redirect('/')

    cursor = mysql.connection.cursor()
    cursor.execute(BOOK_INVENTORY_QUERY)
    books = cursor.fetchall()
    cursor.close()

    return render_template('admins/book_management.html', books=build_book_data(books) or [])


# =====================================================================
# ADD BOOK  —  POST /add_book
# =====================================================================

@admin_bp.route('/add_book', methods=['POST'])
def add_book():
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    title  = request.form.get('title',  '').strip()
    author = request.form.get('author', '').strip()
    isbn   = request.form.get('isbn',   '').strip()

    if not (title and author and isbn):
        return jsonify({'success': False, 'message': 'Title, Author, and ISBN are required.'}), 400

    subtitle       = request.form.get('subtitle',       '').strip() or None
    publisher      = request.form.get('publisher',      '').strip() or None
    category       = request.form.get('category',       '').strip() or None
    genre_or_class = request.form.get('class', '').strip() or None
    edition        = request.form.get('edition',        '').strip() or None
    published_date = request.form.get('published_date', '').strip() or None
    language       = request.form.get('language',       '').strip() or None
    description    = request.form.get('description',    '').strip() or None
    thumbnail_url  = (
        request.form.get('thumbnail_url')
        or request.form.get('thumbnail_url_display')
        or ''
    ).strip() or None
    _pc            = request.form.get('page_count', '') or None
    try:
        page_count = int(float(_pc)) if _pc else None
    except (ValueError, TypeError):
        page_count = None

    api_source     = request.form.get('api_source',  '') or None
    call_number    = request.form.get('call_number',    '').strip() or None
    date_received  = request.form.get('date_received',  '').strip() or None
    copy_right     = request.form.get('copy_right',     '').strip() or None
    source_of_fund = request.form.get('source_of_fund', '').strip() or None
    cost_price     = request.form.get('cost_price',     '') or None

    total_copies   = max(0, int(request.form.get('total_copies',   1) or 1))
    damaged_copies = max(0, int(request.form.get('damaged_copies', 0) or 0))
    lost_copies    = max(0, int(request.form.get('lost_copies',    0) or 0))
    available_copies = max(0, total_copies - damaged_copies - lost_copies)
    shelf_location = request.form.get('shelf_location', '').strip() or None
    status         = request.form.get('status', 'Available').strip()
    is_borrowable  = 1 if request.form.get('is_borrowable') in ('1', 'on', 'true') else 0

    try:
        cursor   = mysql.connection.cursor()
        enc_isbn = encrypt_data(isbn)

        cursor.execute("SELECT id FROM books WHERE isbn = %s", (enc_isbn,))
        if cursor.fetchone():
            cursor.close()
            return jsonify({'success': False, 'message': 'A book with this ISBN already exists.'}), 409

        cursor.execute("""
            INSERT INTO books (
                title, author, isbn,
                subtitle, publisher, category, `class`,
                edition, published_date, language, description, thumbnail_url,
                page_count, api_source,
                call_number, date_received,
                copy_right, source_of_fund, cost_price,
                is_borrowable, created_at
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, NOW()
            )
        """, (
            encrypt_data(title),
            encrypt_data(author),
            enc_isbn,
            subtitle,
            encrypt_data(publisher) if publisher else None,
            encrypt_data(category)  if category  else None,
            encrypt_data(genre_or_class) if genre_or_class else None,
            edition,
            published_date,
            language,
            description,
            thumbnail_url,
            page_count,
            api_source,
            call_number,
            date_received or None,
            copy_right,
            source_of_fund,
            float(cost_price) if cost_price else None,
            is_borrowable,
        ))
        mysql.connection.commit()
        new_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO book_inventory
                (book_id, volumes, available_copies, damaged_copies, lost_copies,
                 status, shelf_location)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (new_id, total_copies, available_copies, damaged_copies,
              lost_copies, status, shelf_location))
        mysql.connection.commit()
        cursor.close()

        return jsonify({'success': True, 'book_id': new_id}), 201

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# =====================================================================
# UPDATE BOOK  —  POST /update_book
# =====================================================================

@admin_bp.route('/update_book', methods=['POST'])
def update_book():
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    book_id = request.form.get('book_id', '').strip()
    if not book_id:
        return jsonify({'success': False, 'message': 'Missing book_id.'}), 400

    title  = request.form.get('title',  '').strip()
    author = request.form.get('author', '').strip()
    isbn   = request.form.get('isbn',   '').strip()

    if not (title and author and isbn):
        return jsonify({'success': False, 'message': 'Title, Author, and ISBN are required.'}), 400

    subtitle       = request.form.get('subtitle',       '').strip() or None
    publisher      = request.form.get('publisher',      '').strip() or None
    category       = request.form.get('category',       '').strip() or None
    genre_or_class = request.form.get('class', '').strip() or None
    edition        = request.form.get('edition',        '').strip() or None
    published_date = request.form.get('published_date', '').strip() or None
    language       = request.form.get('language',       '').strip() or None
    description    = request.form.get('description',    '').strip() or None
    thumbnail_url  = request.form.get('thumbnail_url',  '').strip() or None

    _pc            = request.form.get('page_count', '') or None
    try:
        page_count = int(float(_pc)) if _pc else None
    except (ValueError, TypeError):
        page_count = None

    call_number    = request.form.get('call_number',    '').strip() or None
    date_received  = request.form.get('date_received',  '').strip() or None
    copy_right     = request.form.get('copy_right',     '').strip() or None
    source_of_fund = request.form.get('source_of_fund', '').strip() or None
    cost_price     = request.form.get('cost_price',     '') or None
    is_borrowable  = 1 if request.form.get('is_borrowable') in ('1', 'on', 'true') else 0

    total_copies   = max(0, int(request.form.get('total_copies',   0) or 0))
    damaged_copies = max(0, int(request.form.get('damaged_copies', 0) or 0))
    lost_copies    = max(0, int(request.form.get('lost_copies',    0) or 0))
    available_copies = max(0, total_copies - damaged_copies - lost_copies)
    status         = request.form.get('status', 'Available').strip()
    shelf_location = request.form.get('shelf_location', '').strip() or None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("SELECT id FROM books WHERE id = %s", (book_id,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({'success': False, 'message': 'Book not found.'}), 404

        enc_isbn = encrypt_data(isbn)
        cursor.execute(
            "SELECT id FROM books WHERE isbn = %s AND id != %s",
            (enc_isbn, book_id)
        )
        if cursor.fetchone():
            cursor.close()
            return jsonify({'success': False, 'message': 'Another book with this ISBN already exists.'}), 409

        cursor.execute("""
            UPDATE books SET
                title          = %s,
                author         = %s,
                isbn           = %s,
                subtitle       = %s,
                publisher      = %s,
                category       = %s,
                `class`        = %s,
                edition        = %s,
                published_date = %s,
                language       = %s,
                description    = %s,
                thumbnail_url  = %s,
                page_count     = %s,
                call_number    = %s,
                date_received  = %s,
                copy_right     = %s,
                source_of_fund = %s,
                cost_price     = %s,
                is_borrowable  = %s,
                updated_at     = NOW()
            WHERE id = %s
        """, (
            encrypt_data(title),
            encrypt_data(author),
            enc_isbn,
            subtitle,
            encrypt_data(publisher) if publisher else None,
            encrypt_data(category)  if category  else None,
            encrypt_data(genre_or_class) if genre_or_class else None,
            edition,
            published_date,
            language,
            description,
            thumbnail_url,
            page_count,
            call_number,
            date_received or None,
            copy_right,
            source_of_fund,
            float(cost_price) if cost_price else None,
            is_borrowable,
            book_id,
        ))

        cursor.execute("SELECT id FROM book_inventory WHERE book_id = %s", (book_id,))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE book_inventory SET
                    volumes          = %s,
                    available_copies = %s,
                    damaged_copies   = %s,
                    lost_copies      = %s,
                    status           = %s,
                    shelf_location   = %s
                WHERE book_id = %s
            """, (total_copies, available_copies, damaged_copies,
                  lost_copies, status, shelf_location, book_id))
        else:
            cursor.execute("""
                INSERT INTO book_inventory
                    (book_id, volumes, available_copies, damaged_copies,
                     lost_copies, status, shelf_location)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (book_id, total_copies, available_copies, damaged_copies,
                  lost_copies, status, shelf_location))

        mysql.connection.commit()
        cursor.close()
        return jsonify({'success': True}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# =====================================================================
# DELETE BOOK  —  POST /delete_book/<book_id>
# =====================================================================

@admin_bp.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT id FROM books WHERE id = %s", (book_id,))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({'success': False, 'message': 'Book not found.'}), 404

        cursor.execute("DELETE FROM book_inventory WHERE book_id = %s", (book_id,))
        cursor.execute("DELETE FROM books WHERE id = %s", (book_id,))
        mysql.connection.commit()
        cursor.close()
        return jsonify({'success': True}), 200

    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# =====================================================================
# UPDATE INVENTORY  —  POST /update_inventory
# =====================================================================

@admin_bp.route('/update_inventory', methods=['POST'])
def update_inventory():
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        book_id          = request.form.get('book_id', '').strip()
        total_copies     = max(0, int(request.form.get('total_copies',     0) or 0))
        available_copies = max(0, int(request.form.get('available_copies', 0) or 0))
        damaged_copies   = max(0, int(request.form.get('damaged_copies',   0) or 0))
        lost_copies      = max(0, int(request.form.get('lost_copies',      0) or 0))
        status           = request.form.get('status', 'Available').strip()
        shelf_location   = request.form.get('shelf_location', '').strip() or None
        is_borrowable    = 1 if request.form.get('is_borrowable') in ('1', 'on', 'true') else 0

        cursor = mysql.connection.cursor()

        cursor.execute(
            "UPDATE books SET is_borrowable = %s, updated_at = NOW() WHERE id = %s",
            (is_borrowable, book_id)
        )

        cursor.execute("SELECT id FROM book_inventory WHERE book_id = %s", (book_id,))
        if cursor.fetchone():
            cursor.execute("""
                UPDATE book_inventory SET
                    volumes          = %s,
                    available_copies = %s,
                    damaged_copies   = %s,
                    lost_copies      = %s,
                    status           = %s,
                    shelf_location   = %s
                WHERE book_id = %s
            """, (total_copies, available_copies, damaged_copies,
                  lost_copies, status, shelf_location, book_id))
        else:
            cursor.execute("""
                INSERT INTO book_inventory
                    (book_id, volumes, available_copies, damaged_copies,
                     lost_copies, status, shelf_location)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (book_id, total_copies, available_copies, damaged_copies,
                  lost_copies, status, shelf_location))

        mysql.connection.commit()
        cursor.close()
        return jsonify({'success': True}), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# =====================================================================
# USER / ADMIN / LIBRARIAN MANAGEMENT
# =====================================================================

@admin_bp.route('/admin_management')
def admin_management():
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, username, firstname, lastname, password, failed_attempts, is_locked,
               lock_until, created_at, status, last_seen, role
        FROM users WHERE role = 'admin' ORDER BY created_at DESC
    """)
    users = cur.fetchall()
    cur.close()
    return render_template('admins/admin_management.html', users=build_users_data(users))


@admin_bp.route('/librarian_management')
def librarian_management():
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, username, firstname, lastname, password, failed_attempts, is_locked,
               lock_until, created_at, status, last_seen, role
        FROM users WHERE role = 'librarian' ORDER BY created_at DESC
    """)
    users = cur.fetchall()
    cur.close()
    return render_template('admins/librarian_management.html', users=build_users_data(users))


@admin_bp.route('/user_management')
def user_management():
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, username, firstname, lastname, password, failed_attempts, is_locked,
               lock_until, created_at, status, last_seen, role, is_active
        FROM users WHERE role = 'user' ORDER BY created_at DESC
    """)
    users = cur.fetchall()
    cur.close()
    return render_template('admins/user_management.html', users=build_users_data(users))


@admin_bp.route('/unlock_user/<int:user_id>', methods=['POST'])
def unlock_user(user_id):
    if not is_logged_in() or require_role('admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE users SET is_locked=0, failed_attempts=0, lock_until=NULL WHERE id=%s
        """, (user_id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
 

import os as _os

@admin_bp.route('/admin/valid-id/<int:user_id>')
def serve_valid_id(user_id):
    """
    Securely serve a user's valid ID file.
    - Decrypts the stored path with decrypt_pii()
    - Only admins can access this endpoint
    - Blocks path traversal by verifying the file lives inside valid_id_vault/
    """
    if not is_logged_in() or require_role('admin'):
        abort(403)
 
    cur = mysql.connection.cursor()
    cur.execute("SELECT valid_id_path FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
 
    if not row or not row[0]:
        abort(404)
 
    # Decrypt the stored value — it was saved as encrypt_pii(full_os_path)
    try:
        from helpers import decrypt_pii
        real_path = decrypt_pii(row[0])
    except Exception:
        abort(404)
 
    if not real_path:
        abort(404)
 
    # Normalise separators (Windows paths may use backslashes)
    real_path = real_path.replace('\\', _os.sep).replace('/', _os.sep)
 
    # Security: make sure the file actually exists and is a regular file
    if not _os.path.isfile(real_path):
        app.logger.warning('[serve_valid_id] File not found on disk: %s', real_path)
        abort(404)
 
    # Security: confirm the file lives inside valid_id_vault/ to block
    # any future path-traversal if decryption were ever compromised
    vault_dir  = _os.path.realpath(_os.path.join(app.root_path, 'valid_id_vault'))
    resolved   = _os.path.realpath(real_path)
    if not resolved.startswith(vault_dir + _os.sep) and resolved != vault_dir:
        app.logger.warning('[serve_valid_id] Path outside vault! %s', resolved)
        abort(403)
 
    app.logger.info('[serve_valid_id] Serving user %s → %s', user_id, resolved)
    return send_file(resolved)
 
 
@admin_bp.route('/api/admin/user/<int:user_id>', methods=['GET'])
def api_get_user_detail(user_id):
    """Return full decrypted profile for one user (admin only)."""
    if not is_logged_in() or require_role('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
 
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT
            id,
            username,
            email_display,
            firstname,
            lastname,
            failed_attempts,
            is_locked,
            lock_until,
            created_at,
            status,
            last_seen,
            role,
            is_active,
            is_approved,
            otp_enabled,
            pin_enabled,
            age,
            gender,
            phone_number,
            school,
            city,
            province,
            education_level,
            occupation,
            is_government,
            office_phone,
            valid_id_path
        FROM users
        WHERE id = %s
    """, (user_id,))
    r = cur.fetchone()
    cur.close()
 
    if not r:
        return jsonify({'error': 'User not found'}), 404
 
    # Resolve live online status (5-minute window)
    status    = r[9]
    last_seen = r[10]
    if last_seen and isinstance(last_seen, datetime):
        if datetime.now() - last_seen > timedelta(minutes=5):
            status = 'offline'
 
    # Build the valid-ID URL — we route through /admin/valid-id/<user_id>
    # which decrypts the path server-side and serves the file.
    # This way the encrypted blob never touches the browser at all.
    valid_id_url = f'/admin/valid-id/{user_id}' if r[26] else ''
 
    # email_display (r[2]) = Fernet-encrypted readable email
    # username      (r[1]) = HMAC digest — not human-readable
    email = safe_decrypt_email(r[2]) if r[2] else safe_decrypt_email(r[1])
 
    return jsonify({
        'id':              r[0],
        'username':        email,
        'firstname':       safe_decrypt_pii(r[3])  or '',
        'lastname':        safe_decrypt_pii(r[4])  or '',
        'failed_attempts': int(r[5]) if r[5] else 0,
        'is_locked':       bool(r[6]),
        'lock_until':      r[7].strftime('%Y-%m-%d %H:%M') if r[7] else '',
        'created_at':      r[8].strftime('%Y-%m-%d %I:%M %p') if r[8] else '',
        'status':          status,
        'last_seen':       last_seen.strftime('%Y-%m-%d %I:%M %p') if last_seen else '',
        'role':            r[11],
        'is_active':       bool(r[12]) if r[12] is not None else True,
        'is_approved':     bool(r[13]) if r[13] is not None else False,
        'otp_enabled':     bool(r[14]) if r[14] is not None else False,
        'pin_enabled':     bool(r[15]) if r[15] is not None else False,
        'age':             safe_decrypt_pii(r[16]) if r[16] else '',
        'gender':          safe_decrypt_pii(r[17]) if r[17] else '',
        'phone_number':    safe_decrypt_pii(r[18]) if r[18] else '',
        'school':          safe_decrypt_pii(r[19]) if r[19] else '',
        'city':            safe_decrypt_pii(r[20]) if r[20] else '',
        'province':        safe_decrypt_pii(r[21]) if r[21] else '',
        'education_level': safe_decrypt_pii(r[22]) if r[22] else '',
        'occupation':      safe_decrypt_pii(r[23]) if r[23] else '',
        'is_government':   bool(r[24]) if r[24] is not None else False,
        'office_phone':    safe_decrypt_pii(r[25]) if r[25] else '',
        'valid_id_url':    valid_id_url,
    }), 200

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        mysql.connection.commit()
        cur.close()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect('/admin_management')


@admin_bp.route('/reset_user_password', methods=['POST'])
def reset_user_password():
    if not is_logged_in() or require_role('admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        user_id      = request.form.get('user_id')
        new_password = request.form.get('new_password')
        if not user_id or not new_password:
            return jsonify({'success': False, 'message': 'Missing fields'}), 400

        from flask_bcrypt import Bcrypt
        _bcrypt = Bcrypt(app)
        hashed  = _bcrypt.generate_password_hash(new_password).decode('utf-8')
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE users SET password=%s, failed_attempts=0, is_locked=0, lock_until=NULL WHERE id=%s
        """, (hashed, user_id))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/admin/deactivate_user', methods=['POST'])
def admin_deactivate_user():
    if not is_logged_in() or require_role('admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    user_id = request.form.get('user_id', '').strip()
    if not user_id:
        return jsonify({'success': False, 'message': 'Missing user_id'}), 400
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE users SET is_active=0, status='offline', last_seen=%s
            WHERE id=%s AND role='user'
        """, (datetime.now(), user_id))
        if cur.rowcount == 0:
            cur.close()
            return jsonify({'success': False, 'message': 'User not found'}), 404
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/admin/reactivate_user', methods=['POST'])
def admin_reactivate_user():
    if not is_logged_in() or require_role('admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    user_id = request.form.get('user_id', '').strip()
    if not user_id:
        return jsonify({'success': False, 'message': 'Missing user_id'}), 400
    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE users SET is_active=1 WHERE id=%s AND role='user'", (user_id,))
        if cur.rowcount == 0:
            cur.close()
            return jsonify({'success': False, 'message': 'User not found'}), 404
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# =====================================================================
# ANNOUNCEMENTS
# =====================================================================

@admin_bp.route('/admin/announcements')
def admin_announcements():
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("admins/announcement.html")


# =====================================================================
# ACCOUNT REQUESTS
# =====================================================================

@admin_bp.route('/admin/account-requests')
def admin_account_requests():
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("admins/admin_account_requests.html")


@admin_bp.route('/api/admin/account-requests', methods=['GET'])
def admin_get_account_requests():
    if not is_logged_in() or require_role('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT ar.id, ar.user_id, ar.username, ar.request_type,
            ar.reason, ar.status, ar.created_at, ar.reviewed_at, ar.admin_note,
            u.firstname, u.lastname, ar.card_id,
            ar.renewal1_checked, ar.renewal1_date,
            ar.renewal2_checked, ar.renewal2_date,
            u.gender, u.phone_number, u.school,
            u.city, u.province, u.education_level,
            u.occupation, u.is_government, u.office_phone,
            u.valid_id_path, u.created_at AS user_created_at,
            u.username AS user_username,
            u.email_display
        FROM account_requests ar
        LEFT JOIN users u ON u.id = ar.user_id
        ORDER BY ar.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()

    def _resolve_email(ar_raw, user_raw):
        """Try every decryption strategy to get a readable email."""
        from cryptography.fernet import InvalidToken
        for raw in (user_raw, ar_raw):
            if not raw:
                continue
            # Strategy 1: direct Fernet via email_cipher (store_email path)
            try:
                dec = decrypt_email(raw)
                if dec and '@' in dec:
                    return dec
            except Exception:
                pass
            # Strategy 2: safe_decrypt_email fallback
            try:
                dec = safe_decrypt_email(raw)
                if dec and '@' in dec:
                    return dec
            except Exception:
                pass
        # Last resort: return ar_raw as-is
        return ar_raw or ''

    # r[26] = user_created_at, r[27] = user_username
    return jsonify({'requests': [
        {
            'id': r[0], 'user_id': r[1],
            'username': _resolve_email(r[2], r[28]),
            'request_type': r[3], 'reason': r[4], 'status': r[5],
            'created_at': fmt_dt(r[6]), 'reviewed_at': fmt_dt(r[7]) if r[7] else None,
            'admin_note': r[8] or '',
            'fullname': f"{safe_decrypt_pii(r[9]) or ''} {safe_decrypt_pii(r[10]) or ''}".strip(),
            'firstname': safe_decrypt_pii(r[9]) or '',
            'lastname':  safe_decrypt_pii(r[10]) or '',
            'card_id': r[11],
            'renewal1_checked': bool(r[12]) if r[12] is not None else False,
            'renewal1_date':    str(r[13]) if r[13] else '',
            'renewal2_checked': bool(r[14]) if r[14] is not None else False,
            'renewal2_date':    str(r[15]) if r[15] else '',
            'gender':          safe_decrypt_pii(r[16]) if r[16] else '',
            'phone_number':    safe_decrypt_pii(r[17]) if r[17] else '',
            'school':          safe_decrypt_pii(r[18]) if r[18] else '',
            'city':            safe_decrypt_pii(r[19]) if r[19] else '',
            'province':        safe_decrypt_pii(r[20]) if r[20] else '',
            'education_level': safe_decrypt_pii(r[21]) if r[21] else '',
            'occupation':      safe_decrypt_pii(r[22]) if r[22] else '',
            'is_government':   bool(r[23]) if r[23] is not None else False,
            'office_phone':    safe_decrypt_pii(r[24]) if r[24] else '',
            'valid_id_path':   bool(r[25]),
            'user_created_at': fmt_dt(r[26]) if r[26] else '',
        }
        for r in rows
    ]})


@admin_bp.route('/api/admin/account-requests/<int:req_id>/approve', methods=['POST'])
def admin_approve_account_request(req_id):
    if not is_logged_in() or require_role('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    admin_id   = session['user_id']
    admin_note = (request.get_json() or {}).get('note', '').strip()

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT user_id, request_type, card_id,
               renewal1_checked, renewal1_date, renewal2_checked, renewal2_date
        FROM account_requests WHERE id=%s AND status='pending'
    """, (req_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        return jsonify({'error': 'Request not found or already processed.'}), 404

    target_user_id, req_type, card_id = row[0], row[1], row[2]
    ren1_chk, ren1_date, ren2_chk, ren2_date = row[3], row[4], row[5], row[6]

    try:
        if req_type == 'deactivate':
            cur.execute("""
                UPDATE users SET is_active=0, status='offline', last_seen=%s WHERE id=%s
            """, (datetime.now(), target_user_id))
        elif req_type == 'register':
            cur.execute("UPDATE users SET is_active=1, is_approved=1 WHERE id=%s", (target_user_id,))
        elif req_type == 'delete':
            for tbl in ('user_favorites', 'user_search_history', 'user_appearance', 'notification_reads'):
                cur.execute(f"DELETE FROM {tbl} WHERE user_id=%s", (target_user_id,))
            cur.execute("DELETE FROM users WHERE id=%s", (target_user_id,))
        elif req_type == 'renew':
            cur.execute("""
                UPDATE library_cards
                SET renewal1_checked=%s, renewal1_date=%s,
                    renewal2_checked=%s, renewal2_date=%s
                WHERE id=%s
            """, (ren1_chk, ren1_date, ren2_chk, ren2_date, card_id))

        cur.execute("""
            UPDATE account_requests SET status='approved', reviewed_by=%s,
                   reviewed_at=%s, admin_note=%s WHERE id=%s
        """, (admin_id, datetime.now(), admin_note, req_id))

        if req_type != 'delete':
            if req_type == 'register':
                notif_title = 'Registration Approved — Welcome! 🎉'
                notif_body  = (
                    "Your registration has been approved by the Admin. "
                    "You can now log in." + (f' Note: "{admin_note}"' if admin_note else "")
                )
                send_registration_decision_email(target_user_id, approved=True, note=admin_note)
            elif req_type == 'renew':
                notif_title = 'Library Card Renewal — Approved ✓'
                notif_body  = "Your library card renewal has been approved." + (f' Note: "{admin_note}"' if admin_note else "")
            else:
                notif_title = 'Account Deactivation Request — Approved'
                notif_body  = "Your deactivation request has been approved." + (f' Note: "{admin_note}"' if admin_note else "")

            cur.execute("SELECT firstname, lastname FROM users WHERE id=%s", (admin_id,))
            ar = cur.fetchone()
            author = f"{safe_decrypt_pii(ar[0])} {safe_decrypt_pii(ar[1])} (Admin)"[:100] if ar else "Library Administration"

            cur.execute("""
                INSERT INTO announcements (title, body, category, pinned, author)
                VALUES (%s,%s,'general',0,%s)
            """, (notif_title, notif_body, author))
            new_ann_id = cur.lastrowid

            cur.execute("SELECT id FROM users WHERE id != %s", (target_user_id,))
            other_users = cur.fetchall()
            if other_users:
                cur.executemany("""
                    INSERT IGNORE INTO notification_reads (user_id, announcement_id, dismissed)
                    VALUES (%s, %s, 1)
                """, [(u[0], new_ann_id) for u in other_users])

            cur.execute("""
                DELETE FROM notification_reads WHERE user_id=%s AND announcement_id=%s
            """, (target_user_id, new_ann_id))

        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True}), 200

    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/admin/account-requests/<int:req_id>/reject', methods=['POST'])
def admin_reject_account_request(req_id):
    if not is_logged_in() or require_role('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    admin_id   = session['user_id']
    admin_note = (request.get_json() or {}).get('note', '').strip()

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT user_id, request_type FROM account_requests WHERE id=%s AND status='pending'
    """, (req_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return jsonify({'error': 'Request not found or already processed.'}), 404

    target_user_id, req_type = row[0], row[1]

    try:
        cur.execute("""
            UPDATE account_requests SET status='rejected', reviewed_by=%s,
                   reviewed_at=%s, admin_note=%s WHERE id=%s
        """, (admin_id, datetime.now(), admin_note, req_id))

        if req_type == 'register':
            send_registration_decision_email(target_user_id, approved=False, note=admin_note)

        action_label = 'Renewal' if req_type == 'renew' else req_type.capitalize()
        notif_title  = f'Account {action_label} Request — Not Approved'
        notif_body   = (
            f"Your {req_type} request was not approved. "
            + (f'Reason: "{admin_note}"' if admin_note else "Contact the library for more info.")
        )

        cur.execute("SELECT firstname, lastname FROM users WHERE id=%s", (admin_id,))
        ar     = cur.fetchone()
        author = f"{safe_decrypt_pii(ar[0])} {safe_decrypt_pii(ar[1])} (Admin)"[:100] if ar else "Library Administration"

        cur.execute("""
            INSERT INTO announcements (title, body, category, pinned, author)
            VALUES (%s,%s,'urgent',0,%s)
        """, (notif_title, notif_body, author))
        new_ann_id = cur.lastrowid

        cur.execute("SELECT id FROM users WHERE id != %s", (target_user_id,))
        other_users = cur.fetchall()
        if other_users:
            cur.executemany("""
                INSERT IGNORE INTO notification_reads (user_id, announcement_id, dismissed)
                VALUES (%s, %s, 1)
            """, [(u[0], new_ann_id) for u in other_users])

        cur.execute("""
            DELETE FROM notification_reads WHERE user_id=%s AND announcement_id=%s
        """, (target_user_id, new_ann_id))

        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True}), 200

    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/admin/account-requests/<int:req_id>/delete', methods=['POST'])
def admin_delete_account_request(req_id):
    if not is_logged_in() or require_role('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "DELETE FROM account_requests WHERE id=%s AND status != 'pending'",
            (req_id,),
        )
        if cur.rowcount == 0:
            cur.close()
            return jsonify({'error': 'Not found or still pending.'}), 404
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500


# =====================================================================
# EVENT CALENDAR
# =====================================================================

@admin_bp.route('/admin/event')
def admin_event():
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("admins/calendar_event.html")


@admin_bp.route('/api/events', methods=['GET'])
def api_get_events():
    if not is_logged_in():
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, title, description, event_date,
                   start_time, end_time, location, image, created_at, category
            FROM events ORDER BY event_date ASC, start_time ASC
        """)
        rows = cursor.fetchall()
        cursor.close()
        return jsonify([event_to_dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/events', methods=['POST'])
def api_create_event():
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'error': 'Unauthorized'}), 401

    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    event_date  = request.form.get('event_date', '').strip()
    start_time  = request.form.get('start_time') or None
    end_time    = request.form.get('end_time')   or None
    location    = request.form.get('location', '').strip() or None
    category    = request.form.get('category', 'general').strip().lower()

    if category not in VALID_CATEGORIES:
        category = 'general'
    if not title or not event_date:
        return jsonify({'error': 'Title and event date are required.'}), 400

    image_path = None
    file       = request.files.get('image')
    if file and file.filename:
        if not _allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type.'}), 400
        file.seek(0, os.SEEK_END)
        if file.tell() > MAX_IMAGE_BYTES:
            return jsonify({'error': 'Image must be under 5 MB.'}), 400
        file.seek(0)
        ext        = secure_filename(file.filename).rsplit('.', 1)[1].lower()
        image_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.{ext}").replace('\\', '/')
        file.save(image_path)

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO events
                (title, description, event_date, start_time, end_time, location, image, category)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (title, description or None, event_date, start_time, end_time, location, image_path, category))
        mysql.connection.commit()
        new_id = cursor.lastrowid
        cursor.execute("""
            SELECT id, title, description, event_date,
                   start_time, end_time, location, image, created_at, category
            FROM events WHERE id=%s
        """, (new_id,))
        row = cursor.fetchone()
        cursor.close()
        return jsonify(event_to_dict(row)), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/events/<int:event_id>/update', methods=['POST'])
def api_update_event(event_id):
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'error': 'Unauthorized'}), 401

    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    event_date  = request.form.get('event_date', '').strip()
    start_time  = request.form.get('start_time') or None
    end_time    = request.form.get('end_time')   or None
    location    = request.form.get('location', '').strip() or None
    category    = request.form.get('category', 'general').strip().lower()

    if category not in VALID_CATEGORIES:
        category = 'general'
    if not title or not event_date:
        return jsonify({'error': 'Title and event date are required.'}), 400

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT image FROM events WHERE id=%s", (event_id,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            return jsonify({'error': 'Event not found'}), 404

        new_image_path = row[0]
        file           = request.files.get('image')
        if file and file.filename:
            if not _allowed_file(file.filename):
                cursor.close()
                return jsonify({'error': 'Invalid file type.'}), 400
            file.seek(0, os.SEEK_END)
            if file.tell() > MAX_IMAGE_BYTES:
                cursor.close()
                return jsonify({'error': 'Image must be under 5 MB.'}), 400
            file.seek(0)
            ext            = secure_filename(file.filename).rsplit('.', 1)[1].lower()
            new_image_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}.{ext}").replace('\\', '/')
            file.save(new_image_path)
            if row[0] and os.path.exists(row[0]):
                try:
                    os.remove(row[0])
                except OSError:
                    pass

        cursor.execute("""
            UPDATE events SET title=%s, description=%s, event_date=%s,
                   start_time=%s, end_time=%s, location=%s, image=%s, category=%s
            WHERE id=%s
        """, (title, description or None, event_date,
              start_time, end_time, location, new_image_path, category, event_id))
        mysql.connection.commit()

        cursor.execute("""
            SELECT id, title, description, event_date,
                   start_time, end_time, location, image, created_at, category
            FROM events WHERE id=%s
        """, (event_id,))
        updated = cursor.fetchone()
        cursor.close()
        return jsonify(event_to_dict(updated)), 200

    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/events/<int:event_id>/delete', methods=['POST'])
def api_delete_event(event_id):
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT image FROM events WHERE id=%s", (event_id,))
        row = cursor.fetchone()
        if not row:
            cursor.close()
            return jsonify({'error': 'Event not found'}), 404
        image_path = row[0]
        cursor.execute("DELETE FROM events WHERE id=%s", (event_id,))
        mysql.connection.commit()
        cursor.close()
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                pass
        return jsonify({'success': True, 'id': event_id}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500


# =====================================================================
# LIBRARY CARDS
# =====================================================================

@admin_bp.route('/api/users/search')
def api_users_search():
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'error': 'Unauthorized'}), 401

    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify({'users': []})

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, username, firstname, lastname, phone_number, address
        FROM users WHERE role='user' AND is_active=1
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    cur.close()

    results = []
    for r in rows:
        fn = safe_decrypt_pii(r[2]) or ''
        ln = safe_decrypt_pii(r[3]) or ''
        fullname = f"{fn} {ln}".strip().lower()
        if q in fn.lower() or q in ln.lower() or q in fullname:
            results.append({
                'id':           r[0],
                'username':     safe_decrypt_email(r[1]),
                'firstname':    fn,
                'lastname':     ln,
                'phone_number': safe_decrypt_pii(r[4]) if r[4] else '',
                'address':      safe_decrypt_pii(r[5]) if r[5] else '',
            })
        if len(results) >= 15:
            break

    return jsonify({'users': results})


@admin_bp.route('/library-cards')
def library_cards_page():
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("admins/library_cards.html")


@admin_bp.route('/register/member', methods=['POST'])
def register_member():
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')

    user_id     = request.form.get('user_id', '').strip() or None
    firstname   = request.form.get('firstname', '').strip()
    lastname    = request.form.get('lastname',  '').strip()
    phone       = request.form.get('phone',     '').strip() or None
    address     = request.form.get('address',   '').strip() or None
    date_issued = request.form.get('date',      '').strip()
    date_return = request.form.get('date_return', '').strip() or None
    card_type   = request.form.get('card_type',  '').strip() or None
    valid_until = request.form.get('valid_until','').strip() or None
    ren1_chk    = 1 if request.form.get('renewal1_checked') == '1' else 0
    ren1_date   = request.form.get('renewal1_date', '').strip() or None
    ren2_chk    = 1 if request.form.get('renewal2_checked') == '1' else 0
    ren2_date   = request.form.get('renewal2_date', '').strip() or None

    book_ids_raw = request.form.get('book_ids', '[]')
    try:
        book_ids = json.loads(book_ids_raw)
    except (ValueError, TypeError):
        book_ids = []

    if not firstname or not lastname:
        flash("First name and last name are required.", "danger")
        return redirect('/library-cards')

    try:
        photo_path = save_card_photo(request.files.get('photo'), 'member')
    except ValueError as e:
        flash(str(e), "danger")
        return redirect('/library-cards')

    snapshots = resolve_book_snapshots(book_ids)

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO library_cards (
                card_type_category, user_id, firstname, lastname, phone_number, address,
                date_issued, date_return,
                renewal1_checked, renewal1_date, renewal2_checked, renewal2_date,
                card_type, valid_until, photo_path, registered_by
            ) VALUES ('member',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (user_id, encrypt_pii(firstname), encrypt_pii(lastname),
              encrypt_pii(phone) if phone else None,
              encrypt_pii(address) if address else None,
              date_issued, date_return,
              ren1_chk, ren1_date, ren2_chk, ren2_date, card_type, valid_until,
              photo_path, session['user_id']))
        mysql.connection.commit()
        card_id = cur.lastrowid
        cur.close()
        insert_card_books(card_id, snapshots)
        update_inventory_on_borrow(snapshots)
        flash(f"Member '{firstname} {lastname}' registered successfully!", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect('/library-cards')


@admin_bp.route('/register/borrower', methods=['POST'])
def register_borrower():
    if not is_logged_in() or require_role('admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')

    firstname   = request.form.get('firstname',   '').strip()
    lastname    = request.form.get('lastname',    '').strip()
    phone       = request.form.get('phone',       '').strip() or None
    address     = request.form.get('address',     '').strip() or None
    date_issued = request.form.get('date',        '').strip()
    date_return = request.form.get('date_return', '').strip() or None
    card_type   = request.form.get('card_type',   '').strip() or None
    valid_until = request.form.get('valid_until', '').strip() or None
    ren1_chk    = 1 if request.form.get('renewal1_checked') == '1' else 0
    ren1_date   = request.form.get('renewal1_date', '').strip() or None
    ren2_chk    = 1 if request.form.get('renewal2_checked') == '1' else 0
    ren2_date   = request.form.get('renewal2_date', '').strip() or None

    book_ids_raw = request.form.get('book_ids', '[]')
    try:
        book_ids = json.loads(book_ids_raw)
    except (ValueError, TypeError):
        book_ids = []

    if not firstname or not lastname:
        flash("First name and last name are required.", "danger")
        return redirect('/library-cards')
    if not date_return:
        flash("Date of return is required.", "danger")
        return redirect('/library-cards')

    try:
        photo_path = save_card_photo(request.files.get('photo'), 'borrower')
    except ValueError as e:
        flash(str(e), "danger")
        return redirect('/library-cards')

    snapshots = resolve_book_snapshots(book_ids)

    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO library_cards (
                card_type_category, user_id, firstname, lastname, phone_number, address,
                date_issued, date_return,
                renewal1_checked, renewal1_date, renewal2_checked, renewal2_date,
                card_type, valid_until, photo_path, registered_by
            ) VALUES ('borrower',NULL,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (encrypt_pii(firstname), encrypt_pii(lastname),
              encrypt_pii(phone) if phone else None,
              encrypt_pii(address) if address else None,
              date_issued, date_return,
              ren1_chk, ren1_date, ren2_chk, ren2_date, card_type, valid_until,
              photo_path, session['user_id']))
        mysql.connection.commit()
        card_id = cur.lastrowid
        cur.close()
        insert_card_books(card_id, snapshots)
        update_inventory_on_borrow(snapshots)
        flash(f"Borrower '{firstname} {lastname}' registered successfully!", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect('/library-cards')


@admin_bp.route('/api/library-cards')
def api_library_cards():
    if not is_logged_in() or require_role('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    cat   = request.args.get('type', '')
    q     = request.args.get('q',    '').strip().lower()
    limit = min(int(request.args.get('limit', 100)), 500)

    conditions, params = [], []
    if cat in ('member', 'borrower'):
        conditions.append("lc.card_type_category = %s")
        params.append(cat)

    where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''

    cur = mysql.connection.cursor()
    cur.execute(f"""
        SELECT DISTINCT
            lc.id, lc.card_type_category, lc.firstname, lc.lastname,
            lc.phone_number, lc.address, lc.date_issued, lc.date_return,
            lc.renewal1_checked, lc.renewal1_date,
            lc.renewal2_checked, lc.renewal2_date,
            lc.card_type, lc.valid_until, lc.photo_path, lc.created_at,
            u.firstname, u.lastname, lc.user_id
        FROM library_cards lc
        LEFT JOIN users u ON u.id = lc.registered_by
        LEFT JOIN library_card_books lcb ON lcb.card_id = lc.id
        {where}
        ORDER BY lc.created_at DESC LIMIT %s
    """, params + [limit])
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
            'book_id': br[1], 'title': br[2],
            'author': br[3], 'isbn': br[4], 'quantity': br[5] or 1,
        })

    cards = []
    for r in rows:
        photo_url = ('/' + r[14].replace('\\', '/')) if r[14] else ''
        fn = safe_decrypt_pii(r[2])
        ln = safe_decrypt_pii(r[3])

        if q and q not in (fn or '').lower() and q not in (ln or '').lower() \
                and q not in f"{fn} {ln}".lower():
            continue

        cards.append({
            'id': r[0], 'type': r[1],
            'firstname': fn, 'lastname': ln,
            'phone_number': safe_decrypt_pii(r[4]) if r[4] else '',
            'address':      safe_decrypt_pii(r[5]) if r[5] else '',
            'date_issued':      str(r[6])  if r[6]  else '',
            'date_return':      str(r[7])  if r[7]  else '',
            'renewal1_checked': bool(r[8]),
            'renewal1_date':    str(r[9])  if r[9]  else '',
            'renewal2_checked': bool(r[10]),
            'renewal2_date':    str(r[11]) if r[11] else '',
            'card_type': r[12] or '', 'valid_until': r[13] or '',
            'photo_url': photo_url, 'created_at': fmt_dt(r[15]),
            'registered_by': f"{safe_decrypt_pii(r[16]) or ''} {safe_decrypt_pii(r[17]) or ''}".strip() or '—',
            'user_id': r[18],
            'books': books_by_card.get(r[0], []),
        })

    return jsonify({'cards': cards, 'total': len(cards)})


@admin_bp.route('/api/library-cards/<int:card_id>', methods=['GET'])
def api_get_library_card(card_id):
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'error': 'Unauthorized'}), 401

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, card_type_category, firstname, lastname, phone_number, address,
               date_issued, date_return, renewal1_checked, renewal1_date,
               renewal2_checked, renewal2_date, card_type, valid_until, photo_path
        FROM library_cards WHERE id=%s
    """, (card_id,))
    r = cur.fetchone()
    if not r:
        cur.close()
        return jsonify({'error': 'Not found'}), 404

    cur.execute("""
        SELECT book_id, book_title, book_author, book_isbn, quantity
        FROM library_card_books WHERE card_id=%s
    """, (card_id,))
    book_rows = cur.fetchall()
    cur.close()

    return jsonify({
        'id': r[0], 'type': r[1],
        'firstname':    safe_decrypt_pii(r[2]),
        'lastname':     safe_decrypt_pii(r[3]),
        'phone_number': safe_decrypt_pii(r[4]) if r[4] else '',
        'address':      safe_decrypt_pii(r[5]) if r[5] else '',
        'date_issued':      str(r[6]) if r[6] else '',
        'date_return':      str(r[7]) if r[7] else '',
        'renewal1_checked': bool(r[8]),
        'renewal1_date':    str(r[9])  if r[9]  else '',
        'renewal2_checked': bool(r[10]),
        'renewal2_date':    str(r[11]) if r[11] else '',
        'card_type':  r[12] or '',
        'valid_until': r[13] or '',
        'photo_url': ('/' + r[14].replace('\\', '/')) if r[14] else '',
        'books': [{'book_id': br[0], 'title': br[1], 'author': br[2],
                   'isbn': br[3], 'quantity': br[4] or 1} for br in book_rows],
    })


@admin_bp.route('/api/library-cards/<int:card_id>/update', methods=['POST'])
def api_update_library_card(card_id):
    if not is_logged_in() or require_role('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    data        = request.get_json(silent=True) or {}
    firstname   = data.get('firstname', '').strip()
    lastname    = data.get('lastname',  '').strip()
    phone       = data.get('phone',     '').strip() or None
    address     = data.get('address',   '').strip() or None
    date_return = data.get('date_return','').strip() or None
    card_type   = data.get('card_type', '').strip() or None
    valid_until = data.get('valid_until','').strip() or None
    ren1_chk    = 1 if data.get('renewal1_checked') else 0
    ren1_date   = data.get('renewal1_date', '') or None
    ren2_chk    = 1 if data.get('renewal2_checked') else 0
    ren2_date   = data.get('renewal2_date', '') or None
    book_ids    = data.get('book_ids', [])

    if not firstname or not lastname:
        return jsonify({'error': 'First name and last name are required.'}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT book_id, quantity FROM library_card_books WHERE card_id=%s", (card_id,))
        old_books = cur.fetchall()

        cur.execute("""
            UPDATE library_cards SET firstname=%s, lastname=%s, phone_number=%s, address=%s,
                   date_return=%s, renewal1_checked=%s, renewal1_date=%s,
                   renewal2_checked=%s, renewal2_date=%s, card_type=%s, valid_until=%s
            WHERE id=%s
        """, (encrypt_pii(firstname), encrypt_pii(lastname),
              encrypt_pii(phone) if phone else None,
              encrypt_pii(address) if address else None,
              date_return,
              ren1_chk, ren1_date, ren2_chk, ren2_date, card_type, valid_until, card_id))

        for book_id, qty in old_books:
            cur.execute("""
                UPDATE book_inventory
                SET available_copies = LEAST(volumes, available_copies + %s)
                WHERE book_id=%s
            """, (qty or 1, book_id))

        cur.execute("DELETE FROM library_card_books WHERE card_id=%s", (card_id,))
        mysql.connection.commit()
        cur.close()

        snapshots = resolve_book_snapshots(book_ids)
        insert_card_books(card_id, snapshots)
        update_inventory_on_borrow(snapshots)

        return jsonify({'success': True}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/library-cards/<int:card_id>/return', methods=['POST'])
def api_return_library_card(card_id):
    if not is_logged_in() or require_role('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    data        = request.get_json(silent=True) or {}
    return_date = data.get('return_date', '').strip()
    items       = data.get('items', [])

    if not return_date:
        return jsonify({'error': 'Return date is required.'}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM library_cards WHERE id=%s", (card_id,))
        if not cur.fetchone():
            cur.close()
            return jsonify({'error': 'Card not found.'}), 404

        cur.execute("""
            SELECT id, book_id, book_title, book_author, book_isbn, quantity
            FROM library_card_books WHERE card_id=%s ORDER BY id ASC
        """, (card_id,))
        card_books = cur.fetchall()

        cur.execute("""
            INSERT INTO book_returns (card_id, return_date, processed_by) VALUES (%s,%s,%s)
        """, (card_id, return_date, session['user_id']))
        mysql.connection.commit()
        return_id = cur.lastrowid

        for item in items:
            idx          = item.get('row_index', -1)
            qty_returned = max(0, int(item.get('qty_returned', 0) or 0))
            if idx < 0 or idx >= len(card_books) or qty_returned == 0:
                continue
            cb = card_books[idx]
            cur.execute("""
                INSERT INTO book_return_items
                    (return_id, card_book_id, book_title, book_author, book_isbn, qty_returned)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (return_id, cb[0], cb[2], cb[3], cb[4], qty_returned))

            cur.execute("SELECT id FROM book_inventory WHERE book_id=%s", (cb[1],))
            if cur.fetchone():
                cur.execute("""
                    UPDATE book_inventory
                    SET available_copies = LEAST(volumes, available_copies + %s)
                    WHERE book_id=%s
                """, (qty_returned, cb[1]))
            else:
                cur.execute("""
                    INSERT INTO book_inventory
                        (book_id, volumes, available_copies, damaged_copies, lost_copies, status)
                    VALUES (%s,%s,%s,0,0,'Available')
                """, (cb[1], qty_returned, qty_returned))

        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'return_id': return_id}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/library-cards/returns')
def api_list_returns():
    if not is_logged_in() or require_role('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT br.id, lc.id, lc.card_type_category, lc.firstname, lc.lastname,
                   lc.phone_number, lc.date_issued, br.return_date, u.firstname, u.lastname
            FROM book_returns br
            JOIN library_cards lc ON lc.id = br.card_id
            LEFT JOIN users u ON u.id = br.processed_by
            ORDER BY br.created_at DESC LIMIT 200
        """)
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
                'firstname':    safe_decrypt_pii(r[3]),
                'lastname':     safe_decrypt_pii(r[4]),
                'phone_number': safe_decrypt_pii(r[5]) if r[5] else '',
                'date_issued':  str(r[6]) if r[6] else '',
                'return_date':  str(r[7]) if r[7] else '',
                'processed_by': f"{safe_decrypt_pii(r[8]) or ''} {safe_decrypt_pii(r[9]) or ''}".strip() or '—',
                'books': items_by_return.get(r[0], []),
            }
            for r in rows
        ]
        return jsonify({'returns': returns}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/library-cards/<int:card_id>/returns')
def api_card_returns(card_id):
    if not is_logged_in() or require_role('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT br.id, br.return_date, br.created_at, u.firstname, u.lastname
            FROM book_returns br
            LEFT JOIN users u ON u.id = br.processed_by
            WHERE br.card_id=%s ORDER BY br.created_at DESC
        """, (card_id,))
        rows    = cur.fetchall()
        returns = []
        for r in rows:
            cur.execute("""
                SELECT book_title, book_author, book_isbn, qty_returned
                FROM book_return_items WHERE return_id=%s
            """, (r[0],))
            items = [{'title': i[0], 'author': i[1], 'isbn': i[2], 'qty_returned': i[3]}
                     for i in cur.fetchall()]
            returns.append({
                'id':         r[0],
                'return_date': str(r[1]) if r[1] else '',
                'created_at':  fmt_dt(r[2]),
                'processed_by': f"{safe_decrypt_pii(r[3]) or ''} {safe_decrypt_pii(r[4]) or ''}".strip() or '—',
                'items': items,
            })
        cur.close()
        return jsonify({'returns': returns}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/library-cards/<int:card_id>/delete', methods=['POST'])
def api_delete_library_card(card_id):
    if not is_logged_in() or require_role('admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT photo_path FROM library_cards WHERE id=%s", (card_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            return jsonify({'error': 'Not found'}), 404
        photo_path = row[0]
        cur.execute("DELETE FROM library_cards WHERE id=%s", (card_id,))
        mysql.connection.commit()
        cur.close()
        if photo_path and os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except OSError:
                pass
        return jsonify({'success': True}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500