import os
import sqlite3
import json
from datetime import datetime
from flask import (
    Flask, request, jsonify, redirect,
    render_template, send_from_directory
)
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from flask_cors import CORS

from yandex_disk import YandexDisk


# ================== CONFIG ==================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "legal_crm.db")

YANDEX_TOKEN = os.environ.get("YANDEX_TOKEN", "")
SYNC_DIR = "Apps/LegalCRM/backups"

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin"


# ================== APP ==================

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "super-secret-key"
CORS(app, supports_credentials=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ================== USER ==================

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id


@login_manager.user_loader
def load_user(user_id):
    if user_id == ADMIN_LOGIN:
        return User(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    # IMPORTANT: API must NOT redirect
    if request.path.startswith("/api/"):
        return jsonify({"error": "unauthorized"}), 401
    return redirect("/login")


# ================== DB ==================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_number TEXT NOT NULL,
        client_id INTEGER,
        title TEXT,
        status TEXT,
        notes TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL,
        description TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        created_at TEXT
    );
    """)

    conn.commit()
    conn.close()


init_db()


# ================== WEB ==================

@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


@app.route("/")
@login_required
def index():
    return render_template("index.html")


# ================== AUTH API ==================

@app.route("/api/auth/check")
def api_auth_check():
    return jsonify({"authenticated": current_user.is_authenticated})


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data = request.json or {}
    if (
        data.get("login") == ADMIN_LOGIN
        and data.get("password") == ADMIN_PASSWORD
    ):
        login_user(User(ADMIN_LOGIN))
        return jsonify({"success": True})

    return jsonify({"success": False}), 401


# ================== HELPERS ==================

def rows_to_dicts(rows):
    return [dict(row) for row in rows]


# ================== DATA API ==================

@app.route("/api/clients", methods=["GET", "POST"])
@login_required
def api_clients():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        data = request.json or {}
        cur.execute(
            "INSERT INTO clients (name, phone, email, created_at) VALUES (?, ?, ?, ?)",
            (data.get("name"), data.get("phone"), data.get("email"), datetime.utcnow().isoformat())
        )
        conn.commit()

    cur.execute("SELECT * FROM clients")
    rows = rows_to_dicts(cur.fetchall())
    conn.close()
    return jsonify(rows)


@app.route("/api/cases", methods=["GET", "POST"])
@login_required
def api_cases():
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        data = request.json or {}
        case_number = data.get("case_number") or f"CASE-{int(datetime.utcnow().timestamp())}"

        cur.execute(
            """INSERT INTO cases
            (case_number, client_id, title, status, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                case_number,
                data.get("client_id"),
                data.get("title"),
                data.get("status"),
                data.get("notes"),
                datetime.utcnow().isoformat()
            )
        )
        conn.commit()

    cur.execute("SELECT * FROM cases")
    rows = rows_to_dicts(cur.fetchall())
    conn.close()
    return jsonify(rows)


@app.route("/api/services", methods=["GET"])
@login_required
def api_services():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM services")
    rows = rows_to_dicts(cur.fetchall())
    conn.close()
    return jsonify(rows)


@app.route("/api/payments", methods=["GET"])
@login_required
def api_payments():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM payments")
    rows = rows_to_dicts(cur.fetchall())
    conn.close()
    return jsonify(rows)


@app.route("/api/activities", methods=["GET"])
@login_required
def api_activities():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM activities")
    rows = rows_to_dicts(cur.fetchall())
    conn.close()
    return jsonify(rows)


@app.route("/api/stats")
@login_required
def api_stats():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM clients")
    clients = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM cases")
    cases = cur.fetchone()[0]

    conn.close()
    return jsonify({
        "clients": clients,
        "cases": cases
    })


# ================== SYNC ==================

def get_disk():
    if not YANDEX_TOKEN:
        return None
    return YandexDisk(YANDEX_TOKEN, SYNC_DIR)


@app.route("/api/sync/status")
@login_required
def api_sync_status():
    return jsonify({
        "configured": bool(YANDEX_TOKEN),
        "last_sync": None,
        "backups": 0
    })


@app.route("/api/sync/upload", methods=["POST"])
@login_required
def api_sync_upload():
    yd = get_disk()
    if not yd:
        return jsonify({"error": "not configured"}), 400

    name = yd.upload_backup(DATABASE)
    return jsonify({"success": True, "backup": name})


@app.route("/api/sync/backups")
@login_required
def api_sync_backups():
    yd = get_disk()
    if not yd:
        return jsonify([])

    return jsonify(yd.list_backups())


# ================== RUN ==================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
