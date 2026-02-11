# auth/routes.py

from flask import render_template, request, redirect, url_for, session, current_app
import bcrypt
from datetime import datetime, timedelta
import secrets

from db import get_db_connection
from activity.logger import log_activity
from . import auth_bp

from flask_mail import Message
from extensions import mail

MAX_FAILS = 5
LOCK_MINUTES = 15

OTP_EXP_MINUTES = 5


def get_login_attempt(email: str):
    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute(
        "SELECT email, fail_count, locked_until FROM login_attempts WHERE email = %s",
        (email,)
    )
    row = cur.fetchone()

    cur.close()
    db.close()
    return row


def upsert_fail(email: str):
    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute(
        "SELECT fail_count FROM login_attempts WHERE email = %s",
        (email,)
    )
    row = cur.fetchone()

    fail_count = 1
    locked_until = None

    if row:
        fail_count = int(row["fail_count"]) + 1

    if fail_count >= MAX_FAILS:
        locked_until = datetime.now() + timedelta(minutes=LOCK_MINUTES)

    if row:
        cur.execute(
            "UPDATE login_attempts SET fail_count = %s, locked_until = %s WHERE email = %s",
            (fail_count, locked_until, email)
        )
    else:
        cur.execute(
            "INSERT INTO login_attempts (email, fail_count, locked_until) VALUES (%s, %s, %s)",
            (email, fail_count, locked_until)
        )

    db.commit()
    cur.close()
    db.close()


def reset_attempts(email: str):
    db = get_db_connection()
    cur = db.cursor()
    cur.execute(
        "UPDATE login_attempts SET fail_count = 0, locked_until = NULL WHERE email = %s",
        (email,)
    )
    db.commit()
    cur.close()
    db.close()


def create_otp(user_id: int, email: str) -> str:
    code = f"{secrets.randbelow(1000000):06d}"
    expires_at = datetime.now() + timedelta(minutes=OTP_EXP_MINUTES)

    db = get_db_connection()
    cur = db.cursor()

    cur.execute(
        "INSERT INTO login_otp (user_id, otp_code, expires_at, used) VALUES (%s, %s, %s, 0)",
        (user_id, code, expires_at)
    )
    db.commit()

    cur.close()
    db.close()

    log_activity("OTP_CREATED", username=email, details="otp generated")
    return code


def send_otp_email(user_email: str, code: str) -> None:
    msg = Message(
        subject="SecureNotes verification code",
        recipients=[user_email],
        body=(
            f"Your SecureNotes verification code is: {code}\n\n"
            f"This code expires in {OTP_EXP_MINUTES} minutes."
        ),
    )

    try:
        mail.send(msg)
    except Exception as e:
        current_app.logger.exception("OTP email send failed")
        log_activity("OTP_EMAIL_SEND_FAILED", username=user_email, details=str(e))
        raise


def verify_otp(user_id: int, code: str):
    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute(
        """
        SELECT id, otp_code, expires_at, used
        FROM login_otp
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )
    row = cur.fetchone()

    if not row:
        cur.close()
        db.close()
        return False, "no otp"

    if row["used"]:
        cur.close()
        db.close()
        return False, "otp already used"

    if row["expires_at"] <= datetime.now():
        cur.close()
        db.close()
        return False, "otp expired"

    if str(row["otp_code"]) != str(code):
        cur.close()
        db.close()
        return False, "otp mismatch"

    cur.execute(
        "UPDATE login_otp SET used = 1 WHERE id = %s",
        (row["id"],)
    )
    db.commit()

    cur.close()
    db.close()
    return True, "ok"


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return "Email and password required", 400

    attempt = get_login_attempt(email)
    if attempt and attempt.get("locked_until"):
        if attempt["locked_until"] > datetime.now():
            log_activity("LOGIN_BLOCKED_LOCKOUT", username=email, details="account locked")
            return "Account locked. Try again later.", 403

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute(
        "SELECT id, email, password_hash FROM users WHERE email = %s",
        (email,)
    )
    user = cur.fetchone()

    cur.close()
    db.close()

    if not user:
        upsert_fail(email)
        log_activity("LOGIN_FAILED", username=email, details="user not found")
        return "Invalid email or password", 401

    stored = user.get("password_hash")
    if not stored:
        upsert_fail(email)
        log_activity("LOGIN_FAILED", username=email, details="no password hash")
        return "Invalid email or password", 401

    if not bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8")):
        upsert_fail(email)
        log_activity("LOGIN_FAILED", username=email, details="invalid password")
        return "Invalid email or password", 401

    reset_attempts(email)

    otp_code = create_otp(user["id"], email)
    send_otp_email(email, otp_code)

    session["pending_otp_user_id"] = user["id"]
    session["pending_otp_email"] = email

    log_activity("LOGIN_PASSWORD_OK_2FA_REQUIRED", username=email, details="otp sent and redirect to verify")
    return redirect(url_for("auth.verify"))


@auth_bp.route("/verify", methods=["GET", "POST"])
def verify():
    pending_user_id = session.get("pending_otp_user_id")
    pending_email = session.get("pending_otp_email")

    if not pending_user_id or not pending_email:
        return redirect(url_for("auth.login"))

    if request.method == "GET":
        return render_template("verify.html", email=pending_email)

    code = request.form.get("otp_code", "").strip()

    if not code or len(code) != 6 or not code.isdigit():
        log_activity("OTP_FAILED", username=pending_email, details="bad format")
        return "Invalid code", 400

    ok, reason = verify_otp(pending_user_id, code)
    if not ok:
        log_activity("OTP_FAILED", username=pending_email, details=reason)
        return "Invalid or expired code", 401

    session.pop("pending_otp_user_id", None)
    session.pop("pending_otp_email", None)

    session["user_id"] = pending_user_id
    session["username"] = pending_email

    log_activity("OTP_SUCCESS", user_id=pending_user_id, username=pending_email)
    log_activity("LOGIN_SUCCESS", user_id=pending_user_id, username=pending_email)

    return redirect(url_for("notes.dashboard"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")

    if not email:
        return "Email required", 400
    if not password:
        return "Password required", 400
    if len(password) < 8:
        return "Password must be at least 8 characters", 400
    if password != confirm:
        return "Passwords do not match", 400

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute(
        "SELECT id FROM users WHERE email = %s",
        (email,)
    )
    existing = cur.fetchone()

    if existing:
        cur.close()
        db.close()
        return "Email already registered", 400

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    cur.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
        (email, password_hash)
    )
    db.commit()

    cur.close()
    db.close()

    log_activity("REGISTER_SUCCESS", username=email)
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
def logout():
    if session.get("user_id"):
        log_activity("LOGOUT_MANUAL")

    session.clear()
    return redirect(url_for("auth.login"))
