from flask import request, session
from db import get_db_connection

def log_activity(event_type: str) -> None:
    user_id = session.get("user_id")
    if not user_id:
        return

    ip_address = request.headers.get(
        "X-Forwarded-For",
        request.remote_addr
    )
    user_agent = request.headers.get("User-Agent", "")[:255]

    db = get_db_connection()
    cur = db.cursor()

    cur.execute(
        """
        INSERT INTO activity_log (user_id, event_type, ip_address, user_agent)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, event_type, ip_address, user_agent)
    )

    db.commit()
    cur.close()
    db.close()
