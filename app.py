from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    UserMixin,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

# =====================
# CONFIG
# =====================

DATABASE_NAME = "legal_crm.db"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

# =====================
# LOGIN MANAGER
# =====================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# =====================
# DATABASE
# =====================

def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cur = conn.cursor()

        # users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)

        # clients
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # cases
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                client_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # demo admin
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ("admin", generate_password_hash("12345"))
            )

        conn.commit()

# =====================
# USER MODEL
# =====================

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, password FROM users WHERE id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        if row:
            return User(row["id"], row["username"], row["password"])
    return None

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
    return redirect(url_for("login"))

# =====================
# AUTH API (ВАЖНО)
# =====================

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "Нет данных"})

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "error": "Логин и пароль обязательны"})

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, username, password FROM users WHERE username = ?",
            (username,)
        )
        user = cur.fetchone()

    if not user or not check_password_hash(user["password"], password):
        return jsonify({"success": False, "error": "Неверный логин или пароль"})

    login_user(User(user["id"], user["username"], user["password"]))
    return jsonify({"success": True})

@app.route("/api/auth/check", methods=["GET"])
def api_auth_check():
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username
            }
        })
    return jsonify({"authenticated": False})

@app.route("/api/auth/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"success": True})

# =====================
# CLIENTS API (МИНИМУМ)
# =====================

@app.route("/api/clients", methods=["GET"])
@login_required
def get_clients():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM clients WHERE user_id = ? ORDER BY created_at DESC",
            (current_user.id,)
        )
        clients = [dict(row) for row in cur.fetchall()]
    return jsonify({"success": True, "clients": clients})

# =====================
# MAIN
# =====================

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
