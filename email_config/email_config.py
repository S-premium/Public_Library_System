"""
email_config/email_config.py
-----------------------------
All outgoing email helpers — now using Resend HTTPS API (port 443).
Replaces raw smtplib/SMTP so emails work on Render free tier.

Requires env var:  RESEND_API_KEY=re_xxxxxxxxxxxx
Optional env var:  RESEND_FROM=noreply@yourdomain.com
                   (defaults to onboarding@resend.dev for testing)
"""

import os
import json
import requests

from conn import mysql
from helpers import safe_decrypt_email, safe_decrypt_pii

# ── Credentials ───────────────────────────────────────────────────────────────
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM    = os.getenv("RESEND_FROM", "onboarding@resend.dev")
DISABLE_EMAIL  = not RESEND_API_KEY

RESEND_URL = "https://api.resend.com/emails"


def _send(to: str, subject: str, html: str, text: str = "") -> bool:
    """
    Core Resend API call. Returns True on success, False on failure.
    All other helpers call this instead of touching smtplib.
    """
    if DISABLE_EMAIL:
        print("=" * 50)
        print(f"📧 EMAIL (dev mode — RESEND_API_KEY not set)")
        print(f"To     : {to}")
        print(f"Subject: {subject}")
        print("=" * 50)
        return True

    payload = {
        "from":    RESEND_FROM,
        "to":      [to],
        "subject": subject,
        "html":    html,
    }
    if text:
        payload["text"] = text

    try:
        resp = requests.post(
            RESEND_URL,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type":  "application/json",
            },
            data=json.dumps(payload),
            timeout=10,
        )
        if resp.status_code in (200, 201):
            print(f"✅ Email sent → {to} ({subject})")
            return True
        else:
            print(f"❌ Resend error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False


# =====================================================================
# OTP
# OTP format: 3 uppercase letters + 3 digits  e.g. "XKB492"
# =====================================================================

def send_otp_email(to_email: str, otp: str) -> bool:
    letters_part = otp[:3]
    digits_part  = otp[3:]

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Login Verification</title>
</head>
<body style="margin:0;padding:0;background-color:#eef2f7;
             font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;">

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background-color:#eef2f7;padding:48px 16px;">
    <tr><td align="center">

      <table role="presentation" width="560" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:20px;
                    box-shadow:0 8px 40px rgba(0,0,0,0.10);overflow:hidden;
                    max-width:560px;width:100%;">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(140deg,#0f2d5e 0%,#1a4fae 60%,#2563eb 100%);
                     padding:40px 40px 36px;text-align:center;">
            <div style="display:inline-block;background:rgba(255,255,255,0.15);
                        border-radius:50%;width:64px;height:64px;line-height:64px;
                        font-size:30px;margin-bottom:16px;">📚</div>
            <h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:700;
                       letter-spacing:0.4px;line-height:1.3;">
              Iloilo City Public Library
            </h1>
            <p style="margin:6px 0 0;color:#93c5fd;font-size:12px;
                      letter-spacing:1.5px;text-transform:uppercase;font-weight:600;">
              Secure Login Verification
            </p>
          </td>
        </tr>

        <!-- BODY -->
        <tr>
          <td style="padding:40px 44px 36px;">
            <p style="margin:0 0 6px;color:#111827;font-size:17px;font-weight:600;">
              Hello there 👋
            </p>
            <p style="margin:0 0 32px;color:#6b7280;font-size:14px;line-height:1.7;">
              We received a login request for your library account. Enter
              the one-time password below to complete verification.
            </p>

            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                   style="background:linear-gradient(135deg,#f0f7ff,#e8f0fe);
                          border:1.5px solid #bfdbfe;border-radius:16px;
                          margin-bottom:12px;">
              <tr>
                <td style="padding:28px 20px 20px;text-align:center;">
                  <p style="margin:0 0 18px;color:#6b7280;font-size:11px;
                             text-transform:uppercase;letter-spacing:2px;font-weight:700;">
                    One-Time Password
                  </p>
                  <div style="display:inline-block;background:#0f2d5e;
                              border-radius:12px;padding:16px 36px;
                              box-shadow:0 4px 16px rgba(37,99,235,0.25);">
                    <span style="font-family:'Courier New',Courier,monospace;
                                 font-size:36px;font-weight:800;
                                 color:#ffffff;letter-spacing:10px;
                                 display:inline-block;">
                      {letters_part}{digits_part}
                    </span>
                  </div>
                  <div style="display:inline-block;margin-top:18px;
                              background:#fef2f2;border:1px solid #fecaca;
                              border-radius:20px;padding:6px 16px;">
                    <span style="color:#dc2626;font-size:12px;font-weight:600;">
                      ⏱&nbsp; Expires in 5 minutes
                    </span>
                  </div>
                </td>
              </tr>
            </table>

            <p style="margin:0 0 28px;color:#9ca3af;font-size:11px;
                       text-align:center;line-height:1.5;">
              Enter all 6 characters exactly as shown — letters then numbers.
            </p>

            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                   style="background:#fffbeb;border:1px solid #fcd34d;
                          border-left:4px solid #f59e0b;border-radius:10px;
                          margin-bottom:24px;">
              <tr>
                <td style="padding:14px 18px;">
                  <p style="margin:0;color:#92400e;font-size:13px;line-height:1.6;">
                    <strong>⚠ Didn't try to log in?</strong><br/>
                    If this wasn't you, please ignore this email — your account
                    is still safe and no changes have been made.
                  </p>
                </td>
              </tr>
            </table>

            <p style="margin:0;color:#d1d5db;font-size:11px;text-align:center;">
              Never share this code with anyone. Library staff will <em>never</em> ask for it.
            </p>
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#f9fafb;border-top:1px solid #e5e7eb;
                     padding:20px 44px;text-align:center;">
            <p style="margin:0;color:#9ca3af;font-size:11px;line-height:1.8;">
              Iloilo City Public Library System &nbsp;·&nbsp; Iloilo City, Philippines<br/>
              Dr. Graciano Lopez Jaena Learning Resource Center<br/>
              <span style="color:#d1d5db;">This is an automated message — please do not reply.</span>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return _send(
        to=to_email,
        subject="🔐 Your Login Verification Code — Iloilo City Public Library",
        html=html_body,
        text=(
            f"Your one-time password is: {letters_part}-{digits_part}\n"
            f"(Enter as: {otp})\n\n"
            f"Expires in 5 minutes.\n\n"
            f"If you did not request this, ignore this email.\n\n"
            f"— Iloilo City Public Library"
        ),
    )


# =====================================================================
# PASSWORD RESET
# =====================================================================

def send_reset_email(to_email: str, reset_link: str) -> bool:
    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,.12);">
        <tr>
          <td style="background:linear-gradient(135deg,#2f3f4d,#42586b);padding:36px 40px;text-align:center;">
            <h1 style="margin:0;color:#9fc1e1;font-size:22px;font-weight:700;">📚 Iloilo City Public Library</h1>
            <p style="margin:6px 0 0;color:#dae8f5;font-size:13px;">Dr. Graciano Lopez Jaena Learning Resource Center</p>
          </td>
        </tr>
        <tr>
          <td style="padding:40px 40px 30px;">
            <h2 style="margin:0 0 16px;color:#2f3f4d;font-size:20px;font-weight:700;">Password Reset Request</h2>
            <p style="margin:0 0 28px;color:#42586b;font-size:15px;line-height:1.6;">
              Click the button below to set a new password. This link expires in <strong>1 hour</strong>.
            </p>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="center" style="padding-bottom:28px;">
                  <a href="{reset_link}"
                     style="display:inline-block;background:#9fc1e1;color:#0d1a24;
                            text-decoration:none;font-weight:700;font-size:16px;
                            padding:14px 36px;border-radius:30px;">
                    🔑 Reset My Password
                  </a>
                </td>
              </tr>
            </table>
            <p style="margin:0;color:#8a9bb0;font-size:12px;">
              If the button doesn't work, copy and paste:<br>
              <a href="{reset_link}" style="color:#42586b;word-break:break-all;">{reset_link}</a>
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#f0f4f8;padding:16px 40px;text-align:center;border-top:1px solid #e0e8f0;">
            <p style="margin:0;color:#8a9bb0;font-size:11px;">
              © 2025 Iloilo City Public Library · Automated message, do not reply.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return _send(
        to=to_email,
        subject="Password Reset Request — Iloilo City Public Library",
        html=html_body,
        text=(
            f"You requested a password reset.\n\n"
            f"Reset link (expires in 1 hour):\n{reset_link}\n\n"
            f"If you did not request this, ignore this email.\n\n"
            f"— Iloilo City Public Library"
        ),
    )


# =====================================================================
# ADMIN NOTIFICATION — new registration
# =====================================================================

def notify_admins_new_registration(firstname: str, lastname: str, email: str) -> None:
    firstname = safe_decrypt_pii(firstname)
    lastname  = safe_decrypt_pii(lastname)
    email     = safe_decrypt_email(email)

    if DISABLE_EMAIL:
        print(f"[ADMIN NOTIFY] New registration: {firstname} {lastname} <{email}>")
        return

    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT email_display FROM users WHERE role='admin' AND is_active=1")
        admin_emails = [safe_decrypt_email(row[0]) for row in cur.fetchall() if row[0]]
        cur.close()
    except Exception as e:
        print(f"[ADMIN NOTIFY] Could not fetch admin emails: {e}")
        return

    if not admin_emails:
        return

    requests_url = "https://public-library-system.onrender.com/admin/account-requests"
    subject      = "New Registration Request — Iloilo City Public Library"

    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,.12);">
        <tr>
          <td style="background:linear-gradient(135deg,#2f3f4d,#42586b);padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#9fc1e1;font-size:20px;font-weight:700;">📚 Iloilo City Public Library</h1>
            <p style="margin:5px 0 0;color:#dae8f5;font-size:12px;">Admin Notification</p>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 40px;">
            <h2 style="margin:0 0 14px;color:#2f3f4d;font-size:18px;font-weight:700;">🆕 New Registration Request</h2>
            <p style="margin:0 0 20px;color:#42586b;font-size:14px;line-height:1.7;">
              A new user has signed up and is waiting for your approval:
            </p>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#f8fbff;border:1px solid #d0e4f5;border-radius:10px;margin-bottom:24px;">
              <tr>
                <td style="padding:14px 20px;border-bottom:1px solid #e8f0f8;">
                  <span style="font-size:11px;font-weight:700;color:#8a9bb0;text-transform:uppercase;">Full Name</span><br>
                  <span style="font-size:15px;color:#2f3f4d;font-weight:600;">{firstname} {lastname}</span>
                </td>
              </tr>
              <tr>
                <td style="padding:14px 20px;">
                  <span style="font-size:11px;font-weight:700;color:#8a9bb0;text-transform:uppercase;">Email</span><br>
                  <span style="font-size:14px;color:#42586b;">{email}</span>
                </td>
              </tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="center">
                  <a href="{requests_url}"
                     style="display:inline-block;background:#9fc1e1;color:#0d1a24;
                            text-decoration:none;font-weight:700;font-size:15px;
                            padding:13px 32px;border-radius:30px;">
                    ✅ Review Request
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="background:#f0f4f8;padding:16px 40px;text-align:center;border-top:1px solid #e0e8f0;">
            <p style="margin:0;color:#8a9bb0;font-size:11px;">
              © 2025 Iloilo City Public Library · Automated notification, do not reply.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    for admin_email in admin_emails:
        _send(
            to=admin_email,
            subject=subject,
            html=html_body,
            text=f"New registration: {firstname} {lastname} ({email}). Review at: {requests_url}",
        )


# =====================================================================
# REGISTRATION DECISION EMAIL
# =====================================================================

def send_registration_decision_email(user_id: int, approved: bool, note: str = "") -> None:
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT email_display, firstname, lastname FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        cur.close()
    except Exception:
        return

    if not row:
        return

    to_email  = safe_decrypt_email(row[0])
    firstname = safe_decrypt_pii(row[1])
    lastname  = safe_decrypt_pii(row[2])

    site_url = "https://public-library-system.onrender.com"

    if approved:
        subject    = "Registration Approved — Iloilo City Public Library"
        headline   = "🎉 Your Registration is Approved!"
        color      = "#48c78e"
        body_text  = (
            f"Welcome, {firstname}! Your account has been approved by our admin. "
            "You can now log in and start exploring the library."
        )
        note_label = "Admin Note"
        cta_text   = "Log In Now"
        cta_url    = site_url
    else:
        subject    = "Registration Update — Iloilo City Public Library"
        headline   = "Registration Not Approved"
        color      = "#ff6363"
        body_text  = (
            f"Hi {firstname}, we're sorry to inform you that your registration "
            "request was reviewed and was not approved at this time."
        )
        note_label = "Reason"
        cta_text   = "Visit Our Website"
        cta_url    = site_url

    note_block = (
        f"""<tr><td style="padding:14px 20px;">
          <span style="font-size:11px;font-weight:700;color:#8a9bb0;
                       text-transform:uppercase;">{note_label}</span><br>
          <span style="font-size:14px;color:#42586b;">{note or 'No additional note provided.'}</span>
        </td></tr>"""
        if (note or not approved) else ""
    )

    html_body = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,.12);">
        <tr>
          <td style="background:linear-gradient(135deg,#2f3f4d,#42586b);padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#9fc1e1;font-size:20px;font-weight:700;">📚 Iloilo City Public Library</h1>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 40px;">
            <h2 style="margin:0 0 14px;color:{color};font-size:20px;font-weight:700;">{headline}</h2>
            <p style="margin:0 0 20px;color:#42586b;font-size:14px;line-height:1.7;">{body_text}</p>
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#f8fbff;border:1px solid #d0e4f5;border-radius:10px;margin-bottom:24px;">
              {note_block}
            </table>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="center">
                  <a href="{cta_url}"
                     style="display:inline-block;background:{color};
                            color:{'#0d1a24' if approved else '#fff'};
                            text-decoration:none;font-weight:700;font-size:15px;
                            padding:13px 32px;border-radius:30px;">
                    {cta_text}
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td style="background:#f0f4f8;padding:16px 40px;text-align:center;border-top:1px solid #e0e8f0;">
            <p style="margin:0;color:#8a9bb0;font-size:11px;">
              © 2025 Iloilo City Public Library · Do not reply to this email.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    _send(to=to_email, subject=subject, html=html_body, text=body_text)


# =====================================================================
# PIN EXPIRY EMAIL
# =====================================================================

def send_pin_expiry_email(to_email: str, firstname: str, reset_link: str) -> bool:
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><title>PIN Expired</title></head>
<body style="margin:0;padding:0;background:#eef2f7;
             font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:#eef2f7;padding:48px 16px;">
    <tr><td align="center">
      <table role="presentation" width="560" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:20px;
                    box-shadow:0 8px 40px rgba(0,0,0,.10);overflow:hidden;
                    max-width:560px;width:100%;">

        <!-- HEADER -->
        <tr>
          <td style="background:linear-gradient(140deg,#0f2d5e 0%,#1a4fae 60%,#2563eb 100%);
                     padding:40px 40px 36px;text-align:center;">
            <div style="display:inline-block;background:rgba(255,255,255,.15);
                        border-radius:50%;width:64px;height:64px;line-height:64px;
                        font-size:30px;margin-bottom:16px;">🔐</div>
            <h1 style="margin:0;color:#fff;font-size:20px;font-weight:700;">
              Iloilo City Public Library
            </h1>
            <p style="margin:6px 0 0;color:#93c5fd;font-size:12px;
                      letter-spacing:1.5px;text-transform:uppercase;font-weight:600;">
              PIN Security Notice
            </p>
          </td>
        </tr>

        <!-- BODY -->
        <tr>
          <td style="padding:40px 44px 36px;">
            <p style="margin:0 0 6px;color:#111827;font-size:17px;font-weight:600;">
              Hello, {firstname} 👋
            </p>
            <p style="margin:0 0 24px;color:#6b7280;font-size:14px;line-height:1.7;">
              Your login PIN has <strong style="color:#dc2626;">expired</strong>.
              For your security, PINs are valid for <strong>1 week</strong>.
            </p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                   style="background:#fef2f2;border:1px solid #fecaca;
                          border-left:4px solid #dc2626;border-radius:10px;
                          margin-bottom:28px;">
              <tr>
                <td style="padding:16px 18px;">
                  <p style="margin:0;color:#991b1b;font-size:13px;line-height:1.7;">
                    <strong>What happens next?</strong><br/>
                    Your PIN has been automatically bypassed for this login.
                    Click the button below to set a new PIN and restore your full account security.
                  </p>
                </td>
              </tr>
            </table>
            <table role="presentation" cellpadding="0" cellspacing="0"
                   style="margin:0 auto 28px;">
              <tr>
                <td style="background:linear-gradient(135deg,#1a4fae,#2563eb);
                           border-radius:12px;
                           box-shadow:0 4px 16px rgba(37,99,235,.35);">
                  <a href="{reset_link}"
                     style="display:inline-block;padding:16px 40px;
                            color:#ffffff;font-size:15px;font-weight:700;
                            text-decoration:none;letter-spacing:0.3px;">
                    🔑 &nbsp; Set New PIN
                  </a>
                </td>
              </tr>
            </table>
            <p style="margin:0 0 28px;color:#9ca3af;font-size:11px;
                      text-align:center;line-height:1.6;">
              This link expires in <strong>1 hour</strong>.<br/>
              If you did not request this, your account is safe — simply ignore this email.
            </p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                   style="background:#fffbeb;border:1px solid #fcd34d;
                          border-left:4px solid #f59e0b;border-radius:10px;">
              <tr>
                <td style="padding:14px 18px;">
                  <p style="margin:0;color:#92400e;font-size:13px;line-height:1.6;">
                    <strong>⚠ Security reminder:</strong> Never share your PIN
                    with anyone. Library staff will never ask for it.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background:#f9fafb;border-top:1px solid #e5e7eb;
                     padding:20px 44px;text-align:center;">
            <p style="margin:0;color:#9ca3af;font-size:11px;line-height:1.8;">
              Iloilo City Public Library System &nbsp;·&nbsp; Iloilo City, Philippines<br/>
              Dr. Graciano Lopez Jaena Learning Resource Center<br/>
              <span style="color:#d1d5db;">This is an automated message — please do not reply.</span>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    return _send(
        to=to_email,
        subject="Your Library PIN Has Expired — Action Required",
        html=html_body,
        text=(
            f"Hi {firstname}, your library PIN has expired.\n\n"
            f"Set a new PIN here (link expires in 1 hour):\n{reset_link}\n\n"
            f"— Iloilo City Public Library"
        ),
    )