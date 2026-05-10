"""
routes/librarian_routes.py
---------------------------
Blueprint: librarian_bp

All librarian pages and APIs:
  - Home, Dashboard, Book Management, User Management
  - Announcements, Inventory, Event Calendar
  - ISBN lookup (isbn_bp sub-blueprint)
"""

import json
import re
import os
import time
from datetime import datetime, date

from flask import (
    Blueprint, render_template, request, redirect,
    session, flash, jsonify, url_for,
)
from flask_bcrypt import Bcrypt
import requests as http_requests

from conn import mysql, app
from helpers import (
    is_logged_in, require_role,
    encrypt_data, decrypt_data, safe_decrypt, fmt_dt,
    build_users_data,
    build_book_data, BOOK_INVENTORY_QUERY,
    save_card_photo, resolve_book_snapshots,
    insert_card_books, update_inventory_on_borrow,
    event_to_dict,
)
from email_config import send_registration_decision_email
bcrypt = Bcrypt(app)

librarian_bp = Blueprint("librarian_bp", __name__)
isbn_bp      = Blueprint("isbn_bp",      __name__)

# ── Event upload config (shared with librarian) ───────────────────────
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

@librarian_bp.route('/librarian/home')
def librarian_home():
    if not is_logged_in() or require_role('librarian'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("librarians/librarian_home.html")

@librarian_bp.route('/librarian/library-cards')
def library_cards_page():
    if not is_logged_in() or require_role('librarian'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("librarians/library_cards.html")

@librarian_bp.route('/librarian_user_management')
def librarian_user_management():
    if not is_logged_in() or require_role('librarian'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, username, firstname, lastname, password, failed_attempts, is_locked,
               lock_until, created_at, status, last_seen, role
        FROM users WHERE role='user' ORDER BY created_at DESC
    """)
    users = cur.fetchall()
    cur.close()
    return render_template('librarians/user_management.html', users=build_users_data(users))


@librarian_bp.route('/librarian_book_management')
def librarian_book_management():
    if not is_logged_in() or require_role('admin', 'librarian'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    cursor = mysql.connection.cursor()
    cursor.execute(BOOK_INVENTORY_QUERY)
    books = cursor.fetchall()
    cursor.close()
    return render_template('librarians/book_management.html', books=build_book_data(books))


# =====================================================================
# BOOK ACTIONS
# =====================================================================

@librarian_bp.route('/librarian_delete_book/<int:book_id>', methods=['POST'])
def librarian_delete_book(book_id):
    if not is_logged_in() or require_role('admin', 'librarian'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT id FROM books WHERE id=%s", (book_id,))
        if not cursor.fetchone():
            cursor.close()
            flash("Book not found!", "danger")
            return redirect('/librarian_book_management')
        cursor.execute("DELETE FROM books WHERE id=%s", (book_id,))
        mysql.connection.commit()
        cursor.close()
        flash("Book deleted successfully!", "success")
    except Exception as e:
        mysql.connection.rollback()
        cursor.close()
        flash(f"Error: {str(e)}", "danger")
    return redirect('/librarian_book_management')


@librarian_bp.route('/librarian_update_book', methods=['POST'])
def librarian_update_book():
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    try:
        book_id       = request.form.get('book_id')
        title         = request.form.get('title', '').strip()
        author        = request.form.get('author', '').strip()
        isbn          = request.form.get('isbn', '').strip()
        category      = request.form.get('category', '').strip()
        genre         = request.form.get('genre', '').strip()
        publisher     = request.form.get('publisher', '').strip()
        is_borrowable = 1 if request.form.get("is_borrowable") in ("1", "true", "on") else 0

        if not all([book_id, title, author, isbn]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE books SET title=%s, author=%s, isbn=%s, category=%s,
                   genre=%s, publisher=%s, is_borrowable=%s WHERE id=%s
        """, (
            encrypt_data(title), encrypt_data(author), encrypt_data(isbn),
            encrypt_data(category) if category else None,
            encrypt_data(genre)    if genre    else None,
            encrypt_data(publisher) if publisher else None,
            is_borrowable, book_id,
        ))
        mysql.connection.commit()
        cursor.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# =====================================================================
# DASHBOARD
# =====================================================================

@librarian_bp.route('/librarian_dashboard')
def librarian_dashboard():
    if not is_logged_in() or session.get('role') != 'librarian':
        return redirect(url_for('auth_bp.login'))
    return render_template("librarians/dashboard.html")


@librarian_bp.route('/librarian_dashboard/stats')
def librarian_dashboard_stats():
    if not is_logged_in() or session.get('role') != 'librarian':
        return jsonify({'error': 'Unauthorized'}), 403

    from datetime import date, timedelta
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT DATE(created_at) AS day, COUNT(*) AS total
        FROM books WHERE created_at >= CURDATE() - INTERVAL 6 DAY
        GROUP BY DATE(created_at) ORDER BY day ASC
    """)
    book_rows = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM books")
    total_books = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE role='user'")
    total_users = cur.fetchone()[0]
    cur.close()

    today    = date.today()
    days_map = {today - timedelta(days=i): 0 for i in range(6, -1, -1)}
    for row in book_rows:
        d = row[0] if isinstance(row[0], date) else row[0].date()
        if d in days_map:
            days_map[d] = int(row[1])

    return jsonify({
        'books_per_day': {
            'labels': [d.strftime('%a %d') for d in sorted(days_map)],
            'data':   [days_map[d] for d in sorted(days_map)],
        },
        'totals': {'books': total_books, 'users': total_users},
    })


# =====================================================================
# ANNOUNCEMENTS
# =====================================================================

@librarian_bp.route('/librarian/announcements')
def librarian_announcements():
    if not is_logged_in() or require_role('librarian', 'admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("librarians/announcement.html")


@librarian_bp.route('/api/announcements', methods=['GET'])
def get_announcements():
    if not is_logged_in() or require_role('librarian', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, title, body, category, pinned, author, created_at
        FROM announcements ORDER BY pinned DESC, created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()

    return jsonify({'announcements': [
        {
            'id': r[0], 'title': r[1], 'body': r[2], 'category': r[3],
            'pinned': bool(r[4]), 'author': r[5],
            'created_at': r[6].isoformat() if r[6] else '',
        }
        for r in rows
    ]})


@librarian_bp.route('/api/announcements', methods=['POST'])
def create_announcement():
    if not is_logged_in() or require_role('librarian', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    data     = request.get_json()
    title    = (data.get('title') or '').strip()
    body     = (data.get('body')  or '').strip()
    category = data.get('category', 'general')
    pinned   = bool(data.get('pinned', False))

    if not title or not body:
        return jsonify({'error': 'Title and body are required'}), 400
    if category not in ('general', 'urgent', 'event', 'reminder'):
        category = 'general'

    cur = mysql.connection.cursor()
    cur.execute("SELECT firstname, lastname, role FROM users WHERE id=%s", (session['user_id'],))
    user = cur.fetchone()
    if user:
        role_label = {'admin': 'Admin', 'librarian': 'Librarian', 'user': 'User'}.get(user[2], 'Librarian')
        author = f"{user[0]} {user[1]} ({role_label})"
    else:
        author = 'Librarian'

    cur.execute("""
        INSERT INTO announcements (title, body, category, pinned, author)
        VALUES (%s,%s,%s,%s,%s)
    """, (title, body, category, int(pinned), author))
    mysql.connection.commit()
    new_id = cur.lastrowid

    cur.execute("""
        SELECT id, title, body, category, pinned, author, created_at
        FROM announcements WHERE id=%s
    """, (new_id,))
    row = cur.fetchone()
    cur.close()

    return jsonify({
        'success': True,
        'announcement': {
            'id': row[0], 'title': row[1], 'body': row[2], 'category': row[3],
            'pinned': bool(row[4]), 'author': row[5],
            'created_at': row[6].isoformat() if row[6] else '',
        },
    }), 201


@librarian_bp.route('/api/announcements/<int:ann_id>/update', methods=['POST'])
def update_announcement(ann_id):
    if not is_logged_in() or require_role('librarian', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    data     = request.get_json()
    title    = (data.get('title') or '').strip()
    body     = (data.get('body')  or '').strip()
    category = data.get('category', 'general')
    pinned   = bool(data.get('pinned', False))

    if not title or not body:
        return jsonify({'error': 'Title and body are required'}), 400
    if category not in ('general', 'urgent', 'event', 'reminder'):
        category = 'general'

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE announcements SET title=%s, body=%s, category=%s, pinned=%s WHERE id=%s
    """, (title, body, category, int(pinned), ann_id))
    mysql.connection.commit()
    cur.close()
    return jsonify({'success': True})


@librarian_bp.route('/api/announcements/<int:ann_id>/delete', methods=['POST'])
def delete_announcement(ann_id):
    if not is_logged_in() or require_role('librarian', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM announcements WHERE id=%s", (ann_id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({'success': True})


@librarian_bp.route('/api/announcements/<int:ann_id>/pin', methods=['POST'])
def toggle_pin(ann_id):
    if not is_logged_in() or require_role('librarian', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 401
    cur = mysql.connection.cursor()
    cur.execute("SELECT pinned FROM announcements WHERE id=%s", (ann_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return jsonify({'error': 'Not found'}), 404
    new_pinned = 0 if row[0] else 1
    cur.execute("UPDATE announcements SET pinned=%s WHERE id=%s", (new_pinned, ann_id))
    mysql.connection.commit()
    cur.close()
    return jsonify({'success': True, 'pinned': bool(new_pinned)})


# =====================================================================
# INVENTORY
# =====================================================================

@librarian_bp.route('/librarian/inventory')
def librarian_inventory():
    if not is_logged_in() or require_role('librarian', 'admin'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("librarians/inventory_status.html")


@librarian_bp.route('/api/inventory')
def api_inventory():
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'error': 'Unauthorized'}), 401

    cursor = mysql.connection.cursor()
    cursor.execute(BOOK_INVENTORY_QUERY)
    rows = cursor.fetchall()
    cursor.close()

    return jsonify({'books': build_book_data(rows)})


@librarian_bp.route('/api/inventory/<int:book_id>/update', methods=['POST'])
def update_inventory(book_id):
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'error': 'Unauthorized'}), 401

    data             = request.get_json()
    total_copies     = data.get('total_copies')
    available_copies = data.get('available_copies')
    damaged_copies   = data.get('damaged_copies')
    lost_copies      = data.get('lost_copies')
    status           = data.get('status')
    shelf_location   = data.get('shelf_location')

    if status and status not in ('Available', 'Damaged', 'Lost'):
        return jsonify({'error': 'Invalid status value'}), 400

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM book_inventory WHERE book_id=%s", (book_id,))
        if cur.fetchone():
            fields, values = [], []
            if total_copies     is not None: fields.append("total_copies=%s");     values.append(int(total_copies))
            if available_copies is not None: fields.append("available_copies=%s"); values.append(int(available_copies))
            if damaged_copies   is not None: fields.append("damaged_copies=%s");   values.append(int(damaged_copies))
            if lost_copies      is not None: fields.append("lost_copies=%s");      values.append(int(lost_copies))
            if status:                       fields.append("status=%s");            values.append(status)
            if 'shelf_location' in data:     fields.append("shelf_location=%s");   values.append(shelf_location)
            if fields:
                values.append(book_id)
                cur.execute(f"UPDATE book_inventory SET {', '.join(fields)} WHERE book_id=%s", values)
        else:
            cur.execute("""
                INSERT INTO book_inventory
                    (book_id, total_copies, available_copies, damaged_copies, lost_copies, status, shelf_location)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                book_id,
                int(total_copies)     if total_copies     is not None else 1,
                int(available_copies) if available_copies is not None else 1,
                int(damaged_copies)   if damaged_copies   is not None else 0,
                int(lost_copies)      if lost_copies      is not None else 0,
                status                if status else 'Available',
                shelf_location,
            ))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@librarian_bp.route('/api/inventory/summary')
def api_inventory_summary():
    if not is_logged_in() or require_role('admin', 'librarian'):
        return jsonify({'error': 'Unauthorized'}), 401
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM books")
    total_titles = cur.fetchone()[0]
    cur.execute("""
        SELECT SUM(CASE WHEN status='Available' THEN 1 ELSE 0 END),
               SUM(COALESCE(damaged_copies,0)), SUM(COALESCE(lost_copies,0))
        FROM book_inventory
    """)
    row = cur.fetchone()
    cur.close()
    return jsonify({
        'total_titles': total_titles,
        'available':    int(row[0] or 0),
        'damaged':      int(row[1] or 0),
        'lost':         int(row[2] or 0),
    })

# =====================================================================
# LIBRARIAN ACCOUNT REQUESTS (Card Renewal Only)
# =====================================================================

@librarian_bp.route('/librarian/account-requests')
def librarian_account_requests():
    if not is_logged_in() or require_role('librarian'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("librarians/librarian_account_requests.html")


@librarian_bp.route('/api/librarian/account-requests', methods=['GET'])
def librarian_get_account_requests():
    if not is_logged_in() or require_role('librarian'):
        return jsonify({'error': 'Unauthorized'}), 401

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT ar.id, ar.user_id, ar.username, ar.request_type,
               ar.reason, ar.status, ar.created_at, ar.reviewed_at, ar.admin_note,
               u.firstname, u.lastname, ar.card_id,
               ar.renewal1_checked, ar.renewal1_date,
               ar.renewal2_checked, ar.renewal2_date
        FROM account_requests ar
        LEFT JOIN users u ON u.id = ar.user_id
        WHERE ar.request_type = 'renew'
        ORDER BY ar.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()

    return jsonify({'requests': [
        {
            'id': r[0], 'user_id': r[1], 'username': r[2],
            'request_type': r[3], 'reason': r[4], 'status': r[5],
            'created_at': fmt_dt(r[6]), 'reviewed_at': fmt_dt(r[7]) if r[7] else None,
            'admin_note': r[8] or '',
            'fullname': f"{r[9] or ''} {r[10] or ''}".strip(),
            'card_id': r[11],
            'renewal1_checked': bool(r[12]) if r[12] is not None else False,
            'renewal1_date':    str(r[13]) if r[13] else '',
            'renewal2_checked': bool(r[14]) if r[14] is not None else False,
            'renewal2_date':    str(r[15]) if r[15] else '',
        }
        for r in rows
    ]})


@librarian_bp.route('/api/librarian/account-requests/<int:req_id>/approve', methods=['POST'])
def librarian_approve_account_request(req_id):
    if not is_logged_in() or require_role('librarian'):
        return jsonify({'error': 'Unauthorized'}), 401

    librarian_id = session['user_id']
    admin_note   = (request.get_json() or {}).get('note', '').strip()

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT user_id, request_type, card_id,
               renewal1_checked, renewal1_date, renewal2_checked, renewal2_date
        FROM account_requests
        WHERE id=%s AND status='pending' AND request_type='renew'
    """, (req_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        return jsonify({'error': 'Request not found, already processed, or not a renewal.'}), 404

    target_user_id, req_type, card_id = row[0], row[1], row[2]
    ren1_chk, ren1_date, ren2_chk, ren2_date = row[3], row[4], row[5], row[6]

    try:
        cur.execute("""
            UPDATE library_cards
            SET renewal1_checked=%s, renewal1_date=%s,
                renewal2_checked=%s, renewal2_date=%s
            WHERE id=%s
        """, (ren1_chk, ren1_date, ren2_chk, ren2_date, card_id))

        cur.execute("""
            UPDATE account_requests SET status='approved', reviewed_by=%s,
                   reviewed_at=%s, admin_note=%s WHERE id=%s
        """, (librarian_id, datetime.now(), admin_note, req_id))

        notif_title = 'Library Card Renewal — Approved ✓'
        notif_body  = "Your library card renewal has been approved." + (
            f' Note: "{admin_note}"' if admin_note else ""
        )

        cur.execute("SELECT firstname, lastname FROM users WHERE id=%s", (librarian_id,))
        lr     = cur.fetchone()
        author = f"{lr[0]} {lr[1]} (Librarian)"[:100] if lr else "Library Staff"

        cur.execute("""
            INSERT INTO announcements (title, body, category, pinned, author, target_user_id)
            VALUES (%s, %s, 'general', 0, %s, %s)
        """, (notif_title, notif_body, author, target_user_id))

        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True}), 200

    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'error': str(e)}), 500


@librarian_bp.route('/api/librarian/account-requests/<int:req_id>/reject', methods=['POST'])
def librarian_reject_account_request(req_id):
    if not is_logged_in() or require_role('librarian'):
        return jsonify({'error': 'Unauthorized'}), 401

    librarian_id = session['user_id']
    admin_note   = (request.get_json() or {}).get('note', '').strip()

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT user_id, request_type FROM account_requests
        WHERE id=%s AND status='pending' AND request_type='renew'
    """, (req_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        return jsonify({'error': 'Request not found, already processed, or not a renewal.'}), 404

    target_user_id = row[0]

    try:
        cur.execute("""
            UPDATE account_requests SET status='rejected', reviewed_by=%s,
                   reviewed_at=%s, admin_note=%s WHERE id=%s
        """, (librarian_id, datetime.now(), admin_note, req_id))

        notif_title = 'Library Card Renewal — Not Approved'
        notif_body  = "Your card renewal request was not approved. " + (
            f'Reason: "{admin_note}"' if admin_note else "Contact the library for more info."
        )

        cur.execute("SELECT firstname, lastname FROM users WHERE id=%s", (librarian_id,))
        lr     = cur.fetchone()
        author = f"{lr[0]} {lr[1]} (Librarian)"[:100] if lr else "Library Staff"

        cur.execute("""
            INSERT INTO announcements (title, body, category, pinned, author, target_user_id)
            VALUES (%s, %s, 'urgent', 0, %s, %s)
        """, (notif_title, notif_body, author, target_user_id))

        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True}), 200

    except Exception as e:
        mysql.connection.rollback()
        cur.close()
        return jsonify({'error': str(e)}), 500


@librarian_bp.route('/api/librarian/account-requests/<int:req_id>/delete', methods=['POST'])
def librarian_delete_account_request(req_id):
    if not is_logged_in() or require_role('librarian'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            DELETE FROM account_requests
            WHERE id=%s AND status != 'pending' AND request_type='renew'
        """, (req_id,))
        if cur.rowcount == 0:
            cur.close()
            return jsonify({'error': 'Not found, still pending, or not a renewal.'}), 404
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500
# =====================================================================
# EVENT CALENDAR (librarian page — API is on admin_bp)
# =====================================================================

@librarian_bp.route('/librarian/event')
def librarian_event():
    if not is_logged_in() or require_role('librarian'):
        flash("Unauthorized access", "danger")
        return redirect('/')
    return render_template("librarians/calendar_event.html")


# =====================================================================
# ISBN VALIDATION & LOOKUP  (isbn_bp)
# =====================================================================

_REQ_TIMEOUT = 6
_MAX_RETRIES = 2
_isbn_cache: dict = {}
_CACHE_TTL  = 86_400   # 24 hours


def _clean_isbn(raw: str) -> str:
    return re.sub(r"[^0-9Xx]", "", raw).upper()


def _valid_isbn10(s: str) -> bool:
    if len(s) != 10:
        return False
    total = sum(int(c) * (10 - i) for i, c in enumerate(s[:-1]) if c.isdigit())
    check = s[-1]
    total += 10 if check == 'X' else (int(check) if check.isdigit() else -1)
    return total % 11 == 0


def _valid_isbn13(s: str) -> bool:
    if len(s) != 13 or not s.isdigit():
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(s[:-1]))
    return (10 - total % 10) % 10 == int(s[-1])


def validate_isbn(raw: str):
    cleaned = _clean_isbn(raw)
    return (_valid_isbn10(cleaned) or _valid_isbn13(cleaned)), cleaned


def _sanitize(val, max_len: int = 500) -> str:
    if val is None:
        return ""
    return re.sub(r"<[^>]+>", "", str(val)).strip()[:max_len]


def _get(url: str, params: dict = None):
    for attempt in range(_MAX_RETRIES):
        try:
            r = http_requests.get(url, params=params, timeout=_REQ_TIMEOUT)
            if r.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                continue
            return r
        except http_requests.RequestException:
            if attempt == _MAX_RETRIES - 1:
                return None
            time.sleep(0.5)
    return None


def _fetch_google_books(isbn: str):
    r = _get("https://www.googleapis.com/books/v1/volumes", params={"q": f"isbn:{isbn}"})
    if not r or r.status_code != 200:
        return None
    payload = r.json()
    if not payload.get("totalItems") or not payload.get("items"):
        return None
    info    = payload["items"][0].get("volumeInfo", {})
    authors = ", ".join(_sanitize(a, 120) for a in info.get("authors", []) if a)
    cats    = [p.strip() for c in info.get("categories", []) for p in c.split("/") if p.strip()]
    cats_s  = ", ".join(_sanitize(c, 80) for c in cats[:5])
    cat_l   = [c.strip() for c in cats_s.split(",") if c.strip()]
    img     = info.get("imageLinks", {})
    thumb   = (img.get("thumbnail") or img.get("smallThumbnail") or "").replace("http://", "https://")
    return {
        "source": "Google Books", "title": _sanitize(info.get("title", ""), 300),
        "subtitle": _sanitize(info.get("subtitle", ""), 500), "authors": authors,
        "publisher": _sanitize(info.get("publisher", ""), 200),
        "published_date": _sanitize(info.get("publishedDate", ""), 20),
        "description": _sanitize(info.get("description", ""), 2000),
        "page_count": int(info["pageCount"]) if info.get("pageCount") else None,
        "categories": cats_s,
        "category": cat_l[0] if cat_l else "",
        "genre":    cat_l[1] if len(cat_l) > 1 else "",
        "language": _sanitize(info.get("language", ""), 5).lower(),
        "thumbnail": thumb, "isbn": isbn,
    }


def _fetch_open_library(isbn: str):
    r = _get("https://openlibrary.org/api/books",
             params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "details"})
    if not r or r.status_code != 200:
        return None
    data = r.json()
    key  = f"ISBN:{isbn}"
    if key not in data:
        return None
    info    = data[key].get("details", {})
    authors = ", ".join(
        _sanitize(a.get("name", ""), 120) for a in info.get("authors", []) if a.get("name")
    )
    subjects = []
    for s in info.get("subjects", [])[:5]:
        if isinstance(s, str):
            subjects.append(_sanitize(s, 80))
        elif isinstance(s, dict) and s.get("name"):
            subjects.append(_sanitize(s["name"], 80))
    cats_s  = ", ".join(subjects)
    cat_l   = [c.strip() for c in cats_s.split(",") if c.strip()]
    pubs    = info.get("publishers", [])
    publisher = ""
    if pubs:
        p = pubs[0]
        publisher = _sanitize(p.get("name", p) if isinstance(p, dict) else p, 200)
    desc_raw = info.get("description", "")
    if isinstance(desc_raw, dict):
        desc_raw = desc_raw.get("value", "")
    covers = info.get("covers", [])
    thumb  = f"https://covers.openlibrary.org/b/id/{covers[0]}-M.jpg" if covers else ""
    return {
        "source": "Open Library", "title": _sanitize(info.get("title", ""), 300),
        "subtitle": _sanitize(info.get("subtitle", ""), 500), "authors": authors,
        "publisher": publisher,
        "published_date": _sanitize(str(info.get("publish_date", "")), 20),
        "description": _sanitize(str(desc_raw), 2000),
        "page_count": int(info["number_of_pages"]) if info.get("number_of_pages") else None,
        "categories": cats_s,
        "category": cat_l[0] if cat_l else "",
        "genre":    cat_l[1] if len(cat_l) > 1 else "",
        "language": "", "thumbnail": thumb, "isbn": isbn,
    }


def _db_cache_get(isbn: str):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT meta_json FROM isbn_cache WHERE isbn=%s LIMIT 1", (isbn,))
        row = cur.fetchone()
        cur.close()
        if row and row[0]:
            return json.loads(row[0])
    except Exception:
        pass
    return None


def _db_cache_set(isbn: str, data: dict) -> None:
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO isbn_cache (isbn, meta_json) VALUES (%s,%s)
            ON DUPLICATE KEY UPDATE meta_json=VALUES(meta_json), fetched_at=NOW()
        """, (isbn, json.dumps(data)))
        mysql.connection.commit()
        cur.close()
    except Exception:
        pass


# ── ISBN Blueprint routes ────────────────────────────────────────────

@isbn_bp.route("/librarian_add_book", methods=["POST"])
def librarian_add_book():
    if not is_logged_in() or require_role("admin", "librarian"):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    title            = request.form.get("title",            "").strip()
    author           = request.form.get("author",           "").strip()
    isbn_raw         = request.form.get("isbn",             "").strip()
    category         = request.form.get("category",         "").strip()
    genre            = request.form.get("genre",            "").strip()
    publisher        = request.form.get("publisher",        "").strip()
    total_copies     = int(request.form.get("total_copies",     1) or 1)
    available_copies = int(request.form.get("available_copies", 1) or 1)
    shelf_location   = request.form.get("shelf_location",   "").strip() or None
    is_borrowable    = 1 if request.form.get("is_borrowable") in ("1","true","on") else 0
    subtitle         = request.form.get("subtitle",         "").strip() or None
    published_date   = request.form.get("published_date",   "").strip() or None
    description      = request.form.get("description",      "").strip() or None
    page_count_raw   = request.form.get("page_count",       "").strip()
    page_count       = int(page_count_raw) if page_count_raw.isdigit() else None
    language         = (request.form.get("language", "").strip()[:5].lower()) or None
    thumbnail_url    = request.form.get("thumbnail_url",    "").strip() or None

    meta_json_raw = request.form.get("isbn_meta_json", "").strip()
    meta          = {}
    if meta_json_raw:
        try:
            meta = json.loads(meta_json_raw)
        except (ValueError, TypeError):
            meta = {}
    api_source = _sanitize(meta.get("source", ""), 50) or None

    if not (title and author and isbn_raw):
        return jsonify({"success": False, "message": "Title, Author, and ISBN are required."}), 400

    valid, cleaned_isbn = validate_isbn(isbn_raw)
    if not valid:
        return jsonify({"success": False, "message": f"'{isbn_raw}' is not a valid ISBN."}), 422

    try:
        cursor   = mysql.connection.cursor()
        enc_isbn = encrypt_data(cleaned_isbn)
        cursor.execute("SELECT id FROM books WHERE isbn=%s", (enc_isbn,))
        if cursor.fetchone():
            cursor.close()
            return jsonify({"success": False, "message": "ISBN already exists."}), 409

        cursor.execute("""
            INSERT INTO books
                (title, author, isbn, category, genre, publisher,
                 subtitle, published_date, description, page_count,
                 language, thumbnail_url, api_source, is_borrowable, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
        """, (
            encrypt_data(title), encrypt_data(author), enc_isbn,
            encrypt_data(category) if category else None,
            encrypt_data(genre)    if genre    else None,
            encrypt_data(publisher) if publisher else None,
            subtitle, published_date, description, page_count,
            language, thumbnail_url, api_source, is_borrowable,
        ))
        mysql.connection.commit()
        new_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO book_inventory
                (book_id, total_copies, available_copies, damaged_copies, lost_copies, status, shelf_location)
            VALUES (%s,%s,%s,0,0,'Available',%s)
        """, (new_id, total_copies, available_copies, shelf_location))
        mysql.connection.commit()
        cursor.close()
        if meta:
            _db_cache_set(cleaned_isbn, meta)
        return jsonify({"success": True, "message": "Book added successfully!", "book_id": new_id}), 201
    except Exception as e:
        try:
            mysql.connection.rollback()
        except Exception:
            pass
        return jsonify({"success": False, "message": str(e)}), 500


@isbn_bp.route("/api/fetch-book-by-isbn", methods=["POST"])
def fetch_book_by_isbn():
    if not is_logged_in() or require_role("admin", "librarian"):
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    if request.is_json:
        raw_isbn = (request.get_json(silent=True) or {}).get("isbn", "")
    else:
        raw_isbn = request.form.get("isbn", "")

    raw_isbn = str(raw_isbn).strip()
    if not raw_isbn:
        return jsonify({"success": False, "message": "ISBN is required."}), 400

    valid, cleaned_isbn = validate_isbn(raw_isbn)
    if not valid:
        return jsonify({"success": False, "message": f"'{raw_isbn}' is not a valid ISBN."}), 422

    now = time.time()
    if cleaned_isbn in _isbn_cache:
        ts, cached = _isbn_cache[cleaned_isbn]
        if now - ts < _CACHE_TTL:
            return jsonify({"success": True, "data": cached, "source": cached.get("source", "cache"), "from_cache": True})

    db_cached = _db_cache_get(cleaned_isbn)
    if db_cached:
        _isbn_cache[cleaned_isbn] = (now, db_cached)
        return jsonify({"success": True, "data": db_cached, "source": db_cached.get("source","db_cache"), "from_cache": True})

    book_data = _fetch_google_books(cleaned_isbn) or _fetch_open_library(cleaned_isbn)
    if not book_data:
        return jsonify({
            "success": False,
            "message": "No book found for this ISBN. Fill in details manually.",
            "isbn":    cleaned_isbn,
        }), 404

    _db_cache_set(cleaned_isbn, book_data)
    _isbn_cache[cleaned_isbn] = (now, book_data)
    return jsonify({"success": True, "data": book_data, "source": book_data["source"], "from_cache": False})


@isbn_bp.route("/api/validate-isbn", methods=["GET"])
def api_validate_isbn():
    if not is_logged_in() or require_role("admin", "librarian"):
        return jsonify({"valid": False}), 403
    raw         = request.args.get("isbn", "")
    ok, cleaned = validate_isbn(raw)
    return jsonify({
        "valid":   ok,
        "cleaned": cleaned,
        "type": (
            "ISBN-13" if len(cleaned) == 13 else
            "ISBN-10" if len(cleaned) == 10 else
            "unknown"
        ),
    })

# =====================================================================
# LIBRARY CARDS
# =====================================================================
@librarian_bp.route('/librarian/register/member', methods=['POST'])
def register_member():
    if not is_logged_in() or require_role('librarian'):
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
        return redirect('/librarian/library-cards')
 
    try:
        photo_path = save_card_photo(request.files.get('photo'), 'member')
    except ValueError as e:
        flash(str(e), "danger")
        return redirect('/librarian/library-cards')
 
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
        """, (user_id, firstname, lastname, phone, address, date_issued, date_return,
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
 
    return redirect('/librarian/library-cards')
 
 
@librarian_bp.route('/librarian/register/borrower', methods=['POST'])
def register_borrower():
    if not is_logged_in() or require_role('librarian'):
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
        return redirect('/librarian/library-cards')
    if not date_return:
        flash("Date of return is required.", "danger")
        return redirect('/librarian/library-cards')
 
    try:
        photo_path = save_card_photo(request.files.get('photo'), 'borrower')
    except ValueError as e:
        flash(str(e), "danger")
        return redirect('/librarian/library-cards')
 
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
        """, (firstname, lastname, phone, address, date_issued, date_return,
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
 
    return redirect('/librarian/library-cards')
 
 
@librarian_bp.route('/librarian/api/library-cards')
def api_library_cards():
    if not is_logged_in() or require_role('librarian'):
        return jsonify({'error': 'Unauthorized'}), 401
 
    cat   = request.args.get('type', '')
    q     = request.args.get('q',    '').strip()
    limit = min(int(request.args.get('limit', 100)), 500)
 
    conditions, params = [], []
    if cat in ('member', 'borrower'):
        conditions.append("lc.card_type_category = %s"); params.append(cat)
    if q:
        like = f'%{q}%'
        conditions.append(
            "(lc.firstname LIKE %s OR lc.lastname LIKE %s "
            "OR lcb.book_title LIKE %s OR lcb.book_isbn LIKE %s)"
        )
        params += [like, like, like, like]
 
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
            'registered_by': f"{r[16] or ''} {r[17] or ''}".strip() or '—',
            'user_id': r[18],
            'books': books_by_card.get(r[0], []),
        })
 
    return jsonify({'cards': cards, 'total': len(cards)})
 
 
@librarian_bp.route('/librarian/api/library-cards/<int:card_id>', methods=['GET'])
def api_get_library_card(card_id):
    if not is_logged_in() or require_role('librarian'):
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
        'id': r[0], 'type': r[1], 'firstname': r[2], 'lastname': r[3],
        'phone_number': r[4] or '', 'address': r[5] or '',
        'date_issued': str(r[6]) if r[6] else '',
        'date_return': str(r[7]) if r[7] else '',
        'renewal1_checked': bool(r[8]), 'renewal1_date': str(r[9]) if r[9] else '',
        'renewal2_checked': bool(r[10]), 'renewal2_date': str(r[11]) if r[11] else '',
        'card_type': r[12] or '', 'valid_until': r[13] or '',
        'photo_url': ('/' + r[14].replace('\\', '/')) if r[14] else '',
        'books': [{'book_id': br[0], 'title': br[1], 'author': br[2],
                   'isbn': br[3], 'quantity': br[4] or 1} for br in book_rows],
    })
 
 
@librarian_bp.route('/librarian/api/library-cards/<int:card_id>/update', methods=['POST'])
def api_update_library_card(card_id):
    if not is_logged_in() or require_role('librarian'):
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
        """, (firstname, lastname, phone, address, date_return,
              ren1_chk, ren1_date, ren2_chk, ren2_date, card_type, valid_until, card_id))
 
        for book_id, qty in old_books:
            cur.execute("""
                UPDATE book_inventory
                SET available_copies = LEAST(total_copies, available_copies + %s)
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
 
 
@librarian_bp.route('/librarian/api/library-cards/<int:card_id>/return', methods=['POST'])
def api_return_library_card(card_id):
    if not is_logged_in() or require_role('librarian'):
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
                    SET available_copies = LEAST(total_copies, available_copies + %s)
                    WHERE book_id=%s
                """, (qty_returned, cb[1]))
            else:
                cur.execute("""
                    INSERT INTO book_inventory
                        (book_id, total_copies, available_copies, damaged_copies, lost_copies, status)
                    VALUES (%s,%s,%s,0,0,'Available')
                """, (cb[1], qty_returned, qty_returned))
 
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'return_id': return_id}), 200
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500
 
 
@librarian_bp.route('/librarian/api/library-cards/returns')
def api_list_returns():
    if not is_logged_in() or require_role('librarian'):
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
                'firstname': r[3], 'lastname': r[4],
                'phone_number': r[5] or '',
                'date_issued':  str(r[6]) if r[6] else '',
                'return_date':  str(r[7]) if r[7] else '',
                'processed_by': f"{r[8] or ''} {r[9] or ''}".strip() or '—',
                'books': items_by_return.get(r[0], []),
            }
            for r in rows
        ]
        return jsonify({'returns': returns}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
 
 
@librarian_bp.route('/librarian/api/library-cards/<int:card_id>/returns')
def api_card_returns(card_id):
    if not is_logged_in() or require_role('librarian'):
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
                'id': r[0], 'return_date': str(r[1]) if r[1] else '',
                'created_at': fmt_dt(r[2]),
                'processed_by': f"{r[3] or ''} {r[4] or ''}".strip() or '—',
                'items': items,
            })
        cur.close()
        return jsonify({'returns': returns}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
 
 
@librarian_bp.route('/librarian/api/library-cards/<int:card_id>/delete', methods=['POST'])
def api_delete_library_card(card_id):
    if not is_logged_in() or require_role('librarian'):
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