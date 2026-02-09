from flask import Flask

from auth.routes import auth_bp
from notes.routes import notes_bp

app = Flask(__name__)
app.secret_key = "dev-secret-key-9f3a7c1e8b2d4a6f"

app.register_blueprint(auth_bp)
app.register_blueprint(notes_bp)

@app.route("/")
def home():
    return "SecureNotes running"

if __name__ == "__main__":
    app.run(debug=True)
