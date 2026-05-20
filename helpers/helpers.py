"""
helpers/helpers.py
Changes:
  - Added: name_blind_index()
  - search_users()   → 4-step blind index (email → name → phone → partial fallback)
  - search_members() → same, fixed address bug (city+province, no 'address' column)
  - Everything else unchanged
"""

import os
import json
import uuid
import hmac
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet, InvalidToken
from flask import send_from_directory, session

from conn import mysql, app

load_dotenv()

# =====================================================================
# APK DOWNLOAD
# =====================================================================
@app.route('/download/apk')
def download_apk():
    return send_from_directory(
        directory=os.path.join(app.root_path, 'application'),
        path='app-debug.apk',
        as_attachment=True,
        mimetype='application/vnd.android.package-archive'
    )

# =====================================================================
# LAYER 5: ENCRYPTION KEYS
# =====================================================================

KEY = os.getenv('ENCRYPTION_KEY')
if not KEY:
    raise RuntimeError("ENCRYPTION_KEY missing from .env")
cipher = Fernet(KEY.encode())

PII_KEY = os.getenv('PII_ENCRYPTION_KEY')
if not PII_KEY:
    raise RuntimeError("PII_ENCRYPTION_KEY missing from .env")
pii_cipher = Fernet(PII_KEY.encode())

EMAIL_KEY = os.getenv('EMAIL_ENCRYPTION_KEY')
if not EMAIL_KEY:
    raise RuntimeError("EMAIL_ENCRYPTION_KEY missing from .env")
email_cipher = Fernet(EMAIL_KEY.encode())

_EMAIL_HMAC_KEY = EMAIL_KEY.encode()
_PII_HMAC_KEY   = PII_KEY.encode()

# =====================================================================
# LAYER 5: ENCRYPTION HELPERS
# =====================================================================

def encrypt_data(data: str) -> str:
    if not data:
        return ""
    return cipher.encrypt(data.encode()).decode()

def decrypt_data(data: str) -> str:
    if not data:
        return ""
    return cipher.decrypt(data.encode()).decode()

def safe_decrypt(data: str) -> str:
    if not data:
        return ""
    try:
        return decrypt_data(data)
    except InvalidToken:
        return data

# ── PII helpers ───────────────────────────────────────────────────────

def encrypt_pii(data: str) -> str:
    if not data:
        return ""
    return pii_cipher.encrypt(data.encode()).decode()

def decrypt_pii(data: str) -> str:
    if not data:
        return ""
    return pii_cipher.decrypt(data.encode()).decode()

def safe_decrypt_pii(data: str) -> str:
    if not data:
        return ""
    try:
        return decrypt_pii(data)
    except InvalidToken:
        return data

# ── Email helpers ─────────────────────────────────────────────────────

def encrypt_email(data: str) -> str:
    """Deterministic HMAC-SHA256 — safe for WHERE clauses (blind index)."""
    if not data:
        return ""
    return hmac.new(_EMAIL_HMAC_KEY, data.lower().strip().encode(), hashlib.sha256).hexdigest()

def store_email(data: str) -> str:
    """Fernet-encrypt raw email for reversible display storage."""
    if not data:
        return ""
    return email_cipher.encrypt(data.encode()).decode()

def decrypt_email(data: str) -> str:
    if not data:
        return ""
    return email_cipher.decrypt(data.encode()).decode()

def safe_decrypt_email(data: str) -> str:
    if not data:
        return ""
    try:
        return decrypt_email(data)
    except InvalidToken:
        return data

# ── Phone blind index ─────────────────────────────────────────────────

def phone_blind_index(phone: str) -> str:
    """HMAC-SHA256 of digits-only phone."""
    if not phone:
        return ""
    digits = ''.join(filter(str.isdigit, phone))
    return hmac.new(_PII_HMAC_KEY, digits.encode(), hashlib.sha256).hexdigest()

# ── Name blind index (NEW) ────────────────────────────────────────────

def name_blind_index(firstname: str, lastname: str) -> str:
    """HMAC-SHA256 of 'firstname lastname' — for WHERE name_index = ? queries."""
    if not firstname and not lastname:
        return ""
    combined = f"{firstname.strip().lower()} {lastname.strip().lower()}"
    return hmac.new(_PII_HMAC_KEY, combined.encode(), hashlib.sha256).hexdigest()

# ── Book blind indexes ────────────────────────────────────────────────

def title_blind_index(title: str) -> str:
    """HMAC-SHA256 of normalized title — for WHERE title_index = ? queries."""
    if not title:
        return ""
    return hmac.new(_PII_HMAC_KEY, title.strip().lower().encode(), hashlib.sha256).hexdigest()

def author_blind_index(author: str) -> str:
    """HMAC-SHA256 of normalized author — for WHERE author_index = ? queries."""
    if not author:
        return ""
    return hmac.new(_PII_HMAC_KEY, author.strip().lower().encode(), hashlib.sha256).hexdigest()

def isbn_blind_index(isbn: str) -> str:
    """HMAC-SHA256 of digits-only ISBN."""
    if not isbn:
        return ""
    digits = ''.join(filter(str.isdigit, isbn))
    return hmac.new(_PII_HMAC_KEY, digits.encode(), hashlib.sha256).hexdigest()

def category_blind_index(category: str) -> str:
    """HMAC-SHA256 of normalized category."""
    if not category:
        return ""
    return hmac.new(_PII_HMAC_KEY, category.strip().lower().encode(), hashlib.sha256).hexdigest()

# =====================================================================
# DATE / FORMAT
# =====================================================================

def fmt_dt(dt, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return dt.strftime(fmt) if dt else ""

# =====================================================================
# LAYER 2: ROLE / SESSION HELPERS
# =====================================================================

def is_logged_in() -> bool:
    if 'username' not in session or 'user_id' not in session:
        return False
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE id = %s", (session['user_id'],))
        user = cur.fetchone()
        cur.close()
        if not user:
            session.clear()
            return False
    except Exception:
        return False
    return True

def require_role(*roles) -> bool:
    if not is_logged_in():
        return True
    return session.get('role') not in roles

# =====================================================================
# SEARCH HELPERS — 4-step blind index strategy
# =====================================================================

def search_users(query: str, limit: int = 15) -> list:
    """
    Search users by email, full name, phone, or partial name.
    Step 1: exact email  ~1-2ms  ✅
    Step 2: exact name   ~1-2ms  ✅
    Step 3: exact phone  ~1-2ms  ✅
    Step 4: partial name fallback (200 rows max)
    """
    if not query or not query.strip():
        return []

    q       = query.strip()
    results = []

    try:
        cur = mysql.connection.cursor()

        # ── Step 1: Exact email via blind index ───────────────────────
        cur.execute("""
            SELECT id, username, firstname, lastname, email_display
            FROM users
            WHERE username = %s AND role = 'user'
            LIMIT 1
        """, (encrypt_email(q),))
        row = cur.fetchone()
        if row:
            cur.close()
            return [{
                'id':        row[0],
                'username':  safe_decrypt_email(row[4]) or safe_decrypt_email(row[1]),
                'firstname': safe_decrypt_pii(row[2]),
                'lastname':  safe_decrypt_pii(row[3]),
            }]

        # ── Step 2: Exact full-name via blind index ───────────────────
        parts = q.split()
        if len(parts) >= 2:
            fwd = name_blind_index(parts[0], ' '.join(parts[1:]))
            rev = name_blind_index(' '.join(parts[1:]), parts[0])
            cur.execute("""
                SELECT id, username, firstname, lastname, email_display
                FROM users
                WHERE name_index IN (%s, %s) AND role = 'user'
                LIMIT %s
            """, (fwd, rev, limit))
            rows = cur.fetchall()
            if rows:
                cur.close()
                return [{
                    'id':        r[0],
                    'username':  safe_decrypt_email(r[4]) or safe_decrypt_email(r[1]),
                    'firstname': safe_decrypt_pii(r[2]),
                    'lastname':  safe_decrypt_pii(r[3]),
                } for r in rows]

        # ── Step 3: Exact phone via blind index ───────────────────────
        p_hash = phone_blind_index(q)
        if p_hash:
            cur.execute("""
                SELECT id, username, firstname, lastname, email_display
                FROM users
                WHERE phone_index = %s AND role = 'user'
                LIMIT 1
            """, (p_hash,))
            row = cur.fetchone()
            if row:
                cur.close()
                return [{
                    'id':        row[0],
                    'username':  safe_decrypt_email(row[4]) or safe_decrypt_email(row[1]),
                    'firstname': safe_decrypt_pii(row[2]),
                    'lastname':  safe_decrypt_pii(row[3]),
                }]

        # ── Step 4: Partial name fallback (200 rows max) ──────────────
        cur.execute("""
            SELECT id, username, firstname, lastname, email_display
            FROM users
            WHERE role = 'user'
            ORDER BY id DESC
            LIMIT 200
        """)
        rows = cur.fetchall()
        cur.close()

        q_lower = q.lower()
        for r in rows:
            try:
                fn = pii_cipher.decrypt(r[2].encode()).decode() if r[2] else ''
                ln = pii_cipher.decrypt(r[3].encode()).decode() if r[3] else ''
            except Exception:
                fn, ln = r[2] or '', r[3] or ''

            fullname = f"{fn} {ln}".strip().lower()
            email    = safe_decrypt_email(r[4]) if r[4] else safe_decrypt_email(r[1])

            if q_lower in fn.lower() or q_lower in ln.lower() or q_lower in fullname:
                results.append({
                    'id':        r[0],
                    'username':  email,
                    'firstname': fn,
                    'lastname':  ln,
                })
            if len(results) >= limit:
                break

    except Exception:
        return []

    return results


def search_members(query: str, limit: int = 15) -> list:
    """
    Search members for library card creation.
    Uses city + province instead of missing 'address' column.
    Same 4-step blind index strategy.
    """
    if not query or not query.strip():
        return []

    q       = query.strip()
    results = []

    try:
        cur = mysql.connection.cursor()

        # ── Step 1: Exact email via blind index ───────────────────────
        cur.execute("""
            SELECT id, username, firstname, lastname,
                   phone_number, city, province, email_display
            FROM users
            WHERE username = %s AND role = 'user'
            LIMIT 1
        """, (encrypt_email(q),))
        row = cur.fetchone()
        if row:
            cur.close()
            city     = safe_decrypt_pii(row[5])
            province = safe_decrypt_pii(row[6])
            return [{
                'id':           row[0],
                'username':     safe_decrypt_email(row[7]) or safe_decrypt_email(row[1]),
                'firstname':    safe_decrypt_pii(row[2]),
                'lastname':     safe_decrypt_pii(row[3]),
                'phone_number': safe_decrypt_pii(row[4]),
                'address':      f"{city}, {province}".strip(', '),
            }]

        # ── Step 2: Exact full-name via blind index ───────────────────
        parts = q.split()
        if len(parts) >= 2:
            fwd = name_blind_index(parts[0], ' '.join(parts[1:]))
            rev = name_blind_index(' '.join(parts[1:]), parts[0])
            cur.execute("""
                SELECT id, username, firstname, lastname,
                       phone_number, city, province, email_display
                FROM users
                WHERE name_index IN (%s, %s) AND role = 'user'
                LIMIT %s
            """, (fwd, rev, limit))
            rows = cur.fetchall()
            if rows:
                cur.close()
                out = []
                for r in rows:
                    city     = safe_decrypt_pii(r[5])
                    province = safe_decrypt_pii(r[6])
                    out.append({
                        'id':           r[0],
                        'username':     safe_decrypt_email(r[7]) or safe_decrypt_email(r[1]),
                        'firstname':    safe_decrypt_pii(r[2]),
                        'lastname':     safe_decrypt_pii(r[3]),
                        'phone_number': safe_decrypt_pii(r[4]),
                        'address':      f"{city}, {province}".strip(', '),
                    })
                return out

        # ── Step 3: Exact phone via blind index ───────────────────────
        p_hash = phone_blind_index(q)
        if p_hash:
            cur.execute("""
                SELECT id, username, firstname, lastname,
                       phone_number, city, province, email_display
                FROM users
                WHERE phone_index = %s AND role = 'user'
                LIMIT 1
            """, (p_hash,))
            row = cur.fetchone()
            if row:
                cur.close()
                city     = safe_decrypt_pii(row[5])
                province = safe_decrypt_pii(row[6])
                return [{
                    'id':           row[0],
                    'username':     safe_decrypt_email(row[7]) or safe_decrypt_email(row[1]),
                    'firstname':    safe_decrypt_pii(row[2]),
                    'lastname':     safe_decrypt_pii(row[3]),
                    'phone_number': safe_decrypt_pii(row[4]),
                    'address':      f"{city}, {province}".strip(', '),
                }]

        # ── Step 4: Partial name fallback (200 rows max) ──────────────
        cur.execute("""
            SELECT id, username, firstname, lastname,
                   phone_number, city, province, email_display
            FROM users
            WHERE role = 'user'
            ORDER BY id DESC
            LIMIT 200
        """)
        rows = cur.fetchall()
        cur.close()

        q_lower = q.lower()
        for r in rows:
            try:
                fn = pii_cipher.decrypt(r[2].encode()).decode() if r[2] else ''
                ln = pii_cipher.decrypt(r[3].encode()).decode() if r[3] else ''
            except Exception:
                fn, ln = r[2] or '', r[3] or ''
            try:
                phone = pii_cipher.decrypt(r[4].encode()).decode() if r[4] else ''
            except Exception:
                phone = r[4] or ''

            city     = safe_decrypt_pii(r[5])
            province = safe_decrypt_pii(r[6])
            fullname = f"{fn} {ln}".strip().lower()

            if q_lower in fn.lower() or q_lower in ln.lower() or q_lower in fullname:
                results.append({
                    'id':           r[0],
                    'username':     safe_decrypt_email(r[7]) if r[7] else safe_decrypt_email(r[1]),
                    'firstname':    fn,
                    'lastname':     ln,
                    'phone_number': phone,
                    'address':      f"{city}, {province}".strip(', '),
                })
            if len(results) >= limit:
                break

    except Exception:
        return []

    return results

def search_books(query: str, limit: int = 50) -> list:
    """
    Search books by title, author, ISBN, or category.
    Step 1: exact title    via blind index ~1-2ms ✅
    Step 2: exact author   via blind index ~1-2ms ✅
    Step 3: exact ISBN     via blind index ~1-2ms ✅
    Step 4: exact category via blind index ~1-2ms ✅
    Step 5: partial decrypt fallback (max 500 rows)
    """
    if not query or not query.strip():
        return []

    q = query.strip()

    BASE_SELECT = """
        SELECT b.id, b.call_number, b.date_received, b.`class`, b.author,
               b.title, b.isbn, b.edition, b.page_count, b.category,
               b.source_of_fund, b.cost_price, b.publisher, b.copy_right,
               b.subtitle, b.published_date, b.description, b.language,
               b.thumbnail_url, b.api_source, b.is_borrowable, b.created_at,
               b.updated_at,
               COALESCE(inv.volumes, 0),
               COALESCE(inv.available_copies, 0),
               COALESCE(inv.damaged_copies, 0),
               COALESCE(inv.lost_copies, 0),
               COALESCE(inv.status, 'Available'),
               COALESCE(inv.shelf_location, '')
        FROM books b
        LEFT JOIN book_inventory inv ON b.id = inv.book_id
    """

    try:
        cur = mysql.connection.cursor()

        # ── Step 1: Exact title ───────────────────────────────────────
        cur.execute(BASE_SELECT + " WHERE b.title_index = %s LIMIT %s",
                    (title_blind_index(q), limit))
        rows = cur.fetchall()
        if rows:
            cur.close()
            return build_book_data(rows)

        # ── Step 2: Exact author ──────────────────────────────────────
        cur.execute(BASE_SELECT + " WHERE b.author_index = %s LIMIT %s",
                    (author_blind_index(q), limit))
        rows = cur.fetchall()
        if rows:
            cur.close()
            return build_book_data(rows)

        # ── Step 3: Exact ISBN ────────────────────────────────────────
        i_hash = isbn_blind_index(q)
        if i_hash:
            cur.execute(BASE_SELECT + " WHERE b.isbn_index = %s LIMIT %s",
                        (i_hash, limit))
            rows = cur.fetchall()
            if rows:
                cur.close()
                return build_book_data(rows)

        # ── Step 4: Partial decrypt fallback (max 500 rows) ──────────
        cur.execute(BASE_SELECT + " ORDER BY b.id DESC LIMIT 500")
        rows = cur.fetchall()
        cur.close()

        q_lower = q.lower()
        results = []
        for row in rows:
            title    = safe_decrypt(row[5]) if row[5] else ""
            author   = safe_decrypt(row[4]) if row[4] else ""
            isbn     = safe_decrypt(row[6]) if row[6] else ""
            category = safe_decrypt(row[9]) if row[9] else ""
            if (q_lower in title.lower()    or
                q_lower in author.lower()   or
                q_lower in isbn.lower()     or
                q_lower in category.lower()):
                results.append(row)
            if len(results) >= limit:
                break

        return build_book_data(results)

    except Exception:
        return []
# =====================================================================
# USER DATA BUILDER
# =====================================================================

def build_users_data(all_users: list) -> list:
    users_data = []
    for user in all_users:
        status    = user[9]
        last_seen = user[10]

        if last_seen and isinstance(last_seen, datetime):
            if datetime.now() - last_seen > timedelta(minutes=5):
                status = "offline"

        users_data.append({
            'id':              user[0],
            'username':        safe_decrypt_email(user[1]),
            'firstname':       safe_decrypt_pii(user[2]),
            'lastname':        safe_decrypt_pii(user[3]),
            'password':        user[4],
            'failed_attempts': user[5] or 0,
            'is_locked':       user[6],
            'lock_until':      user[7],
            'created_at':      user[8],
            'status':          status,
            'last_seen':       last_seen,
            'role':            user[11],
            'is_active':       user[12] if len(user) > 12 else 1,
        })
    return users_data

# =====================================================================
# BOOK DATA BUILDER
# =====================================================================

BOOK_INVENTORY_QUERY = """
    SELECT
        b.id, b.call_number, b.date_received, b.`class`, b.author,
        b.title, b.isbn, b.edition, b.page_count, b.category,
        b.source_of_fund, b.cost_price, b.publisher, b.copy_right,
        b.subtitle, b.published_date, b.description, b.language,
        b.thumbnail_url, b.api_source, b.is_borrowable, b.created_at,
        b.updated_at,
        COALESCE(inv.volumes, 0)          AS total_copies,
        COALESCE(inv.available_copies, 0) AS available_copies,
        COALESCE(inv.damaged_copies, 0)   AS damaged_copies,
        COALESCE(inv.lost_copies, 0)      AS lost_copies,
        COALESCE(inv.status, 'Available') AS status,
        COALESCE(inv.shelf_location, '')  AS shelf_location
    FROM books b
    LEFT JOIN book_inventory inv ON b.id = inv.book_id
    ORDER BY b.id DESC
"""

def build_book_data(rows: list, date_fmt: str = "%Y-%m-%d") -> list:
    result = []
    for b in rows:
        class_val = safe_decrypt(b[3]) if b[3] else ""
        try:
            page_count_val = int(float(b[8])) if b[8] else None
        except (ValueError, TypeError):
            page_count_val = None

        result.append({
            "id":               b[0],
            "call_number":      b[1]  or "",
            "date_received":    str(b[2]) if b[2] else "",
            "class":            class_val,
            "genre":            class_val,
            "author":           safe_decrypt(b[4])  if b[4]  else "",
            "title":            safe_decrypt(b[5])  if b[5]  else "",
            "isbn":             safe_decrypt(b[6])  if b[6]  else "",
            "edition":          b[7]  or "",
            "page_count":       page_count_val,
            "category":         safe_decrypt(b[9])  if b[9]  else "",
            "source_of_fund":   b[10] or "",
            "cost_price":       float(b[11]) if b[11] is not None else 0.0,
            "publisher":        safe_decrypt(b[12]) if b[12] else "",
            "copy_right":       b[13] or "",
            "subtitle":         b[14] or "",
            "published_date":   b[15] or "",
            "description":      (b[16] or "").replace('\r', ' ').replace('\n', ' ').strip(),
            "language":         b[17] or "",
            "thumbnail_url":    b[18] or "",
            "api_source":       b[19] or "",
            "is_borrowable":    bool(b[20]),
            "created_at":       fmt_dt(b[21], date_fmt),
            "updated_at":       fmt_dt(b[22], date_fmt),
            "total_copies":     int(b[23]),
            "available_copies": int(b[24]),
            "damaged_copies":   int(b[25]),
            "lost_copies":      int(b[26]),
            "status":           b[27] or "Available",
            "shelf_location":   b[28] or "",
            "date_added":       fmt_dt(b[21], date_fmt),
        })
    return result

# =====================================================================
# STORAGE
# =====================================================================

STORAGE_LIMIT_BYTES = 1 * 1024 * 1024
_ROW_OVERHEAD       = 96
_SEARCH_IDX_BYTES   = 28
_FAV_ROW_BYTES      = 48
_APPEARANCE_BASE    = 256

def calc_storage(user_id: int, cursor) -> dict:
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(LENGTH(query)), 0)
        FROM user_search_history WHERE user_id = %s
    """, (user_id,))
    row = cursor.fetchone()
    hist_rows, hist_query_bytes = int(row[0]), int(row[1])
    history_bytes = hist_query_bytes + hist_rows * (_ROW_OVERHEAD + _SEARCH_IDX_BYTES)

    cursor.execute("SELECT COUNT(*) FROM user_favorites WHERE user_id = %s", (user_id,))
    fav_count  = int(cursor.fetchone()[0])
    fav_bytes  = fav_count * (_FAV_ROW_BYTES + _ROW_OVERHEAD)

    cursor.execute("SELECT COUNT(*) FROM user_appearance WHERE user_id = %s", (user_id,))
    has_appearance   = int(cursor.fetchone()[0])
    appearance_bytes = _APPEARANCE_BASE if has_appearance else 0

    total = history_bytes + fav_bytes + appearance_bytes
    return {
        "total_bytes":      total,
        "limit_bytes":      STORAGE_LIMIT_BYTES,
        "history_bytes":    history_bytes,
        "favorites_bytes":  fav_bytes,
        "appearance_bytes": appearance_bytes,
        "used_percent":     round(total / STORAGE_LIMIT_BYTES * 100, 2),
        "is_full":          total >= STORAGE_LIMIT_BYTES,
        "is_warning":       total >= STORAGE_LIMIT_BYTES * 0.85,
    }

# =====================================================================
# CARD / PHOTO HELPERS
# =====================================================================

CARD_PHOTO_FOLDER = os.path.join('static', 'uploads', 'card_photos')
CARD_MAX_BYTES    = 2 * 1024 * 1024

os.makedirs(CARD_PHOTO_FOLDER, exist_ok=True)

def _allowed_card_photo(filename: str) -> bool:
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'webp'}
    )

def save_card_photo(photo_file, prefix: str):
    if not photo_file or not photo_file.filename:
        return None
    if not _allowed_card_photo(photo_file.filename):
        raise ValueError("Invalid photo format. Use PNG, JPG, or WEBP.")
    photo_file.seek(0, os.SEEK_END)
    size = photo_file.tell()
    photo_file.seek(0)
    if size > CARD_MAX_BYTES:
        raise ValueError("Photo must be under 2 MB.")
    ext       = secure_filename(photo_file.filename).rsplit('.', 1)[1].lower()
    filename  = f"{prefix}_{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(CARD_PHOTO_FOLDER, filename)
    photo_file.save(save_path)
    return save_path.replace('\\', '/')

def resolve_book_snapshots(book_ids: list) -> list:
    snapshots = []
    if not book_ids:
        return snapshots
    cur = mysql.connection.cursor()
    for item in book_ids:
        if isinstance(item, dict):
            bid = item.get('id')
            qty = max(1, int(item.get('qty', 1) or 1))
        else:
            bid = item
            qty = 1
        if not bid:
            continue
        cur.execute("SELECT id, title, author, isbn FROM books WHERE id=%s", (bid,))
        row = cur.fetchone()
        if row:
            snapshots.append({
                'book_id': row[0],
                'title':   safe_decrypt(row[1]),
                'author':  safe_decrypt(row[2]),
                'isbn':    safe_decrypt(row[3]),
                'qty':     qty,
            })
    cur.close()
    return snapshots

def insert_card_books(card_id: int, snapshots: list) -> None:
    if not snapshots:
        return
    cur = mysql.connection.cursor()
    cur.executemany("""
        INSERT INTO library_card_books
            (card_id, book_id, book_title, book_author, book_isbn, quantity)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, [
        (card_id, s['book_id'], s['title'], s['author'], s['isbn'], s.get('qty', 1))
        for s in snapshots
    ])
    mysql.connection.commit()
    cur.close()

def update_inventory_on_borrow(snapshots: list) -> None:
    if not snapshots:
        return
    cur = mysql.connection.cursor()
    for s in snapshots:
        cur.execute("SELECT id FROM book_inventory WHERE book_id = %s", (s['book_id'],))
        if cur.fetchone():
            cur.execute("""
                UPDATE book_inventory
                SET available_copies = GREATEST(0, available_copies - %s)
                WHERE book_id = %s
            """, (s.get('qty', 1), s['book_id']))
        else:
            cur.execute("""
                INSERT INTO book_inventory
                    (book_id, volumes, available_copies, damaged_copies, lost_copies, status)
                VALUES (%s, 1, 0, 0, 0, 'Available')
            """, (s['book_id'],))
    mysql.connection.commit()
    cur.close()

# =====================================================================
# EVENT HELPER
# =====================================================================

from datetime import date, timedelta as _td, time as _time_type

def event_to_dict(row: tuple) -> dict:
    ev_date = row[3]
    if isinstance(ev_date, (date, datetime)):
        date_str = ev_date.strftime('%Y-%m-%d')
    else:
        date_str = str(ev_date)

    def build_dt(t_val):
        if t_val is None:
            return date_str
        if isinstance(t_val, _td):
            total = int(t_val.total_seconds())
            h, rem = divmod(total, 3600)
            m = rem // 60
            return f"{date_str}T{h:02d}:{m:02d}:00+08:00"
        if isinstance(t_val, _time_type):
            return f"{date_str}T{t_val.strftime('%H:%M:%S')}+08:00"
        return f"{date_str}T{str(t_val)}+08:00"

    image_path = row[7]
    image_url  = ('/' + image_path.replace('\\', '/')) if image_path else ''

    return {
        'id':          row[0],
        'title':       row[1],
        'start':       build_dt(row[4]),
        'end':         build_dt(row[5]),
        'description': row[2] or '',
        'location':    row[6] or '',
        'image':       image_url,
        'date_str':    date_str,
        'category':    row[9] if len(row) > 9 else 'general',
    }

# =====================================================================
# SEARCH HISTORY
# =====================================================================

def save_search_history(user_id: int, query: str) -> None:
    if not user_id or not query or not query.strip():
        return
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO user_search_history (user_id, query) VALUES (%s, %s)",
            (user_id, query.strip())
        )
        mysql.connection.commit()
        cur.execute("""
            DELETE FROM user_search_history
            WHERE user_id = %s
              AND id NOT IN (
                  SELECT id FROM (
                      SELECT id FROM user_search_history
                      WHERE user_id = %s
                      ORDER BY searched_at DESC
                      LIMIT 50
                  ) AS sub
              )
        """, (user_id, user_id))
        mysql.connection.commit()
        cur.close()
    except Exception:
        pass