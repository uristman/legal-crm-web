from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, UserMixin, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

DATABASE = "legal_crm.db"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")

# =====================
# DATABASE
# =====================

def db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        cur = c.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT
            )
        """)

        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ("admin", generate_password_hash("12345"))
            )

        c.commit()

init_db()

# =====================
# AUTH
# =====================

login_manager = LoginManager(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.password = row["password"]

@login_manager.user_loader
def load_user(user_id):
    with db() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        return User(row) if row else None

# =====================
# PAGES
# =====================

@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/logout")
def logout():
    logout_user()
    return redirect("/login")

# =====================
# AUTH API
# =====================

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json()
    with db() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (data["username"],))
        row = cur.fetchone()

    if not row or not check_password_hash(row["password"], data["password"]):
        return jsonify(success=False)

    login_user(User(row))
    return jsonify(success=True)

@app.route("/api/auth/check")
def api_auth_check():
    return jsonify(authenticated=current_user.is_authenticated)

@app.route("/api/auth/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify(success=True)

# =====================
# STUB API (ВАЖНО)
# =====================

@app.route("/api/clients", methods=["GET", "POST"])
@login_required
def api_clients():
    return jsonify(success=True, clients=[])

@app.route("/api/cases")
@login_required
def api_cases():
    return jsonify(success=True, cases=[])

@app.route("/api/activities")
@login_required
def api_activities():
    return jsonify(success=True, activities=[])

@app.route("/api/payments")
@login_required
def api_payments():
    return jsonify(success=True, payments=[])

@app.route("/api/services")
@login_required
def api_services():
    return jsonify(success=True, services=[])

@app.route("/api/stats")
@login_required
def api_stats():
    return jsonify(success=True, stats={})

@app.route("/api/sync/status")
@login_required
def api_sync_status():
    return jsonify(success=True, connected=False)

@app.route("/api/sync/backups")
@login_required
def api_sync_backups():
    return jsonify(success=True, backups=[])
