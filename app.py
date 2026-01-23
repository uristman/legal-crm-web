from flask import Flask, render_template, request, jsonify, redirect
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, UserMixin, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime

DATABASE = "legal_crm.db"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

# =====================
# DATABASE
# =====================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                status TEXT,
                address TEXT,
                passport TEXT,
                inn TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                client_id INTEGER NOT NULL,
                case_number TEXT NOT NULL,
                court TEXT,
                case_type TEXT,
                plaintiff TEXT,
                defendant TEXT,
                claim_amount TEXT,
                stage TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ("admin", generate_password_hash("12345"))
            )

        conn.commit()

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
    with get_db() as conn:
        cur = conn.cursor()
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
@login_required
def logout():
    logout_user()
    return redirect("/login")

# =====================
# AUTH API
# =====================

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json()
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (data.get("username"),))
        user = cur.fetchone()

    if not user or not check_password_hash(user["password"], data.get("password")):
        return jsonify(success=False)

    login_user(User(user))
    return jsonify(success=True)

@app.route("/api/auth/check")
def api_auth_check():
    return jsonify(authenticated=current_user.is_authenticated)

@app.route("/api/auth/logout", methods=["POST"])
@login_required
def api_auth_logout():
    logout_user()
    return jsonify(success=True)

# =====================
# CLIENTS API
# =====================

@app.route("/api/clients", methods=["GET", "POST"])
@login_required
def api_clients():
    with get_db() as conn:
        cur = conn.cursor()

        if request.method == "POST":
            data = request.get_json()
            cur.execute("""
                INSERT INTO clients
                (user_id, full_name, phone, email, status, address, passport, inn, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                current_user.id,
                data.get("full_name"),
                data.get("phone"),
                data.get("email"),
                data.get("status"),
                data.get("address"),
                data.get("passport"),
                data.get("inn"),
                data.get("notes")
            ))
            conn.commit()

        cur.execute("""
            SELECT id, full_name, phone, email, status, created_at
            FROM clients
            WHERE user_id=?
            ORDER BY created_at DESC
        """, (current_user.id,))

        return jsonify(success=True, clients=[dict(r) for r in cur.fetchall()])

# =====================
# CASES API (ИСПРАВЛЕНО)
# =====================

@app.route("/api/cases", methods=["GET", "POST"])
@login_required
def api_cases():
    with get_db() as conn:
        cur = conn.cursor()

        if request.method == "POST":
            data = request.get_json()

            # 🔐 защита от пустого номера дела
            case_number = (
                data.get("case_number")
                or data.get("number")
                or f"Дело {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            cur.execute("""
                INSERT INTO cases
                (user_id, client_id, case_number, court, case_type,
                 plaintiff, defendant, claim_amount, stage, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                current_user.id,
                data.get("client_id"),
                case_number,
                data.get("court"),
                data.get("case_type"),
                data.get("plaintiff"),
                data.get("defendant"),
                data.get("claim_amount"),
                data.get("stage"),
                data.get("notes")
            ))
            conn.commit()

        cur.execute("""
            SELECT c.id, c.case_number, c.court, c.stage,
                   cl.full_name AS client_name, c.created_at
            FROM cases c
            JOIN clients cl ON cl.id = c.client_id
            WHERE c.user_id=?
            ORDER BY c.created_at DESC
        """, (current_user.id,))

        return jsonify(success=True, cases=[dict(r) for r in cur.fetchall()])

# =====================
# STUB API
# =====================

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
    return jsonify(success=True, connected=False, last_sync=None, backups=0)

@app.route("/api/sync/backups")
@login_required
def api_sync_backups():
    return jsonify(success=True, backups=[])

@app.route("/api/sync/upload", methods=["POST"])
@login_required
def api_sync_upload():
    return jsonify(success=True)
