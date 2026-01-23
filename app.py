import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, redirect, url_for, render_template
from flask_login import (
    LoginManager, UserMixin,
    login_user, login_required,
    logout_user, current_user
)
from flask_cors import CORS
import requests

# ======================
# APP CONFIG
# ======================

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")
CORS(app, supports_credentials=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

DB_PATH = "database.db"

# ======================
# USER MODEL
# ======================

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

USERS = {
    "admin": {
        "id": 1,
        "username": "admin",
        "password": "admin"
    }
}

@login_manager.user_loader
def load_user(user_id):
    for u in USERS.values():
        if str(u["id"]) == str(user_id):
            return User(u["id"], u["username"])
    return None

# ======================
# DATABASE
# ======================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ======================
# ROUTES (PAGES)
# ======================

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/")
@login_required
def index():
    return render_template("index.html")

# ======================
# AUTH API
# ======================

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")

    user = USERS.get(username)

    if not user or user["password"] != password:
        return jsonify({"error": "Invalid credentials"}), 401

    login_user(User(user["id"], user["username"]))
    return jsonify({"success": True})

@app.route("/api/auth/check")
def api_auth_check():
    if current_user.is_authenticated:
        return jsonify({"authenticated": True})
    return jsonify({"authenticated": False}), 401

@app.route("/api/auth/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"success": True})

# ======================
# CORE API (STUBS)
# ======================

def ok(data=None):
    return jsonify(data if data is not None else [])

@app.route("/api/clients", methods=["GET", "POST"])
@login_required
def api_clients():
    if request.method == "POST":
        return ok({"status": "saved"})
    return ok([])

@app.route("/api/cases", methods=["GET", "POST"])
@login_required
def api_cases():
    if request.method == "POST":
        return ok({"status": "saved"})
    return ok([])

@app.route("/api/services", methods=["GET", "POST"])
@login_required
def api_services():
    return ok([])

@app.route("/api/payments", methods=["GET", "POST"])
@login_required
def api_payments():
    return ok([])

@app.route("/api/activities", methods=["GET", "POST"])
@login_required
def api_activities():
    return ok([])

@app.route("/api/stats")
@login_required
def api_stats():
    return ok({})

# ======================
# YANDEX DISK (STATUS ONLY)
# ======================

YANDEX_TOKEN = os.environ.get("YANDEX_TOKEN")

@app.route("/api/sync/status")
@login_required
def sync_status():
    if YANDEX_TOKEN:
        return jsonify({
            "configured": True,
            "last_sync": "ok",
            "backups": 1
        })
    return jsonify({
        "configured": False,
        "last_sync": None,
        "backups": 0
    })

@app.route("/api/sync/upload", methods=["POST"])
@login_required
def sync_upload():
    return jsonify({"success": True})

@app.route("/api/sync/backups")
@login_required
def sync_backups():
    return jsonify([])

# ======================
# RUN
# ======================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
