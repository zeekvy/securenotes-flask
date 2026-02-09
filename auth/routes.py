from flask import Blueprint, request, redirect, url_for, session
from flask_bcrypt import Bcrypt
from db import get_db_connection
from flask import render_template

auth_bp = Blueprint("auth", __name__)
bcrypt = Bcrypt()

@auth_bp.record_once
def init(state):
    bcrypt.init_app(state.app)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if len(password) < 8:
        return "Password must be at least 8 characters", 400
    if len(email) > 255:
        return "Email too long", 400
    weak = {"password", "12345678", "qwerty123", "password123"}
    if password.strip().lower() in weak:
        return "Password too common", 400

   

    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
        (email, pw_hash),
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("auth.login"))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return "Invalid login", 401

    user_id, pw_hash = row[0], row[1]

    if not bcrypt.check_password_hash(pw_hash, password):
        return "Invalid login", 401

    session["user_id"] = user_id
    return redirect("/dashboard")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
