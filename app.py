import os
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, request, session, redirect, render_template
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# ======================
# CONFIG
# ======================

APP_SECRET = os.environ.get("SECRET_KEY", "dev-secret")
DATABASE = "database.db"

app = Flask(__name__)
app.secret_key = APP_SECRET
CORS(app, supports_credentials=True)

# ======================
# DATABASE
# ======================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()

    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT
    );

    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY,
        name TEXT,
        phone TEXT
    );

    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY,
        title TEXT,
        client_id INTEGER
    );

    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY,
        name TEXT,
        price REAL
    );

    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY,
        client_id INTEGER,
        amount REAL,
        date TEXT
    );

    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY,
        title TEXT,
        date TEXT
    );

    CREATE TABLE IF NOT EXISTS sync_state (
        id INTEGER PRIMARY KEY,
        configured INTEGER,
        last_sync TEXT
    );
    """)

    # admin user
    cur = db.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        db.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", generate_password_hash("admin"))
        )

    # sync state
    cur = db.execute("SELECT * FROM sync_state")
    if not cur.fetchone():
        db.execute(
            "INSERT INTO sync_state (configured, last_sync) VALUES (0, NULL)"
        )

    db.commit()

init_db()

# ======================
# AUTH
# ======================

def require_auth():
    if not session.get("user"):
        return False
    return True

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.json
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username=?",
        (data["username"],)
    ).fetchone()

    if not user or not check_password_hash(user["password"], data["password"]):
        return jsonify({"error": "invalid"}), 401

    session["user"] = user["username"]
    return jsonify({"ok": True})

@app.route("/api/auth/check")
def api_auth_check():
    if not require_auth():
        return jsonify({"auth": False}), 401
    return jsonify({"auth": True})

@app.route("/api/auth/logout")
def api_logout():
    session.clear()
    return jsonify({"ok": True})

# ======================
# MAIN PAGE
# ======================

@app.route("/")
def index():
    if not require_auth():
        return redirect("/login")
    return render_template("index.html")

# ======================
# API — CLIENTS / CASES
# ======================

@app.route("/api/clients", methods=["GET", "POST"])
def api_clients():
    if not require_auth():
        return jsonify([])

    db = get_db()
    if request.method == "POST":
        d = request.json
        db.execute("INSERT INTO clients (name, phone) VALUES (?,?)",
                   (d["name"], d["phone"]))
        db.commit()
    rows = db.execute("SELECT * FROM clients").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/cases", methods=["GET", "POST"])
def api_cases():
    if not require_auth():
        return jsonify([])

    db = get_db()
    if request.method == "POST":
        d = request.json
        db.execute("INSERT INTO cases (title, client_id) VALUES (?,?)",
                   (d["title"], d["client_id"]))
        db.commit()
    rows = db.execute("SELECT * FROM cases").fetchall()
    return jsonify([dict(r) for r in rows])

# ======================
# API — SERVICES
# ======================

@app.route("/api/services", methods=["GET", "POST"])
def api_services():
    if not require_auth():
        return jsonify([])

    db = get_db()
    if request.method == "POST":
        d = request.json
        db.execute("INSERT INTO services (name, price) VALUES (?,?)",
                   (d["name"], d["price"]))
        db.commit()
    rows = db.execute("SELECT * FROM services").fetchall()
    return jsonify([dict(r) for r in rows])

# ======================
# API — PAYMENTS
# ======================

@app.route("/api/payments", methods=["GET", "POST"])
def api_payments():
    if not require_auth():
        return jsonify([])

    db = get_db()
    if request.method == "POST":
        d = request.json
        db.execute(
            "INSERT INTO payments (client_id, amount, date) VALUES (?,?,?)",
            (d["client_id"], d["amount"], d["date"])
        )
        db.commit()
    rows = db.execute("SELECT * FROM payments").fetchall()
    return jsonify([dict(r) for r in rows])

# ======================
# API — ACTIVITIES
# ======================

@app.route("/api/activities", methods=["GET", "POST"])
def api_activities():
    if not require_auth():
        return jsonify([])

    db = get_db()
    if request.method == "POST":
        d = request.json
        db.execute(
            "INSERT INTO activities (title, date) VALUES (?,?)",
            (d["title"], d["date"])
        )
        db.commit()
    rows = db.execute("SELECT * FROM activities").fetchall()
    return jsonify([dict(r) for r in rows])

# ======================
# API — STATS
# ======================

@app.route("/api/stats")
def api_stats():
    if not require_auth():
        return jsonify({})

    db = get_db()
    return jsonify({
        "clients": db.execute("SELECT COUNT(*) FROM clients").fetchone()[0],
        "cases": db.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
        "income": db.execute("SELECT IFNULL(SUM(amount),0) FROM payments").fetchone()[0]
    })

# ======================
# API — SYNC
# ======================

@app.route("/api/sync/status")
def api_sync_status():
    db = get_db()
    row = db.execute("SELECT * FROM sync_state").fetchone()
    return jsonify({
        "configured": bool(row["configured"]),
        "last_sync": row["last_sync"]
    })

@app.route("/api/sync/upload", methods=["POST"])
def api_sync_upload():
    db = get_db()
    db.execute(
        "UPDATE sync_state SET configured=1, last_sync=?",
        (datetime.now().isoformat(),)
    )
    db.commit()
    return jsonify({"ok": True})

@app.route("/api/sync/backups")
def api_sync_backups():
    return jsonify([])

# ======================
# RUN
# ======================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
