"""
Веб-версия Legal CRM с аутентификацией - Flask Backend
Система учета клиентов и активностей для юридической практики с защитой
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import secrets
from datetime import datetime
import json

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Разрешаем CORS для фронтенда

# Константы
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'legal_crm.db')
STATIC_FOLDER = 'static'
TEMPLATES_FOLDER = 'templates'

# Настройки безопасности
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 8  # 8 часов

# Настройки для облачного развертывания
DEBUG_MODE = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))

class AuthDatabase:
    def __init__(self, db_name=DATABASE_NAME):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных с таблицей пользователей"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Включаем поддержку внешних ключей
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Таблица пользователей (добавляем аутентификацию)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME,
                is_active BOOLEAN DEFAULT 1
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
                passport_data TEXT,
                inn TEXT,
                notes TEXT,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'Активный'
            )
        """)
        
        # Таблица судебных дел
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                case_number TEXT NOT NULL,
                court_name TEXT,
                case_type TEXT,
                plaintiff TEXT,
                defendant TEXT,
                claim_amount REAL,
                case_stage TEXT,
                start_date TEXT,
                end_date TEXT,
                result TEXT,
                notes TEXT,
                status TEXT DEFAULT 'Активное',
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)
        
        # Таблица услуг
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                case_id INTEGER,
                service_type TEXT NOT NULL,
                description TEXT,
                service_date TEXT,
                hours REAL,
                cost REAL,
                notes TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL
            )
        """)
        
        # Таблица платежей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                case_id INTEGER,
                service_id INTEGER,
                payment_type TEXT,
                amount REAL NOT NULL,
                payment_date TEXT,
                payment_method TEXT,
                invoice_number TEXT,
                notes TEXT,
                status TEXT DEFAULT 'Оплачено',
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL,
                FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL
            )
        """)
        
        # Таблица событий календаря
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                case_id INTEGER,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                event_date TEXT NOT NULL,
                event_time TEXT,
                location TEXT,
                reminder INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Запланировано',
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
            )
        """)
        
        # Таблица документов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                case_id INTEGER,
                document_type TEXT NOT NULL,
                title TEXT NOT NULL,
                file_path TEXT,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
            )
        """)
        
        # Создаем администратора по умолчанию, если его нет
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            admin_hash = generate_password_hash(admin_password)
            
            cursor.execute("""
                INSERT INTO users (username, password_hash, email, full_name, role)
                VALUES (?, ?, ?, ?, ?)
            """, ('admin', admin_hash, 'admin@legal-crm.com', 'Администратор', 'admin'))
            
            print(f"🔑 Создан администратор по умолчанию:")
            print(f"   Логин: admin")
            print(f"   Пароль: {admin_password}")
            print(f"   ⚠️  Обязательно смените пароль после первого входа!")
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Получение соединения с базой данных"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # Для получения данных как словарей
        return conn

db = AuthDatabase()

# ==================== СИСТЕМА АУТЕНТИФИКАЦИИ ====================

def login_required(f):
    """Декоратор для защищенных маршрутов"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    
    return decorated_function

def api_login_required(f):
    """Декоратор для защищенных API маршрутов"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Требуется аутентификация'}), 401
        return f(*args, **kwargs)
    
    return decorated_function

@app.route('/login')
def login():
    """Страница входа в систему"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """API для входа в систему"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Логин и пароль обязательны'}), 400
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE username = ? AND is_active = 1",
                (username,)
            )
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                # Успешная аутентификация
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session.permanent = True
                
                # Обновляем время последнего входа
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.now(), user['id'])
                )
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'user': {
                        'id': user['id'],
                        'username': user['username'],
                        'full_name': user['full_name'],
                        'role': user['role']
                    }
                })
            else:
                return jsonify({'success': False, 'error': 'Неверный логин или пароль'}), 401
                
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
@api_login_required
def api_logout():
    """API для выхода из системы"""
    session.clear()
    return jsonify({'success': True, 'message': 'Вы успешно вышли из системы'})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Проверка аутентификации"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session['user_id'],
                'username': session['username'],
                'role': session['role']
            }
        })
    return jsonify({'authenticated': False})

@app.route('/api/auth/change-password', methods=['POST'])
@api_login_required
def change_password():
    """Смена пароля пользователя"""
    try:
        data = request.json
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'success': False, 'error': 'Все поля обязательны'}), 400
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE id = ?",
                (session['user_id'],)
            )
            user = cursor.fetchone()
            
            if not check_password_hash(user['password_hash'], current_password):
                return jsonify({'success': False, 'error': 'Неверный текущий пароль'}), 400
            
            # Обновляем пароль
            new_hash = generate_password_hash(new_password)
            cursor.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_hash, session['user_id'])
            )
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Пароль успешно изменен'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ГЛАВНЫЕ МАРШРУТЫ ====================

@app.route('/')
@login_required
def index():
    """Главная страница (защищена)"""
    return render_template('index.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    return redirect(url_for('login'))

# ==================== ЗАЩИЩЕННЫЕ API ENDPOINTS ====================

@app.route('/api/clients', methods=['GET'])
@api_login_required
def get_clients():
    """Получение всех клиентов"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            search = request.args.get('search', '')
            status = request.args.get('status', '')
            
            query = "SELECT * FROM clients WHERE 1=1"
            params = []
            
            if search:
                query += " AND (full_name LIKE ? OR phone LIKE ? OR email LIKE ?)"
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param])
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY full_name"
            
            cursor.execute(query, params)
            clients = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({'success': True, 'data': clients})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clients', methods=['POST'])
@api_login_required
def add_client():
    """Добавление клиента"""
    try:
        data = request.json
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO clients (full_name, phone, email, address, passport_data, inn, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('full_name'),
                data.get('phone', ''),
                data.get('email', ''),
                data.get('address', ''),
                data.get('passport_data', ''),
                data.get('inn', ''),
                data.get('notes', '')
            ))
            
            client_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({'success': True, 'id': client_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clients/<int:client_id>', methods=['PUT'])
@api_login_required
def update_client(client_id):
    """Обновление клиента"""
    try:
        data = request.json
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Создаем динамический запрос UPDATE
            fields = []
            values = []
            
            for key, value in data.items():
                if key != 'id':  # Не обновляем ID
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if fields:
                values.append(client_id)
                query = f"UPDATE clients SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(query, values)
                conn.commit()
            
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clients/<int:client_id>', methods=['DELETE'])
@api_login_required
def delete_client(client_id):
    """Удаление клиента"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            conn.commit()
            
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Аналогичные endpoints для дел, услуг, платежей, событий и документов
@app.route('/api/cases', methods=['GET'])
@api_login_required
def get_cases():
    """Получение всех дел"""
    try:
        client_id = request.args.get('client_id')
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if client_id:
                query = """
                    SELECT c.*, cl.full_name as client_name
                    FROM cases c
                    JOIN clients cl ON c.client_id = cl.id
                    WHERE c.client_id = ?
                    ORDER BY c.start_date DESC
                """
                cursor.execute(query, (client_id,))
            else:
                query = """
                    SELECT c.*, cl.full_name as client_name
                    FROM cases c
                    JOIN clients cl ON c.client_id = cl.id
                    ORDER BY c.start_date DESC
                """
                cursor.execute(query)
            
            cases = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({'success': True, 'data': cases})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cases', methods=['POST'])
@api_login_required
def add_case():
    """Добавление дела"""
    try:
        data = request.json
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO cases (client_id, case_number, court_name, case_type,
                                 plaintiff, defendant, claim_amount, case_stage,
                                 start_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('client_id'),
                data.get('case_number'),
                data.get('court_name', ''),
                data.get('case_type', ''),
                data.get('plaintiff', ''),
                data.get('defendant', ''),
                data.get('claim_amount', 0),
                data.get('case_stage', ''),
                data.get('start_date', ''),
                data.get('notes', '')
            ))
            
            case_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({'success': True, 'id': case_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/services', methods=['GET'])
@api_login_required
def get_services():
    """Получение всех услуг"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT s.*, cl.full_name as client_name, c.case_number
                FROM services s
                JOIN clients cl ON s.client_id = cl.id
                LEFT JOIN cases c ON s.case_id = c.id
                ORDER BY s.service_date DESC
            """
            
            cursor.execute(query)
            services = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({'success': True, 'data': services})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/services', methods=['POST'])
@api_login_required
def add_service():
    """Добавление услуги"""
    try:
        data = request.json
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO services (client_id, case_id, service_type, description,
                                    service_date, hours, cost, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('client_id'),
                data.get('case_id'),
                data.get('service_type'),
                data.get('description', ''),
                data.get('service_date', ''),
                data.get('hours', 0),
                data.get('cost', 0),
                data.get('notes', '')
            ))
            
            service_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({'success': True, 'id': service_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/payments', methods=['GET'])
@api_login_required
def get_payments():
    """Получение всех платежей"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT p.*, cl.full_name as client_name, c.case_number
                FROM payments p
                JOIN clients cl ON p.client_id = cl.id
                LEFT JOIN cases c ON p.case_id = c.id
                ORDER BY p.payment_date DESC
            """
            
            cursor.execute(query)
            payments = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({'success': True, 'data': payments})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/payments', methods=['POST'])
@api_login_required
def add_payment():
    """Добавление платежа"""
    try:
        data = request.json
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO payments (client_id, case_id, service_id, payment_type,
                                    amount, payment_date, payment_method,
                                    invoice_number, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('client_id'),
                data.get('case_id'),
                data.get('service_id'),
                data.get('payment_type', ''),
                data.get('amount'),
                data.get('payment_date', ''),
                data.get('payment_method', ''),
                data.get('invoice_number', ''),
                data.get('notes', '')
            ))
            
            payment_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({'success': True, 'id': payment_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/events', methods=['GET'])
@api_login_required
def get_events():
    """Получение всех событий"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT e.*, cl.full_name as client_name, c.case_number
                FROM events e
                LEFT JOIN clients cl ON e.client_id = cl.id
                LEFT JOIN cases c ON e.case_id = c.id
                ORDER BY e.event_date, e.event_time
            """
            
            cursor.execute(query)
            events = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({'success': True, 'data': events})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/events/<int:event_id>', methods=['GET'])
@api_login_required
def get_event(event_id):
    """Получение конкретного события по ID"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT e.*, cl.full_name as client_name, c.case_number
                FROM events e
                LEFT JOIN clients cl ON e.client_id = cl.id
                LEFT JOIN cases c ON e.case_id = c.id
                WHERE e.id = ?
            """
            
            cursor.execute(query, (event_id,))
            row = cursor.fetchone()
            
            if row:
                event = dict(row)
                return jsonify({'success': True, 'data': event})
            else:
                return jsonify({'success': False, 'error': 'Событие не найдено'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/events', methods=['POST'])
@api_login_required
def add_event():
    """Добавление события"""
    try:
        data = request.json
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO events (client_id, case_id, event_type, title,
                                  description, event_date, event_time, location, reminder)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('client_id'),
                data.get('case_id'),
                data.get('event_type'),
                data.get('title'),
                data.get('description', ''),
                data.get('event_date'),
                data.get('event_time', ''),
                data.get('location', ''),
                data.get('reminder', 0)
            ))
            
            event_id = cursor.lastrowid
            conn.commit()
            
            return jsonify({'success': True, 'id': event_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/events/<int:event_id>', methods=['PUT'])
@api_login_required
def update_event(event_id):
    """Обновление события"""
    try:
        data = request.json
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            fields = []
            values = []
            
            for key, value in data.items():
                if key != 'id':
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if fields:
                values.append(event_id)
                query = f"UPDATE events SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(query, values)
                conn.commit()
            
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
@api_login_required
def delete_event(event_id):
    """Удаление события"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cases/<int:case_id>', methods=['PUT'])
@api_login_required
def update_case(case_id):
    """Обновление дела"""
    try:
        data = request.json
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            fields = []
            values = []
            
            for key, value in data.items():
                if key != 'id':
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if fields:
                values.append(case_id)
                query = f"UPDATE cases SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(query, values)
                conn.commit()
            
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cases/<int:case_id>', methods=['DELETE'])
@api_login_required
def delete_case(case_id):
    """Удаление дела"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cases WHERE id = ?", (case_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/services/<int:service_id>', methods=['PUT'])
@api_login_required
def update_service(service_id):
    """Обновление услуги"""
    try:
        data = request.json
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            fields = []
            values = []
            
            for key, value in data.items():
                if key != 'id':
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if fields:
                values.append(service_id)
                query = f"UPDATE services SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(query, values)
                conn.commit()
            
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/services/<int:service_id>', methods=['DELETE'])
@api_login_required
def delete_service(service_id):
    """Удаление услуги"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/payments/<int:payment_id>', methods=['PUT'])
@api_login_required
def update_payment(payment_id):
    """Обновление платежа"""
    try:
        data = request.json
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            fields = []
            values = []
            
            for key, value in data.items():
                if key != 'id':
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if fields:
                values.append(payment_id)
                query = f"UPDATE payments SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(query, values)
                conn.commit()
            
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/payments/<int:payment_id>', methods=['DELETE'])
@api_login_required
def delete_payment(payment_id):
    """Удаление платежа"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/statistics', methods=['GET'])
@api_login_required
def get_statistics():
    """Получение статистики"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Количество клиентов
            cursor.execute("SELECT COUNT(*) FROM clients WHERE status='Активный'")
            stats['active_clients'] = cursor.fetchone()[0]
            
            # Количество активных дел
            cursor.execute("SELECT COUNT(*) FROM cases WHERE status='Активное'")
            stats['active_cases'] = cursor.fetchone()[0]
            
            # События на сегодня
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                SELECT COUNT(*) FROM events 
                WHERE event_date = ? AND status='Запланировано'
            """, (today,))
            stats['today_events'] = cursor.fetchone()[0]
            
            # Общая сумма платежей за текущий месяц
            current_month = datetime.now().strftime("%Y-%m")
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM payments 
                WHERE payment_date LIKE ?
            """, (f"{current_month}%",))
            stats['month_payments'] = cursor.fetchone()[0]
            
            return jsonify({'success': True, 'data': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== DEMO DATA ENDPOINT ====================

@app.route('/api/demo-data', methods=['POST'])
@api_login_required
def create_demo_data():
    """Создание демонстрационных данных"""
    try:
        from datetime import timedelta
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Очистим таблицы для чистого старта
            cursor.execute("DELETE FROM events")
            cursor.execute("DELETE FROM payments")
            cursor.execute("DELETE FROM services")
            cursor.execute("DELETE FROM cases")
            cursor.execute("DELETE FROM clients")
            
            # Демонстрационные клиенты (упрощенно)
            demo_clients = [
                ('Иванов Иван Иванович', '+7-999-123-45-67', 'ivanov@example.com', 'г. Москва, ул. Тверская, д. 10', '4510 123456', '1234567890', 'Постоянный клиент'),
                ('Петрова Елена Алексеевна', '+7-999-234-56-78', 'petrova@example.com', 'г. Санкт-Петербург, пр. Невский, д. 25', '4510 234567', '2345678901', 'Корпоративный клиент')
            ]
            
            client_ids = []
            for client_data in demo_clients:
                cursor.execute("""
                    INSERT INTO clients (full_name, phone, email, address, passport_data, inn, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, client_data)
                client_ids.append(cursor.lastrowid)
            
            # Демонстрационные дела (упрощенно)
            demo_cases = [
                (client_ids[0], 'А40-123456/2024', 'Арбитражный суд г. Москвы', 'Экономический спор', 'ООО "Ромашка"', 'ИП Иванов И.И.', 500000.00),
                (client_ids[1], '2-1234/2024', 'Суд общей юрисдикции г. Санкт-Петербурга', 'Семейное право', 'Петрова Е.А.', 'Сидоров С.С.', 0)
            ]
            
            case_ids = []
            for case_data in demo_cases:
                cursor.execute("""
                    INSERT INTO cases (client_id, case_number, court_name, case_type,
                                     plaintiff, defendant, claim_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, case_data)
                case_ids.append(cursor.lastrowid)
            
            # Демонстрационные услуги (упрощенно)
            today = datetime.now()
            demo_services = [
                (client_ids[0], case_ids[0], 'Консультация', 'Первичная консультация по делу', 
                 (today - timedelta(days=30)).strftime('%Y-%m-%d'), 2.0, 15000.00),
                (client_ids[1], case_ids[1], 'Подготовка документов', 'Составление искового заявления', 
                 (today - timedelta(days=25)).strftime('%Y-%m-%d'), 4.0, 25000.00)
            ]
            
            for service_data in demo_services:
                cursor.execute("""
                    INSERT INTO services (client_id, case_id, service_type, description,
                                        service_date, hours, cost)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, service_data)
            
            # Демонстрационные платежи (упрощенно)
            demo_payments = [
                (client_ids[0], case_ids[0], None, 'Оплата услуг', 20000.00, 
                 (today - timedelta(days=28)).strftime('%Y-%m-%d'), 'Банковский перевод', 'INV-001'),
                (client_ids[1], case_ids[1], None, 'Оплата услуг', 25000.00, 
                 (today - timedelta(days=23)).strftime('%Y-%m-%d'), 'Карта', 'INV-002')
            ]
            
            for payment_data in demo_payments:
                cursor.execute("""
                    INSERT INTO payments (client_id, case_id, service_id, payment_type,
                                        amount, payment_date, payment_method, invoice_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, payment_data)
            
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Демонстрационные данные созданы!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # Создаем папки для статических файлов и шаблонов
    os.makedirs(STATIC_FOLDER, exist_ok=True)
    os.makedirs(TEMPLATES_FOLDER, exist_ok=True)
    
    # Запускаем сервер для облачного развертывания
    print("🚀 Запуск веб-версии Legal CRM с аутентификацией...")
    print(f"📡 Сервер доступен по адресу: http://localhost:{PORT}")
    print("⚖️  Legal CRM Web - Защищенная система для юристов")
    print("💡 Для создания демо-данных перейдите на /api/demo-data (POST)")
    print("🔐 Главная страница защищена - требуется авторизация")
    
    # Для production окружения используем переменную PORT
    app.run(debug=DEBUG_MODE, host='0.0.0.0', port=PORT)
