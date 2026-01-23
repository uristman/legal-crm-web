import os
import sqlite3
from datetime import datetime
from flask import (
    Flask, jsonify, request, session,
    redirect, render_template
)
from flask_cors import CORS

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
# APP
# ======================

app = Flask(__name__, static_folder="static", template_folder="templates")

# 🔐 КРИТИЧЕСКИ ВАЖНО ДЛЯ RENDER + HTTPS
app.secret_key = "legal-crm-secret-key"
app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True,
)

CORS(app, supports_credentials=True)

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

def auth_required(fn):
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


@app.route("/api/auth/check")
def auth_check():
    if session.get("user"):
        return jsonify({"authenticated": True})
    return jsonify({"authenticated": False}), 401


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    row = get_db().execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    ).fetchone()

    if not row:
        return jsonify({"error": "invalid"}), 401

    session["user"] = username

    # 👇 КЛЮЧЕВОЕ ИЗМЕНЕНИЕ
    return jsonify({"ok": True, "redirect": "/"})

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


# ======================
# UI
# ======================

@app.route("/login")
def login():
    if session.get("user"):
        return redirect("/")
    return render_template("login.html")


@app.route("/")
def index():
    if not session.get("user"):
        return redirect("/login")
    return render_template("index.html")


# ======================
# API — CLIENTS
# ======================

@app.route("/api/clients", methods=["GET", "POST"])
@auth_required
def api_clients():
    db = get_db()
    if request.method == "POST":
        data = request.json
        db.execute(
            "INSERT INTO clients (name, phone, email, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                data["name"],
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
@auth_required
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
# SYNC
# ======================

@app.route("/api/sync/status")
@auth_required
def sync_status():
    row = get_db().execute(
        "SELECT * FROM sync_state WHERE id=1"
    ).fetchone()

    return jsonify({
        "enabled": bool(row["enabled"]),
        "last_sync": row["last_sync"]
    })


@app.route("/api/sync/upload", methods=["POST"])
@auth_required
def sync_upload():
    yd = YandexDisk(YANDEX_TOKEN)
    name = yd.upload_backup(DATABASE)

    db = get_db()
    db.execute(
        "UPDATE sync_state SET enabled=1, last_sync=? WHERE id=1",
        (datetime.now().isoformat(),)
    )
    db.commit()

    return jsonify({"backup": name})


# ======================
# RUN
# ======================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
