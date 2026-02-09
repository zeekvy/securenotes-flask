from flask import Blueprint, render_template, session, abort
from db import get_db_connection

activity_bp = Blueprint("activity", __name__, url_prefix="/activity")


def login_required():
    if not session.get("user_id"):
        abort(404)

@activity_bp.route("/", methods=["GET"])
def history():
    if not session.get("user_id"):
        abort(404)

    user_id = session["user_id"]
    db = get_db_connection()
    cur = db.cursor()

    cur.execute("""
        SELECT event_type, created_at
        FROM activity_log
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 100
    """, (user_id,))

    rows = cur.fetchall()
    activities = [
        {"event_type": r[0], "created_at": r[1]}
        for r in rows
    ]

    cur.close()
    db.close()

    return render_template(
        "activity/history.html",
        activities=activities
    )
