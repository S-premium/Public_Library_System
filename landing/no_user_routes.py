"""
landing/no_user_routes.py
--------------------------
Blueprint: landing_bp

Public-facing routes that require NO login:
  GET /            — landing page
  GET /no_user_about
  GET /browse      — public book browser
  GET /api/public/books
"""

from flask import Blueprint, render_template, jsonify

from conn import mysql
from helpers import safe_decrypt, fmt_dt

landing_bp = Blueprint("landing_bp", __name__)


@landing_bp.route('/')
def landing_page():
    return render_template("homepage.html")


@landing_bp.route('/no_user_about')
def no_user_about():
    return render_template('aboutus.html')


@landing_bp.route('/browse')
def browse():
    return render_template("books.html")


@landing_bp.route('/api/public/books')
def api_public_books():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT id, title, author, isbn, category, genre, publisher, created_at, is_borrowable
        FROM books
        ORDER BY created_at DESC
    """)
    books = cursor.fetchall()
    cursor.close()

    books_list = [
        {
            "id":            b[0],
            "title":         safe_decrypt(b[1]),
            "author":        safe_decrypt(b[2]),
            "isbn":          safe_decrypt(b[3]),
            "category":      safe_decrypt(b[4]) if b[4] else "",
            "genre":         safe_decrypt(b[5]) if b[5] else "",
            "publisher":     safe_decrypt(b[6]) if b[6] else "",
            "date_added":    fmt_dt(b[7]),
            "is_borrowable": bool(b[8]),
        }
        for b in books
    ]

    return jsonify({'books': books_list})