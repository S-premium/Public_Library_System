"""
helpers/login_sessions.py
Records staff login sessions and builds the data for the
"Login Activity" block on the admin and librarian settings pages.

  - get_login_activity(user_id)  -> full stats + heatmap + last 7 days + recent
                                    sessions (used by the ADMIN settings page)
  - get_recent_sessions(user_id) -> recent sessions only
                                    (used by the LIBRARIAN settings page)

All times are Philippine time (UTC+8, no DST), stored as naive DATETIMEs.
"""

import secrets
import time as _time
from collections import defaultdict
from datetime import datetime, date, time, timedelta, timezone

from flask import session, current_app

from conn import mysql

_PH            = timezone(timedelta(hours=8))
HEATMAP_WEEKS  = 26
TOUCH_EVERY    = 60      # seconds between last_active_at updates
ACTIVE_WINDOW  = 300     # a session with activity in the last 5 min is "now"
MIN_SESSION    = 60      # every session counts at least 1 minute


def now_local() -> datetime:
    return datetime.now(_PH).replace(tzinfo=None)


# =====================================================================
# RECORDING
# =====================================================================

def record_login(user_id: int) -> None:
    """Call right after a SUCCESSFUL login (after session['user_id'] is set)."""
    if session.get('role') not in ('admin', 'librarian'):
        return
    token = secrets.token_hex(16)
    now   = now_local()
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO login_sessions (user_id, session_token, login_at, last_active_at)
            VALUES (%s, %s, %s, %s)
        """, (user_id, token, now, now))
        mysql.connection.commit()
        cur.close()
        session['ls_token']   = token
        session['ls_touched'] = _time.time()
    except Exception:
        mysql.connection.rollback()
        current_app.logger.exception('[login_sessions] record_login failed')


def record_logout() -> None:
    """Call on logout BEFORE session.clear()."""
    token = session.get('ls_token')
    if not token:
        return
    now = now_local()
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE login_sessions
            SET logout_at = %s, last_active_at = %s
            WHERE session_token = %s AND logout_at IS NULL
        """, (now, now, token))
        mysql.connection.commit()
        cur.close()
    except Exception:
        mysql.connection.rollback()
        current_app.logger.exception('[login_sessions] record_logout failed')


def touch_session() -> None:
    """Call from before_request / the heartbeat. Throttled to once per minute."""
    token = session.get('ls_token')
    if not token:
        return
    ts = _time.time()
    if ts - session.get('ls_touched', 0) < TOUCH_EVERY:
        return
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE login_sessions SET last_active_at = %s
            WHERE session_token = %s AND logout_at IS NULL
        """, (now_local(), token))
        mysql.connection.commit()
        cur.close()
        session['ls_touched'] = ts
    except Exception:
        mysql.connection.rollback()


# =====================================================================
# HELPERS
# =====================================================================

def _level(sec: float) -> int:
    if sec <= 0:      return 0
    if sec <= 3600:   return 1      # 1h & below
    if sec <= 7200:   return 2      # 2h
    if sec < 18000:   return 3      # 3h
    return 4                        # 5h & above


def _fmt(sec: float) -> str:
    m = int(sec // 60)
    return f"{m // 60}h {m % 60:02d}m"


def _t(dt: datetime) -> str:
    return dt.strftime('%I:%M %p').lstrip('0')


def _merge(intervals):
    """Merge overlapping sessions so two tabs/devices don't double count."""
    out = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def _end_of(login_at, last_active, logout_at):
    end = logout_at or last_active or login_at
    return max(end, login_at + timedelta(seconds=MIN_SESSION))


# =====================================================================
# LIBRARIAN SETTINGS: recent sessions only
# =====================================================================

def get_recent_sessions(user_id: int, limit: int = 5) -> list:
    now   = now_local()
    today = now.date()

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT login_at, last_active_at, logout_at
        FROM login_sessions
        WHERE user_id = %s
        ORDER BY login_at DESC
        LIMIT %s
    """, (user_id, limit))
    rows = cur.fetchall()
    cur.close()

    sessions = []
    for login_at, last_active, logout_at in rows:
        end  = _end_of(login_at, last_active, logout_at)
        live = logout_at is None and (now - (last_active or login_at)).total_seconds() <= ACTIVE_WINDOW
        d    = login_at.date()
        dlabel = ('Today' if d == today
                  else 'Yesterday' if d == today - timedelta(days=1)
                  else d.strftime('%b %d, %Y'))
        sessions.append({
            'live':     live,
            'label':    f"{dlabel} · {_t(login_at)} → {'now' if live else _t(end)}",
            'duration': 'Active now' if live else _fmt((end - login_at).total_seconds()),
        })
    return sessions


# =====================================================================
# ADMIN SETTINGS: full login activity (UNCHANGED from the original)
# =====================================================================

def get_login_activity(user_id: int) -> dict:
    now    = now_local()
    today  = now.date()
    sunday = today - timedelta(days=(today.weekday() + 1) % 7)       # week starts Sunday
    start  = sunday - timedelta(weeks=HEATMAP_WEEKS - 1)
    start_dt = datetime.combine(start, time.min)

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT login_at, last_active_at, logout_at
        FROM login_sessions
        WHERE user_id = %s AND COALESCE(logout_at, last_active_at) >= %s
        ORDER BY login_at
    """, (user_id, start_dt))
    rows = cur.fetchall()
    cur.execute("""
        SELECT login_at, last_active_at, logout_at
        FROM login_sessions WHERE user_id = %s
        ORDER BY login_at DESC LIMIT 5
    """, (user_id,))
    recent_rows = cur.fetchall()
    cur.close()

    # ── seconds per day (split across midnight) ──────────────────────
    per_day = defaultdict(float)
    for s, e in _merge([(r[0], _end_of(*r)) for r in rows]):
        c = max(s, start_dt)
        while c < e:
            nxt = datetime.combine(c.date() + timedelta(days=1), time.min)
            seg = min(e, nxt)
            per_day[c.date()] += (seg - c).total_seconds()
            c = seg

    total = sum(per_day.values())
    days  = sorted(per_day)

    # ── streaks ──────────────────────────────────────────────────────
    best = run = 0
    prev = None
    for d in days:
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        best = max(best, run)
        prev = d

    cursor_day = today if today in per_day else today - timedelta(days=1)
    streak = 0
    while cursor_day in per_day:
        streak += 1
        cursor_day -= timedelta(days=1)

    longest_day = max(per_day, key=per_day.get) if per_day else None

    # ── heatmap ──────────────────────────────────────────────────────
    columns, months = [], []
    for w in range(HEATMAP_WEEKS):
        col, label = [], ''
        for i in range(7):
            d = start + timedelta(weeks=w, days=i)
            if d.day == 1:
                label = d.strftime('%b')
            if d > today:
                col.append({'future': True})
                continue
            sec = per_day.get(d, 0)
            col.append({
                'future': False,
                'level':  _level(sec),
                'title':  f"{d.strftime('%a, %b %d, %Y')} — " + (_fmt(sec) if sec else 'No login'),
            })
        if w == 0 and not label:
            label = start.strftime('%b')
        columns.append(col)
        months.append(label)

    # ── last 7 days ──────────────────────────────────────────────────
    week = []
    for i in range(6, -1, -1):
        d   = today - timedelta(days=i)
        sec = per_day.get(d, 0)
        week.append({
            'day':    d.strftime('%a'),
            'value':  _fmt(sec) if sec else '—',
            'level':  _level(sec),
            'height': min(100, round(sec / (8 * 3600) * 100)),
            'title':  f"{d.strftime('%a, %b %d')} — " + (_fmt(sec) if sec else 'No login'),
        })

    # ── recent sessions ──────────────────────────────────────────────
    sessions = []
    for login_at, last_active, logout_at in recent_rows:
        end    = _end_of(login_at, last_active, logout_at)
        live   = logout_at is None and (now - (last_active or login_at)).total_seconds() <= ACTIVE_WINDOW
        d      = login_at.date()
        dlabel = 'Today' if d == today else 'Yesterday' if d == today - timedelta(days=1) else d.strftime('%b %d')
        dur    = (end - login_at).total_seconds()
        sessions.append({
            'level':    _level(dur),
            'label':    f"{dlabel} · {_t(login_at)} → {'now' if live else _t(end)}",
            'duration': _fmt(dur),
        })

    return {
        'total':         _fmt(total),
        'avg':           _fmt(total / len(days)) if days else '0h 00m',
        'days':          len(days),
        'streak':        streak,
        'best_streak':   best,
        'longest':       _fmt(per_day[longest_day]) if longest_day else '0h 00m',
        'longest_label': longest_day.strftime('%b %d') if longest_day else '—',
        'months':        months,
        'columns':       columns,
        'week':          week,
        'sessions':      sessions,
    }