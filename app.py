from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from auth import auth_bp
from notes.routes import notes_bp
from activity.routes import activity_bp

app = Flask(__name__)

# Core security config
app.secret_key = "dev-secret-key-9f3a7c1e8b2d4a6f"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# CSRF protection
csrf = CSRFProtect(app)

# Content Security Policy
csp = {
    "default-src": ["'self'"],
    "img-src": ["'self'", "data:"],
    "style-src": ["'self'", "'unsafe-inline'"],
    "script-src": ["'self'"],
}



# Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(notes_bp)
app.register_blueprint(activity_bp)

from datetime import datetime, timedelta, timezone
from flask import session, redirect, url_for, request

app.permanent_session_lifetime = timedelta(minutes=15)

IDLE_SECONDS = 15

@app.before_request
def enforce_idle_timeout():
    if request.endpoint == "static":
        return

    public_endpoints = {
        "auth.login",
        "auth.register"
    }
    if request.endpoint in public_endpoints:
        return

    user_id = session.get("user_id")
    if not user_id:
        return

    now = datetime.now(timezone.utc).timestamp()
    last_activity = session.get("last_activity")

    if last_activity and (now - float(last_activity)) > IDLE_SECONDS:
        from activity.logger import log_activity
        log_activity("LOGOUT_IDLE_TIMEOUT")

        session.clear()
        return redirect(url_for("auth.login"))

    session["last_activity"] = now
    session.permanent = True

#Security headers
@app.after_request
def add_security_headers(resp):
    resp.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'"
)
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return resp

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

# Root route
@app.route("/")
def home():
    return "SecureNotes running"


if __name__ == "__main__":
    app.run(debug=True)
