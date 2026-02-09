# auth/routes.py

from flask import Blueprint, render_template, request, redirect, url_for, session
import bcrypt

from db import get_db_connection
from activity.logger import log_activity

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return "Email and password required", 400

    db = get_db_connection()
    cur = db.cursor(dictionary=True)

    cur.execute(
        "SELECT id, password_hash FROM users WHERE email = %s",
        (email,)
    )
    user = cur.fetchone()

    cur.close()
    db.close()

    if not user:
        return "Invalid email or password", 401

    stored = user.get("password_hash")
    if not stored:
        return "Invalid email or password", 401

    stored_hash = stored if isinstance(stored, (bytes, bytearray)) else str(stored).encode("utf-8")

    if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        return "Invalid email or password", 401

    session["user_id"] = user["id"]
    log_activity("user_login")

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
    if len(email) > 255:
        return "Email too long", 400
    if not password:
        return "Password required", 400
    if len(password) < 8:
        return "Password must be at least 8 characters", 400
    if password != confirm:
        return "Passwords do not match", 400

    weak = {"password", "12345678", "qwerty123", "password123"}
    if password.strip().lower() in weak:
        return "Password too common", 400

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

    return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
def logout():
    if session.get("user_id"):
        log_activity("user_logout")

    session.clear()
    return redirect(url_for("auth.login"))
