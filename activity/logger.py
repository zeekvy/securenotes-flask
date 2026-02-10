from flask import request, session
from db import get_db_connection

def log_activity(event_type, user_id=None, username=None, note_id=None, details=None):
    if user_id is None:
        user_id = session.get("user_id")

    if username is None:
        username = session.get("username")

    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"
    user_agent = (request.headers.get("User-Agent") or "")[:255]

    db = get_db_connection()
    cur = db.cursor()

    cur.execute(
        """
        INSERT INTO activity_log
        (user_id, username, event_type, ip_address, user_agent, note_id, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (user_id, username, event_type, ip_address, user_agent, note_id, details)
    )

    db.commit()
    cur.close()
    db.close()
