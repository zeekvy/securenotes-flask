# auth/routes.py

from flask import render_template, request, redirect, url_for, session
import bcrypt
from datetime import datetime, timedelta

from db import get_db_connection
from activity.logger import log_activity
from . import auth_bp


MAX_FAILS = 5
LOCK_MINUTES = 15


def get_login_attempt(email):
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


def upsert_fail(email):
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


def reset_attempts(email):
    db = get_db_connection()
    cur = db.cursor()
    cur.execute(
        "UPDATE login_attempts SET fail_count = 0, locked_until = NULL WHERE email = %s",
        (email,)
    )
    db.commit()
    cur.close()
    db.close()


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
            log_activity("LOGIN_BLOCKED_LOCKOUT", username=email)
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

    stored_hash = stored.encode("utf-8")

    if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        upsert_fail(email)
        log_activity("LOGIN_FAILED", username=email, details="invalid password")
        return "Invalid email or password", 401

    reset_attempts(email)

    session["user_id"] = user["id"]
    session["username"] = user["email"]

    log_activity("LOGIN_SUCCESS")

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
