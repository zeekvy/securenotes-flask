from flask import Flask

from auth.routes import auth_bp
from notes.routes import notes_bp
from activity.routes import activity_bp
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.secret_key = "dev-secret-key-9f3a7c1e8b2d4a6f"
csrf = CSRFProtect(app)

app.register_blueprint(auth_bp)
app.register_blueprint(notes_bp)
app.register_blueprint(activity_bp)


@app.route("/")
def home():
    return "SecureNotes running"


if __name__ == "__main__":
    app.run(debug=True)
