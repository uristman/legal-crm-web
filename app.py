from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import requests
from datetime import datetime

# Конфигурация Flask
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key')
DATABASE_NAME = 'legal_crm.db'

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(user_data[0], user_data[1], user_data[2])
    return None

# Работа с БД
def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Роуты
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user_data = cursor.fetchone()
            if user_data and check_password_hash(user_data['password'], password):
                user = User(user_data['id'], user_data['username'], user_data['password'])
                login_user(user)
                return redirect(url_for('index'))
            flash('Неверные данные для входа')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Восстановление базы данных (синхронизация с Яндекс.Диском)
def upload_to_yandex(file_path):
    """Загрузка файла на Яндекс.Диск"""
    token = os.getenv('YANDEX_TOKEN')  # App Password из переменных окружения
    url = f'https://cloud-api.yandex.net/v1/disk/resources/upload'
    headers = {'Authorization': f'OAuth {token}'}
    params = {'path': f'/legal_crm/{file_path}', 'overwrite': 'true'}
    
    response = requests.get(url, headers=headers, params=params).json()
    upload_url = response.get('href')
    
    if upload_url:
        with open(file_path, 'rb') as f:
            requests.put(upload_url, files={'file': f})
        return True
    return False

@app.route('/api/sync/upload', methods=['POST'])
@login_required
def upload_backup():
    """Резервное копирование на Яндекс.Диск"""
    try:
        success = upload_to_yandex(DATABASE_NAME)
        if success:
            return jsonify({'success': True, 'message': 'Резервная копия успешно загружена на Яндекс.Диск!'})
        return jsonify({'success': False, 'error': 'Не удалось загрузить резервную копию.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Создание пользователей и таблиц
def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                client_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
            )
        """)
        conn.commit()

# Основной запуск
if __name__ == '__main__':
    init_db()  # Инициализация базы данных
    app.run(debug=True)
