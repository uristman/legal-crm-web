import os
import sqlite3
from datetime import datetime

from flask import Flask, jsonify, request, redirect, render_template
from flask_cors import CORS
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)

from yandex_disk import YandexDisk

# ======================
# CONFIG
# ======================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "legal_crm.db")

YANDEX_TOKEN = os.getenv(
    "YANDEX_DISK_TOKEN",
    "y0__xC0-4YkGNuWAyCO0vKUFjDF_v-xCL6nN0jYFp_VSGo9eiutJ3WTKiv4"
)

# ======================
# APP INIT
# ======================

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "super-secret-key"
CORS(app, supports_credentials=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ======================
# DB
# ======================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        );

        INSERT OR IGNORE INTO users (id, username, password)
        VALUES (1, 'admin', 'admin');

        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            status TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY,
            client_id INTEGER,
            case_number TEXT NOT NULL,
            court TEXT,
            case_type TEXT,
            stage TEXT,
            notes TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY,
            client_id INTEGER,
            amount REAL,
            date TEXT,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY,
            title TEXT,
            date TEXT,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS sync_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_sync TEXT,
            enabled INTEGER
        );

        INSERT OR IGNORE INTO sync_state (id, enabled)
        VALUES (1, 0);
        """)

init_db()

# ======================
# AUTH
# ======================

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    row = get_db().execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    if row:
        return User(row["id"], row["username"])
    return None


# ===== API AUTH (ВАЖНО ДЛЯ UI) =====

@app.route("/api/auth/check")
def api_auth_check():
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user": current_user.username
        })
    return jsonify({"authenticated": False}), 401


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    row = get_db().execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, password)
    ).fetchone()

    if not row:
        return jsonify({"error": "invalid_credentials"}), 401

    user = User(row["id"], row["username"])
    login_user(user)

    return jsonify({"ok": True})


@app.route("/api/auth/logout", methods=["POST"])
@login_required
def api_auth_logout():
    logout_user()
    return jsonify({"ok": True})


# ======================
# UI
# ======================

@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/")
@login_required
def index():
    return render_template("index.html")


# ======================
# API — CLIENTS
# ======================

@app.route("/api/clients", methods=["GET", "POST"])
@login_required
def api_clients():
    db = get_db()
    if request.method == "POST":
        data = request.json
        db.execute(
            "INSERT INTO clients (name, phone, email, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                data.get("name"),
                data.get("phone"),
                data.get("email"),
                data.get("status", "active"),
                datetime.now().isoformat()
            )
        )
        db.commit()
        return jsonify({"ok": True})

    rows = db.execute("SELECT * FROM clients").fetchall()
    return jsonify([dict(r) for r in rows])


# ======================
# API — CASES
# ======================

@app.route("/api/cases", methods=["GET", "POST"])
@login_required
def api_cases():
    db = get_db()
    if request.method == "POST":
        data = request.json
        db.execute("""
            INSERT INTO cases
            (client_id, case_number, court, case_type, stage, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data["client_id"],
            data["case_number"],
            data.get("court"),
            data.get("case_type"),
            data.get("stage"),
            data.get("notes"),
            datetime.now().isoformat()
        ))
        db.commit()
        return jsonify({"ok": True})

    rows = db.execute("SELECT * FROM cases").fetchall()
    return jsonify([dict(r) for r in rows])


# ======================
# API — SERVICES
# ======================

@app.route("/api/services", methods=["GET", "POST"])
@login_required
def api_services():
    db = get_db()
    if request.method == "POST":
        data = request.json
        db.execute(
            "INSERT INTO services (name, price) VALUES (?, ?)",
            (data["name"], data.get("price", 0))
        )
        db.commit()
        return jsonify({"ok": True})

    rows = db.execute("SELECT * FROM services").fetchall()
    return jsonify([dict(r) for r in rows])


# ======================
# API — PAYMENTS
# ======================

@app.route("/api/payments", methods=["GET", "POST"])
@login_required
def api_payments():
    db = get_db()
    if request.method == "POST":
        data = request.json
        db.execute(
            "INSERT INTO payments (client_id, amount, date, description) VALUES (?, ?, ?, ?)",
            (
                data["client_id"],
                data["amount"],
                data.get("date", datetime.now().isoformat()),
                data.get("description")
            )
        )
        db.commit()
        return jsonify({"ok": True})

    rows = db.execute("SELECT * FROM payments").fetchall()
    return jsonify([dict(r) for r in rows])


# ======================
# API — ACTIVITIES
# ======================

@app.route("/api/activities", methods=["GET", "POST"])
@login_required
def api_activities():
    db = get_db()
    if request.method == "POST":
        data = request.json
        db.execute(
            "INSERT INTO activities (title, date, description) VALUES (?, ?, ?)",
            (data["title"], data["date"], data.get("description"))
        )
        db.commit()
        return jsonify({"ok": True})

    rows = db.execute("SELECT * FROM activities").fetchall()
    return jsonify([dict(r) for r in rows])


# ======================
# API — SYNC
# ======================

@app.route("/api/sync/status")
@login_required
def sync_status():
    row = get_db().execute(
        "SELECT * FROM sync_state WHERE id = 1"
    ).fetchone()
    return jsonify({
        "enabled": bool(row["enabled"]),
        "last_sync": row["last_sync"]
    })


@app.route("/api/sync/upload", methods=["POST"])
@login_required
def api_sync_upload():
    yd = YandexDisk(YANDEX_TOKEN)
    backup_name = yd.upload_backup(DATABASE)

    db = get_db()
    db.execute(
        "UPDATE sync_state SET enabled = 1, last_sync = ? WHERE id = 1",
        (datetime.now().isoformat(),)
    )
    db.commit()

    return jsonify({"backup": backup_name})


# ======================
# RUN
# ======================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
