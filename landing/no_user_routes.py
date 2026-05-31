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
from helpers import (
    safe_decrypt, fmt_dt,
    BOOK_INVENTORY_QUERY,
    build_book_data,
)

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
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(BOOK_INVENTORY_QUERY)
        rows = cursor.fetchall()
        cursor.close()
        return jsonify({'books': build_book_data(rows)})
    except Exception as e:
        return jsonify({'books': [], 'error': str(e)}), 500