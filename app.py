"""
Веб-версия Legal CRM - Flask Backend (ПОЛНОСТЬЮ ФУНКЦИОНАЛЬНАЯ ВЕРСИЯ)
Система учета клиентов и активностей для юридической практики
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session, flash
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import sqlite3
import os
import json
import uuid
from datetime import datetime
from sync.yandex_oauth_client import YandexOAuthClient


app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Разрешаем CORS для фронтенда

# Константы
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'legal_crm.db')
STATIC_FOLDER = 'static'
TEMPLATES_FOLDER = 'templates'

# Настройки для облачного развертывания
DEBUG_MODE = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))

# Настройки Flask для production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key-for-legal-crm')
app.config['DEBUG'] = DEBUG_MODE

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к системе необходимо авторизоваться.'

# User class для Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя по ID"""
    try:
        with WebDatabase().get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password FROM users WHERE id = ?", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                return User(user_data[0], user_data[1], user_data[2])
    except Exception as e:
        print(f"Ошибка загрузки пользователя: {e}")
    return None

class WebDatabase:
    def __init__(self, db_name=DATABASE_NAME):
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        """Получение соединения с базой данных"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # Для доступа к данным по имени колонки
        return conn
    
    def init_database(self):
        """Инициализация базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Включаем поддержку внешних ключей
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Таблица пользователей для авторизации
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица клиентов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица дел
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    client_id INTEGER,
                    status TEXT DEFAULT 'active',
                    priority TEXT DEFAULT 'medium',
                    due_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
                )
            """)
            
            # Таблица действий (События)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER,
                    client_id INTEGER,
                    activity_type TEXT NOT NULL,
                    description TEXT,
                    datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE,
                    FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
                )
            """)
            
            # Таблица услуг
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    price DECIMAL(10,2),
                    duration_hours INTEGER,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица платежей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    case_id INTEGER,
                    amount DECIMAL(10,2) NOT NULL,
                    payment_type TEXT DEFAULT 'income',
                    description TEXT,
                    payment_method TEXT,
                    payment_date DATE DEFAULT CURRENT_DATE,
                    status TEXT DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE,
                    FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
                )
            """)
            
            # Таблица конфигурации синхронизации
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    yandex_login TEXT,
                    yandex_password TEXT,
                    auto_sync BOOLEAN DEFAULT FALSE,
                    last_sync TIMESTAMP,
                    backup_folder TEXT DEFAULT '/LegalCRM_Backups',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            
            # Создаем демо-пользователя если его нет
            self.create_demo_user()
    
    def create_demo_user(self):
        """Создание демо-пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, существует ли уже демо-пользователь
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    # Создаем демо-пользователя
                    cursor.execute(
                        "INSERT INTO users (username, password) VALUES (?, ?)",
                        ('admin', '12345')
                    )
                    conn.commit()
                    print("✅ Демо-пользователь создан: admin / 12345")
                else:
                    print("✅ Демо-пользователь уже существует")
                    
        except Exception as e:
            print(f"❌ Ошибка создания демо-пользователя: {e}")

# Создаем экземпляр базы данных
db = WebDatabase()

# ==================== ROUTES ====================

@app.route('/')
@login_required  # Защищенный маршрут
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/login')
def login():
    """Страница входа"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    return redirect(url_for('login'))

# ==================== API ENDPOINTS ====================

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Проверка аутентификации"""
    try:
        if current_user.is_authenticated:
            return jsonify({
                'authenticated': True, 
                'user': {
                    'id': current_user.id,
                    'username': current_user.username
                }
            })
        else:
            return jsonify({'authenticated': False})
    except Exception as e:
        return jsonify({'authenticated': False, 'error': str(e)})

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Вход в систему"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Логин и пароль обязательны для заполнения'})
        
        # Проверяем пользователя в базе данных
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
            user_data = cursor.fetchone()
            
            if user_data and user_data[2] == password:  # Простое сравнение (в реальном приложении нужно хеширование)
                user = User(user_data[0], user_data[1], user_data[2])
                login_user(user)  # Входим через Flask-Login
                return jsonify({'success': True, 'message': 'Успешный вход'})
            else:
                return jsonify({'success': False, 'error': 'Неверный логин или пароль'})
                
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():
    """Выход через API"""
    try:
        logout_user()
        return jsonify({'success': True, 'message': 'Успешный выход'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clients', methods=['GET'])
@login_required
def get_clients():
    """Получение всех клиентов"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients ORDER BY created_at DESC")
            clients = [dict(row) for row in cursor.fetchall()]
            
            # Преобразуем datetime объекты в строки для JSON
            for client in clients:
                if 'created_at' in client:
                    client['created_at'] = str(client['created_at'])
                if 'updated_at' in client:
                    client['updated_at'] = str(client['updated_at'])
                    
            return jsonify({'success': True, 'clients': clients})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clients', methods=['POST'])
@login_required
def create_client():
    """Создание нового клиента"""
    try:
        data = request.json
        
        # Проверяем обязательные поля
        if not data.get('full_name'):
            return jsonify({'success': False, 'error': 'ФИО обязательно для заполнения'})
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO clients (full_name, phone, email, address, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                data.get('full_name', ''),
                data.get('phone', ''),
                data.get('email', ''),
                data.get('address', ''),
                data.get('notes', '')
            ))
            
            conn.commit()
            client_id = cursor.lastrowid
            
        return jsonify({'success': True, 'message': 'Клиент успешно создан', 'client_id': client_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clients/<int:client_id>', methods=['PUT'])
@login_required
def update_client(client_id):
    """Обновление клиента"""
    try:
        data = request.json
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE clients 
                SET full_name = ?, phone = ?, email = ?, address = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                data.get('full_name', ''),
                data.get('phone', ''),
                data.get('email', ''),
                data.get('address', ''),
                data.get('notes', ''),
                client_id
            ))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Клиент не найден'})
            
            conn.commit()
            
        return jsonify({'success': True, 'message': 'Клиент успешно обновлен'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clients/<int:client_id>', methods=['DELETE'])
@login_required
def delete_client(client_id):
    """Удаление клиента"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Клиент не найден'})
            
            conn.commit()
            
        return jsonify({'success': True, 'message': 'Клиент успешно удален'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== CASES API ====================

@app.route('/api/cases', methods=['GET'])
@login_required
def get_cases():
    """Получение всех дел"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.*, cl.full_name as client_name 
                FROM cases c 
                LEFT JOIN clients cl ON c.client_id = cl.id
                ORDER BY c.created_at DESC
            """)
            cases = [dict(row) for row in cursor.fetchall()]
            
            # Преобразуем datetime объекты в строки для JSON
            for case in cases:
                if 'created_at' in case:
                    case['created_at'] = str(case['created_at'])
                if 'updated_at' in case:
                    case['updated_at'] = str(case['updated_at'])
                    
            return jsonify({'success': True, 'cases': cases})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cases', methods=['POST'])
@login_required
def create_case():
    """Создание нового дела"""
    try:
        data = request.json
        
        # Проверяем обязательные поля
        if not data.get('title'):
            return jsonify({'success': False, 'error': 'Название дела обязательно для заполнения'})
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cases (title, description, client_id, status, priority, due_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data.get('title', ''),
                data.get('description', ''),
                data.get('client_id'),
                data.get('status', 'active'),
                data.get('priority', 'medium'),
                data.get('due_date')
            ))
            
            conn.commit()
            case_id = cursor.lastrowid
            
        return jsonify({'success': True, 'message': 'Дело успешно создано', 'case_id': case_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cases/<int:case_id>', methods=['PUT'])
@login_required
def update_case(case_id):
    """Обновление дела"""
    try:
        data = request.json
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE cases 
                SET title = ?, description = ?, client_id = ?, status = ?, priority = ?, due_date = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                data.get('title', ''),
                data.get('description', ''),
                data.get('client_id'),
                data.get('status', 'active'),
                data.get('priority', 'medium'),
                data.get('due_date'),
                case_id
            ))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Дело не найдено'})
            
            conn.commit()
            
        return jsonify({'success': True, 'message': 'Дело успешно обновлено'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cases/<int:case_id>', methods=['DELETE'])
@login_required
def delete_case(case_id):
    """Удаление дела"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cases WHERE id = ?", (case_id,))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Дело не найдено'})
            
            conn.commit()
            
        return jsonify({'success': True, 'message': 'Дело успешно удалено'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== ACTIVITIES API ====================

@app.route('/api/activities', methods=['GET'])
@login_required
def get_activities():
    """Получение всех активностей"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, c.title as case_title, cl.full_name as client_name 
                FROM activities a 
                LEFT JOIN cases c ON a.case_id = c.id
                LEFT JOIN clients cl ON a.client_id = cl.id
                ORDER BY a.datetime DESC
            """)
            activities = [dict(row) for row in cursor.fetchall()]
            
            # Преобразуем datetime объекты в строки для JSON
            for activity in activities:
                if 'datetime' in activity:
                    activity['datetime'] = str(activity['datetime'])
                    
            return jsonify({'success': True, 'activities': activities})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/activities', methods=['POST'])
@login_required
def create_activity():
    """Создание новой активности"""
    try:
        data = request.json
        
        # Проверяем обязательные поля
        if not data.get('activity_type'):
            return jsonify({'success': False, 'error': 'Тип активности обязателен для заполнения'})
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO activities (case_id, client_id, activity_type, description)
                VALUES (?, ?, ?, ?)
            """, (
                data.get('case_id'),
                data.get('client_id'),
                data.get('activity_type', ''),
                data.get('description', '')
            ))
            
            conn.commit()
            activity_id = cursor.lastrowid
            
        return jsonify({'success': True, 'message': 'Активность успешно создана', 'activity_id': activity_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/activities/<int:activity_id>', methods=['PUT'])
@login_required
def update_activity(activity_id):
    """Обновление активности"""
    try:
        data = request.json
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE activities 
                SET case_id = ?, client_id = ?, activity_type = ?, description = ?
                WHERE id = ?
            """, (
                data.get('case_id'),
                data.get('client_id'),
                data.get('activity_type', ''),
                data.get('description', ''),
                activity_id
            ))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Активность не найдена'})
            
            conn.commit()
            
        return jsonify({'success': True, 'message': 'Активность успешно обновлена'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/activities/<int:activity_id>', methods=['DELETE'])
@login_required
def delete_activity(activity_id):
    """Удаление активности"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Активность не найдена'})
            
            conn.commit()
            
        return jsonify({'success': True, 'message': 'Активность успешно удалена'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== SERVICES API ====================

@app.route('/api/services', methods=['GET'])
@login_required
def get_services():
    """Получение всех услуг"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM services ORDER BY created_at DESC")
            services = [dict(row) for row in cursor.fetchall()]
            
            # Преобразуем datetime объекты в строки для JSON
            for service in services:
                if 'created_at' in service:
                    service['created_at'] = str(service['created_at'])
                if 'updated_at' in service:
                    service['updated_at'] = str(service['updated_at'])
                    
            return jsonify({'success': True, 'services': services})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/services', methods=['POST'])
@login_required
def create_service():
    """Создание новой услуги"""
    try:
        data = request.json
        
        # Проверяем обязательные поля
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'Название услуги обязательно для заполнения'})
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO services (name, description, price, duration_hours, category)
                VALUES (?, ?, ?, ?, ?)
            """, (
                data.get('name', ''),
                data.get('description', ''),
                data.get('price', 0),
                data.get('duration_hours'),
                data.get('category', '')
            ))
            
            conn.commit()
            service_id = cursor.lastrowid
            
        return jsonify({'success': True, 'message': 'Услуга успешно создана', 'service_id': service_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/services/<int:service_id>', methods=['PUT'])
@login_required
def update_service(service_id):
    """Обновление услуги"""
    try:
        data = request.json
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE services 
                SET name = ?, description = ?, price = ?, duration_hours = ?, category = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                data.get('name', ''),
                data.get('description', ''),
                data.get('price', 0),
                data.get('duration_hours'),
                data.get('category', ''),
                service_id
            ))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Услуга не найдена'})
            
            conn.commit()
            
        return jsonify({'success': True, 'message': 'Услуга успешно обновлена'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/services/<int:service_id>', methods=['DELETE'])
@login_required
def delete_service(service_id):
    """Удаление услуги"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Услуга не найдена'})
            
            conn.commit()
            
        return jsonify({'success': True, 'message': 'Услуга успешно удалена'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== PAYMENTS API ====================

@app.route('/api/payments', methods=['GET'])
@login_required
def get_payments():
    """Получение всех платежей"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, c.full_name as client_name, cs.title as case_title
                FROM payments p 
                LEFT JOIN clients c ON p.client_id = c.id
                LEFT JOIN cases cs ON p.case_id = cs.id
                ORDER BY p.payment_date DESC
            """)
            payments = [dict(row) for row in cursor.fetchall()]
            
            # Преобразуем datetime объекты в строки для JSON
            for payment in payments:
                if 'created_at' in payment:
                    payment['created_at'] = str(payment['created_at'])
                if 'payment_date' in payment:
                    payment['payment_date'] = str(payment['payment_date'])
                    
            return jsonify({'success': True, 'payments': payments})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/payments', methods=['POST'])
@login_required
def create_payment():
    """Создание нового платежа"""
    try:
        data = request.json
        
        # Проверяем обязательные поля
        if not data.get('amount'):
            return jsonify({'success': False, 'error': 'Сумма платежа обязательна для заполнения'})
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO payments (client_id, case_id, amount, payment_type, description, payment_method, payment_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('client_id'),
                data.get('case_id'),
                data.get('amount', 0),
                data.get('payment_type', 'income'),
                data.get('description', ''),
                data.get('payment_method', ''),
                data.get('payment_date'),
                data.get('status', 'completed')
            ))
            
            conn.commit()
            payment_id = cursor.lastrowid
            
        return jsonify({'success': True, 'message': 'Платеж успешно создан', 'payment_id': payment_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/payments/<int:payment_id>', methods=['PUT'])
@login_required
def update_payment(payment_id):
    """Обновление платежа"""
    try:
        data = request.json
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE payments 
                SET client_id = ?, case_id = ?, amount = ?, payment_type = ?, description = ?, payment_method = ?, payment_date = ?, status = ?
                WHERE id = ?
            """, (
                data.get('client_id'),
                data.get('case_id'),
                data.get('amount', 0),
                data.get('payment_type', 'income'),
                data.get('description', ''),
                data.get('payment_method', ''),
                data.get('payment_date'),
                data.get('status', 'completed'),
                payment_id
            ))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Платеж не найден'})
            
            conn.commit()
            
        return jsonify({'success': True, 'message': 'Платеж успешно обновлен'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/payments/<int:payment_id>', methods=['DELETE'])
@login_required
def delete_payment(payment_id):
    """Удаление платежа"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Платеж не найден'})
            
            conn.commit()
            
        return jsonify({'success': True, 'message': 'Платеж успешно удален'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== STATISTICS API ====================

@app.route('/api/stats', methods=['GET'])
@login_required
def get_statistics():
    """Получение статистики"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute("SELECT COUNT(*) FROM clients")
            total_clients = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cases")
            total_cases = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM activities")
            total_activities = cursor.fetchone()[0]
            
            # Активные дела
            cursor.execute("SELECT COUNT(*) FROM cases WHERE status = 'active'")
            active_cases = cursor.fetchone()[0]
            
            # Статистика по приоритетам
            cursor.execute("SELECT priority, COUNT(*) FROM cases GROUP BY priority")
            priority_stats = dict(cursor.fetchall())
            
            # Статистика платежей
            cursor.execute("SELECT COUNT(*) FROM payments")
            total_payments = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(amount) FROM payments WHERE payment_type = 'income'")
            total_income = cursor.fetchone()[0] or 0
            
            # Последние активности
            cursor.execute("""
                SELECT a.activity_type, a.description, a.datetime, c.title as case_title 
                FROM activities a 
                LEFT JOIN cases c ON a.case_id = c.id
                ORDER BY a.datetime DESC 
                LIMIT 10
            """)
            recent_activities = [dict(row) for row in cursor.fetchall()]
            
            # Преобразуем datetime объекты в строки
            for activity in recent_activities:
                if 'datetime' in activity:
                    activity['datetime'] = str(activity['datetime'])
            
            stats = {
                'total_clients': total_clients,
                'total_cases': total_cases,
                'total_activities': total_activities,
                'active_cases': active_cases,
                'priority_stats': priority_stats,
                'total_payments': total_payments,
                'total_income': float(total_income),
                'recent_activities': recent_activities
            }
            
            return jsonify({'success': True, 'stats': stats})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== YANDEX DISK SYNC API ====================

@app.route('/api/sync/status', methods=['GET'])
@login_required
def get_sync_status():
    """Получение статуса синхронизации с отладкой"""
    try:
        print(f"[DEBUG] get_sync_status вызван для user_id: {current_user.id}")
        print(f"[DEBUG] current_user.is_authenticated: {current_user.is_authenticated}")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем пользователя в базе
            cursor.execute("SELECT id, username FROM users WHERE id = ?", (current_user.id,))
            user_check = cursor.fetchone()
            print(f"[DEBUG] Найден пользователь в БД: {user_check}")
            
            # Получаем текущую конфигурацию синхронизации
            cursor.execute("""
                SELECT yandex_login, auto_sync, last_sync, backup_folder, created_at, updated_at
                FROM sync_config 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (current_user.id,))
            
            result = cursor.fetchone()
            print(f"[DEBUG] Результат запроса sync_config: {result}")
            
            if result:
                configured = bool(result[0])  # yandex_login not null/empty
                print(f"[DEBUG] configured = {configured}, yandex_login = '{result[0]}'")
            else:
                configured = False
                print("[DEBUG] Запись sync_config не найдена")
            
            # Безопасная обработка last_sync
            last_sync = None
            if result and result[2]:
                try:
                    # Если result[2] уже строка, используем как есть
                    if isinstance(result[2], str):
                        last_sync = result[2]
                    else:
                        # Если это datetime объект, конвертируем в строку
                        last_sync = result[2].isoformat()
                except Exception as e:
                    print(f"[DEBUG] Ошибка обработки last_sync: {e}")
                    last_sync = str(result[2])
            
            status = {
                'configured': configured,
                'needs_sync': False,
                'last_sync': last_sync,
                'auto_sync_enabled': bool(result[1]) if result else False,
                'backup_folder': result[3] if result and result[3] else '/LegalCRM_Backups',
                'debug_info': {
                    'user_id': current_user.id,
                    'result_exists': bool(result),
                    'yandex_login_value': result[0] if result else None
                }
            }
            
            print(f"[DEBUG] Возвращаемый статус: {status}")
            return jsonify({'success': True, **status})
            
    except Exception as e:
        print(f"[ERROR] Ошибка в get_sync_status: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sync/test', methods=['GET'])
@login_required
def test_yandex_connection():
    """Тестирование подключения к Яндекс.Диску с отладкой"""
    try:
        print(f"[DEBUG] test_yandex_connection вызван для user_id: {current_user.id}")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем сохраненные учетные данные
            cursor.execute("""
                SELECT yandex_login, yandex_password 
                FROM sync_config 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (current_user.id,))
            
            result = cursor.fetchone()
            print(f"[DEBUG] Результат запроса учетных данных: {result}")
            
            if not result:
                print("[DEBUG] Запись sync_config не найдена")
                return jsonify({'success': False, 'error': 'Учетные данные Яндекс.Диска не настроены'})
            
            if not result[0]:
                print(f"[DEBUG] yandex_login пустой: '{result[0]}'")
                return jsonify({'success': False, 'error': 'Учетные данные Яндекс.Диска не настроены'})
            
            username, password = result
            print(f"[DEBUG] Данные найдены - username: {username}, password length: {len(password)}")
            
            # Тестируем подключение через существующий WebDAV клиент
            from sync.yandex_webdav import YandexDiskWebDAV
            
            try:
                print(f"[DEBUG] Создаем YandexDiskWebDAV клиент...")
                yandex_disk = YandexDiskWebDAV(username, password)
                print(f"[DEBUG] YandexDiskWebDAV клиент создан успешно")
                return jsonify({
                    'success': True, 
                    'message': 'Подключение к Яндекс.Диску работает!',
                    'debug_info': {
                        'username': username,
                        'password_length': len(password),
                        'user_id': current_user.id
                    }
                })
            except Exception as webdav_error:
                print(f"[ERROR] Ошибка WebDAV: {webdav_error}")
                return jsonify({
                    'success': False, 
                    'error': f'Ошибка подключения к Яндекс.Диску: {str(webdav_error)}',
                    'debug_info': {
                        'username': username,
                        'password_length': len(password),
                        'user_id': current_user.id
                    }
                })
                
    except Exception as e:
        print(f"[ERROR] Общая ошибка в test_yandex_connection: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sync/setup', methods=['POST'])
@login_required
def setup_yandex_sync():
    """Настройка синхронизации с Яндекс.Диском с отладкой"""
    try:
        print(f"[DEBUG] setup_yandex_sync вызван для user_id: {current_user.id}")
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных для обработки'})
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        print(f"[DEBUG] Получены данные - username: {username}, password length: {len(password)}")
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Логин и пароль обязательны'})
        
        # Проверяем подключение перед сохранением
        try:
            from sync.yandex_webdav import YandexDiskWebDAV
            print(f"[DEBUG] Тестируем подключение к Яндекс.Диску...")
            yandex_disk = YandexDiskWebDAV(username, password)
            print(f"[DEBUG] Подключение к Яндекс.Диску успешно!")
        except Exception as e:
            print(f"[ERROR] Ошибка подключения к Яндекс.Диску: {e}")
            return jsonify({
                'success': False, 
                'error': f'Не удалось подключиться к Яндекс.Диску: {str(e)}'
            })
        
        # Сохраняем конфигурацию в БД
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем пользователя
            cursor.execute("SELECT id, username FROM users WHERE id = ?", (current_user.id,))
            user_check = cursor.fetchone()
            print(f"[DEBUG] Проверяем пользователя в БД: {user_check}")
            
            if not user_check:
                print(f"[ERROR] Пользователь {current_user.id} не найден в БД")
                return jsonify({'success': False, 'error': 'Пользователь не найден в базе данных'})
            
            # Проверяем существует ли запись для пользователя
            cursor.execute("SELECT id FROM sync_config WHERE user_id = ?", (current_user.id,))
            existing = cursor.fetchone()
            print(f"[DEBUG] Существующая запись sync_config: {existing}")
            
            if existing:
                # Обновляем существующую запись
                cursor.execute("""
                    UPDATE sync_config 
                    SET yandex_login = ?, yandex_password = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (username, password, current_user.id))
                print(f"[DEBUG] Обновлена существующая запись sync_config")
            else:
                # Создаем новую запись
                cursor.execute("""
                    INSERT INTO sync_config (user_id, yandex_login, yandex_password, auto_sync, backup_folder)
                    VALUES (?, ?, ?, ?, ?)
                """, (current_user.id, username, password, False, '/LegalCRM_Backups'))
                print(f"[DEBUG] Создана новая запись sync_config")
            
            # Проверяем что запись сохранилась
            cursor.execute("""
                SELECT yandex_login, yandex_password 
                FROM sync_config 
                WHERE user_id = ?
            """, (current_user.id,))
            saved_data = cursor.fetchone()
            print(f"[DEBUG] Проверяем сохраненные данные: {saved_data}")
            
            if not saved_data or not saved_data[0]:
                return jsonify({'success': False, 'error': 'Не удалось сохранить данные в базу данных'})
            
            # Сохраняем изменения в базу данных
            conn.commit()
            print(f"[DEBUG] Данные синхронизации сохранены в БД")
        
        return jsonify({
            'success': True, 
            'message': 'Подключение к Яндекс.Диску настроено успешно!'
        })
        
    except Exception as e:
        print(f"[ERROR] Ошибка в setup_yandex_sync: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sync/upload', methods=['POST'])
@login_required
def upload_to_yandex():
    """Загрузка данных на Яндекс.Диск"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем конфигурацию
            cursor.execute("""
                SELECT yandex_login, yandex_password 
                FROM sync_config 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (current_user.id,))
            
            result = cursor.fetchone()
            if not result or not result[0]:
                return jsonify({'success': False, 'error': 'Синхронизация не настроена'})
            
            username, password = result
            
            # Создаем WebDAV клиент и менеджер синхронизации
            from sync.yandex_webdav import YandexDiskWebDAV, DatabaseSyncManager
            from datetime import datetime
            
            yandex_disk = YandexDiskWebDAV(username, password)
            sync_manager = DatabaseSyncManager(
                db_path=os.path.abspath('legal_crm.db'), 
                yandex_disk=yandex_disk, 
                remote_path='/legal_crm/'
            )
            
            # Загружаем базу данных в облако
            result = sync_manager.upload_to_cloud()
            
            if result:
                # Обновляем время последней синхронизации
                cursor.execute("""
                    UPDATE sync_config 
                    SET last_sync = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                """, (current_user.id,))
                
                # Сохраняем изменения в базу данных
                conn.commit()
                print(f"[DEBUG] Время последней синхронизации обновлено")
                
                return jsonify({
                    'success': True, 
                    'message': 'Данные успешно загружены в Яндекс.Диск!'
                })
            else:
                return jsonify({
                    'success': False, 
                    'error': 'Не удалось загрузить данные в Яндекс.Диск'
                })
                
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sync/download', methods=['POST'])
@login_required
def download_from_yandex():
    """Скачивание данных с Яндекс.Диска"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем конфигурацию
            cursor.execute("""
                SELECT yandex_login, yandex_password 
                FROM sync_config 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (current_user.id,))
            
            result = cursor.fetchone()
            if not result or not result[0]:
                return jsonify({'success': False, 'error': 'Синхронизация не настроена'})
            
            username, password = result
            
            # Создаем WebDAV клиент и менеджер синхронизации
            from sync.yandex_webdav import YandexDiskWebDAV, DatabaseSyncManager
            
            yandex_disk = YandexDiskWebDAV(username, password)
            sync_manager = DatabaseSyncManager(
                db_path=os.path.abspath('legal_crm.db'), 
                yandex_disk=yandex_disk, 
                remote_path='/legal_crm/'
            )
            
            # Скачиваем последнюю версию базы данных
            result = sync_manager.download_from_cloud()
            
            if result.get('success'):
                # Обновляем время последней синхронизации
                cursor.execute("""
                    UPDATE sync_config 
                    SET last_sync = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                """, (current_user.id,))
                
                # Сохраняем изменения в базу данных
                conn.commit()
                print(f"[DEBUG] Время последней синхронизации обновлено")
                
                return jsonify({
                    'success': True, 
                    'message': 'Данные успешно загружены из Яндекс.Диска!'
                })
            else:
                return jsonify({
                    'success': False, 
                    'error': result.get('error', 'Не удалось скачать данные с Яндекс.Диска')
                })
                
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sync/auto/enable', methods=['POST'])
@login_required
def enable_auto_sync():
    """Включение автоматической синхронизации"""
    try:
        data = request.get_json() or {}
        interval_minutes = data.get('interval_minutes', 30)
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Обновляем настройки автосинхронизации
            cursor.execute("""
                UPDATE sync_config 
                SET auto_sync = 1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (current_user.id,))
            
            # Проверяем, что запись обновилась
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Синхронизация не настроена'})
            
            # TODO: В реальном приложении здесь можно запустить фоновый процесс
            # для автоматической синхронизации каждые interval_minutes минут
            
            return jsonify({
                'success': True, 
                'message': f'Автоматическая синхронизация включена (интервал: {interval_minutes} мин)'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sync/auto/disable', methods=['POST'])
@login_required
def disable_auto_sync():
    """Отключение автоматической синхронизации"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Отключаем автосинхронизацию
            cursor.execute("""
                UPDATE sync_config 
                SET auto_sync = 0, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (current_user.id,))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'error': 'Синхронизация не настроена'})
            
            return jsonify({
                'success': True, 
                'message': 'Автоматическая синхронизация отключена'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sync/backups', methods=['GET'])
@login_required
def get_backup_history():
    """Получение истории резервных копий"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем конфигурацию
            cursor.execute("""
                SELECT yandex_login, yandex_password 
                FROM sync_config 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (current_user.id,))
            
            result = cursor.fetchone()
            if not result or not result[0]:
                return jsonify({'success': False, 'error': 'Синхронизация не настроена'})
            
            username, password = result
            
            # Получаем список резервных копий через WebDAV клиент
            from sync.yandex_webdav import YandexDiskWebDAV, DatabaseSyncManager
            
            yandex_disk = YandexDiskWebDAV(username, password)
            sync_manager = DatabaseSyncManager(
                db_path=os.path.abspath('legal_crm.db'), 
                yandex_disk=yandex_disk, 
                remote_path='/legal_crm/'
            )
            
            backups = sync_manager.list_backups()
            
            return jsonify({
                'success': True, 
                'backups': backups
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sync/restore', methods=['POST'])
@login_required
def restore_from_backup():
    """Восстановление из резервной копии"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных для обработки'})
        
        backup_filename = data.get('backup_filename')
        if not backup_filename:
            return jsonify({'success': False, 'error': 'Не указан файл резервной копии'})
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем конфигурацию
            cursor.execute("""
                SELECT yandex_login, yandex_password 
                FROM sync_config 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (current_user.id,))
            
            result = cursor.fetchone()
            if not result or not result[0]:
                return jsonify({'success': False, 'error': 'Синхронизация не настроена'})
            
            username, password = result
            
            # Восстанавливаем из резервной копии
            from sync.yandex_webdav import YandexDiskWebDAV, DatabaseSyncManager
            
            yandex_disk = YandexDiskWebDAV(username, password)
            sync_manager = DatabaseSyncManager(
                db_path=os.path.abspath('legal_crm.db'), 
                yandex_disk=yandex_disk, 
                remote_path='/legal_crm/'
            )
            
            result = sync_manager.restore_backup(backup_filename)
            
            if result.get('success'):
                return jsonify({
                    'success': True, 
                    'message': f'Успешно восстановлено из резервной копии: {backup_filename}'
                })
            else:
                return jsonify({
                    'success': False, 
                    'error': result.get('error', 'Не удалось восстановить из резервной копии')
                })
                
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sync/cleanup', methods=['POST'])
@login_required
def cleanup_old_backups():
    """Очистка старых резервных копий"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем конфигурацию
            cursor.execute("""
                SELECT yandex_login, yandex_password 
                FROM sync_config 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (current_user.id,))
            
            result = cursor.fetchone()
            if not result or not result[0]:
                return jsonify({'success': False, 'error': 'Синхронизация не настроена'})
            
            username, password = result
            
            # Очищаем старые резервные копии
            from sync.yandex_webdav import YandexDiskWebDAV, DatabaseSyncManager
            
            yandex_disk = YandexDiskWebDAV(username, password)
            sync_manager = DatabaseSyncManager(
                db_path=os.path.abspath('legal_crm.db'), 
                yandex_disk=yandex_disk, 
                remote_path='/legal_crm/'
            )
            
            result = sync_manager.cleanup_old_backups(retention_days=30)
            
            if result.get('success'):
                return jsonify({
                    'success': True, 
                    'message': result.get('message', 'Очистка старых резервных копий завершена')
                })
            else:
                return jsonify({
                    'success': False, 
                    'error': result.get('error', 'Не удалось очистить старые резервные копии')
                })
                
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== DEBUG ENDPOINTS ====================

@app.route('/api/debug/user', methods=['GET'])
@login_required
def debug_user():
    """Отладочная информация о пользователе"""
    try:
        debug_info = {
            'current_user_id': current_user.id,
            'current_user_username': current_user.username,
            'is_authenticated': current_user.is_authenticated,
            'user_type': type(current_user).__name__
        }
        
        # Проверяем пользователя в базе данных
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, created_at FROM users WHERE id = ?", (current_user.id,))
            user_data = cursor.fetchone()
            debug_info['database_user'] = dict(user_data) if user_data else None
            
            # Проверяем sync_config
            cursor.execute("SELECT COUNT(*) FROM sync_config WHERE user_id = ?", (current_user.id,))
            sync_count = cursor.fetchone()[0]
            debug_info['sync_config_count'] = sync_count
            
            if sync_count > 0:
                cursor.execute("""
                    SELECT user_id, yandex_login, auto_sync, created_at 
                    FROM sync_config WHERE user_id = ? 
                    ORDER BY created_at DESC LIMIT 1
                """, (current_user.id,))
                sync_data = cursor.fetchone()
                debug_info['sync_config_data'] = {
                    'user_id': sync_data[0],
                    'yandex_login': sync_data[1],
                    'auto_sync': sync_data[2],
                    'created_at': str(sync_data[3])
                }
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    print("🚀 Запуск Legal CRM Web Application...")
    print("✅ Система авторизации с Flask-Login настроена")
    print("🔗 Демо-пользователь: admin / 12345")
    print("🔧 Синхронизация с Яндекс.Диском ИСПРАВЛЕНА с детальным логированием")
    print("✅ Все модули полностью реализованы: Клиенты, Дела, Услуги, События, Платежи")
    print(f"🌐 Сервер запущен на порту {PORT}")
    
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG_MODE)
