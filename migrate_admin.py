"""
migrate_admin.py (recovery edition)
-------------------------------------
Usernames are already HMAC hashes but email_display is empty.
This script lets you manually provide the raw emails to recover.

Run from the project root:
    python migrate_admin.py
"""

import os
import hmac
import hashlib
from dotenv import load_dotenv
from cryptography.fernet import Fernet, InvalidToken
import MySQLdb

load_dotenv()

EMAIL_KEY       = os.getenv('EMAIL_ENCRYPTION_KEY')
PII_KEY         = os.getenv('PII_ENCRYPTION_KEY')
email_cipher    = Fernet(EMAIL_KEY.encode())
pii_cipher      = Fernet(PII_KEY.encode())
_EMAIL_HMAC_KEY = EMAIL_KEY.encode()

def hash_email(val: str) -> str:
    return hmac.new(_EMAIL_HMAC_KEY, val.lower().strip().encode(), hashlib.sha256).hexdigest()

def store_email(val: str) -> str:
    return email_cipher.encrypt(val.encode()).decode()

def encrypt_pii(val: str) -> str:
    if not val:
        return val
    return pii_cipher.encrypt(val.encode()).decode()

def already_pii_encrypted(val: str) -> bool:
    if not val:
        return False
    try:
        pii_cipher.decrypt(val.encode())
        return True
    except Exception:
        return False

db = MySQLdb.connect(
    host=os.getenv('MYSQL_HOST', '127.0.0.1'),
    port=int(os.getenv('MYSQL_PORT', 3306)),
    user=os.getenv('MYSQL_USER', 'root'),
    passwd=os.getenv('MYSQL_PASSWORD', ''),
    db=os.getenv('MYSQL_DB', 's-premium'),
)
cur = db.cursor()

cur.execute("""
    SELECT id, username, email_display, firstname, lastname, role
    FROM users
""")
rows = cur.fetchall()

print("\n=== EMAIL DISPLAY RECOVERY ===")
print("Users with empty email_display need their raw email entered manually.\n")

for user_id, username, email_display, firstname, lastname, role in rows:
    # Decrypt PII for display if possible
    try:
        display_first = pii_cipher.decrypt(firstname.encode()).decode() if firstname else '?'
    except Exception:
        display_first = firstname or '?'
    try:
        display_last = pii_cipher.decrypt(lastname.encode()).decode() if lastname else '?'
    except Exception:
        display_last = lastname or '?'

    if email_display:
        print(f"  [ID={user_id}] {display_first} {display_last} ({role}) — email_display already set, skipping.")
        continue

    print(f"  [ID={user_id}] {display_first} {display_last} ({role})")
    raw_email = input(f"  Enter raw email for this user: ").strip()

    if not raw_email:
        print(f"  ⚠ Skipped (no email entered).\n")
        continue

    # Verify the entered email matches the stored HMAC
    computed_hash = hash_email(raw_email)
    if computed_hash != username:
        print(f"  ✗ Email does NOT match the stored hash! Double-check and try again.")
        print(f"    Entered : {raw_email}")
        print(f"    Expected hash : {username}")
        print(f"    Got hash      : {computed_hash}\n")
        continue

    # Encrypt PII fields if not already done
    enc_firstname = firstname if already_pii_encrypted(firstname) else encrypt_pii(firstname) if firstname else firstname
    enc_lastname  = lastname  if already_pii_encrypted(lastname)  else encrypt_pii(lastname)  if lastname  else lastname

    cur.execute("""
        UPDATE users
        SET email_display=%s, firstname=%s, lastname=%s
        WHERE id=%s
    """, (store_email(raw_email), enc_firstname, enc_lastname, user_id))

    print(f"  ✓ email_display set and PII encrypted for ID={user_id}.\n")

db.commit()
cur.close()
db.close()

print("✅ Recovery complete! You can now log in.")