from flask import Blueprint, request, redirect, url_for, session, render_template
from db import get_db_connection

notes_bp = Blueprint("notes", __name__)

@notes_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("dashboard.html")

@notes_bp.route("/notes", methods=["GET", "POST"])
def notes():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO notes (user_id, title, content) VALUES (%s, %s, %s)",
            (user_id, title, content),
        )
        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for("notes.notes"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, created_at FROM notes WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    items = "".join([f"<li>{r[1]} ({r[2]}) <a href='/notes/{r[0]}'>Open</a></li>" for r in rows])

    return render_template("notes.html", notes=[
{"id": r[0], "title": r[1], "created_at": r[2]} for r in rows
])

@notes_bp.route("/notes/<int:note_id>")
def view_note(note_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT title, content, created_at FROM notes WHERE id = %s AND user_id = %s",
        (note_id, user_id),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return "Note not found", 404

    title, content, created_at = row[0], row[1], row[2]

    return render_template("view_note.html",
title=title,
content=content,
created_at=created_at
)
    
@notes_bp.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
def edit_note(note_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        cur.execute(
            "UPDATE notes SET title=%s, content=%s WHERE id=%s AND user_id=%s",
            (title, content, note_id, user_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/notes")

    cur.execute(
        "SELECT id, title, content FROM notes WHERE id=%s AND user_id=%s",
        (note_id, user_id)
    )
    note = cur.fetchone()
    cur.close()
    conn.close()

    if not note:
        return "Note not found", 404

    return render_template("edit_note.html", note=note)



@notes_bp.route("/notes/<int:note_id>/delete", methods=["POST"])
def delete_note(note_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect("/login")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM notes WHERE id=%s AND user_id=%s",
        (note_id, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/notes")


