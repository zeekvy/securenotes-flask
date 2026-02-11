from flask import Blueprint, request, redirect, url_for, session, render_template
from db import get_db_connection
from activity.logger import log_activity

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

        log_activity("note_create")

        cur.close()
        conn.close()

        return redirect(url_for("notes.notes"))

    q = (request.args.get("q") or "").strip()

    conn = get_db_connection()
    cur = conn.cursor()

    if q:
        like = f"%{q}%"
        cur.execute(
            """
            SELECT id, title, created_at
            FROM notes
            WHERE user_id = %s
              AND (title LIKE %s OR content LIKE %s)
            ORDER BY created_at DESC
            """,
            (user_id, like, like),
        )
        log_activity("note_search")
    else:
        cur.execute(
            """
            SELECT id, title, created_at
            FROM notes
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,),
        )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return render_template(
        "notes.html",
        q=q,
        notes=[{"id": r[0], "title": r[1], "created_at": r[2]} for r in rows],
    )



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

    return render_template(
        "view_note.html",
        title=row[0],
        content=row[1],
        created_at=row[2]
    )


@notes_bp.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
def edit_note(note_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        cur.execute(
            "UPDATE notes SET title = %s, content = %s WHERE id = %s AND user_id = %s",
            (title, content, note_id, user_id)
        )
        conn.commit()

        log_activity("note_update")

        cur.close()
        conn.close()

        return redirect(url_for("notes.notes"))

    cur.execute(
        "SELECT id, title, content FROM notes WHERE id = %s AND user_id = %s",
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
        return redirect(url_for("auth.login"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM notes WHERE id = %s AND user_id = %s",
        (note_id, user_id)
    )
    conn.commit()

    log_activity("note_delete")

    cur.close()
    conn.close()

    return redirect(url_for("notes.notes"))
