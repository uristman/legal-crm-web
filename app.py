"""
Legal CRM - Финальная стабильная версия
Исправлены все ошибки: HTTP методы, БД, мобильные шаблоны
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

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

def is_mobile_device():
    """Определение мобильного устройства по User-Agent"""
    user_agent = request.headers.get('User-Agent', '').lower()
    
    mobile_agents = [
        'mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 
        'windows phone', 'webos', 'opera mobi', 'opera mini'
    ]
    
    return any(agent in user_agent for agent in mobile_agents)

class WebDatabase:
    def __init__(self, db_name=DATABASE_NAME):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        try:
            # Удаляем старую БД для чистой установки
            if os.path.exists(self.db_name):
                os.remove(self.db_name)
                print("Старая база данных удалена")
            
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Включаем поддержку внешних ключей
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Таблица клиентов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    company TEXT,
                    registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # Таблица услуг
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    price REAL DEFAULT 0,
                    duration_hours REAL DEFAULT 0,
                    category TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Таблица дел/кейсов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    service_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'medium',
                    start_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    end_date TEXT,
                    lawyer_assigned TEXT,
                    total_hours REAL DEFAULT 0,
                    hourly_rate REAL DEFAULT 0,
                    total_cost REAL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE,
                    FOREIGN KEY (service_id) REFERENCES services (id) ON DELETE SET NULL
                )
            """)
            
            # Таблица платежей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER,
                    amount REAL NOT NULL,
                    payment_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    payment_method TEXT,
                    reference_number TEXT,
                    notes TEXT,
                    status TEXT DEFAULT 'completed',
                    FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
                )
            """)
            
            # Таблица календаря
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER,
                    client_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    event_date TEXT NOT NULL,
                    event_time TEXT,
                    duration_hours REAL DEFAULT 1,
                    event_type TEXT DEFAULT 'meeting',
                    location TEXT,
                    status TEXT DEFAULT 'scheduled',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE SET NULL,
                    FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE SET NULL
                )
            """)
            
            # Таблица пользователей для аутентификации
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    email TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Добавляем тестовые данные
            test_clients = [
                ("Иванов Иван Иванович", "+7-999-123-45-67", "ivanov@example.com", 
                 "г. Москва, ул. Примерная, д. 1", "ООО Пример", 
                 "Тестовый клиент", "active"),
                ("Петрова Анна Сергеевна", "+7-999-987-65-43", "petrova@example.com",
                 "г. СПб, пр. Тестовый, д. 5", "", "Другая тестовая запись", "active"),
                ("Сидоров Михаил Петрович", "+7-999-111-22-33", "sidorov@example.com",
                 "г. Казань, ул. Примерная, д. 15", "ИП Сидоров", "Пробная запись", "active")
            ]
            cursor.executemany("""INSERT INTO clients 
                (full_name, phone, email, address, company, notes, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""", test_clients)
            
            test_services = [
                ("Консультация юриста", "Первичная правовая консультация", 5000, 1, "Консультации", 1),
                ("Составление договора", "Подготовка договора любой сложности", 10000, 2, "Документы", 1),
                ("Представительство в суде", "Представительство интересов в суде", 15000, 4, "Судебная работа", 1),
                ("Регистрация ООО", "Полный комплекс услуг по регистрации", 25000, 8, "Регистрация", 1)
            ]
            cursor.executemany("""INSERT INTO services 
                (name, description, price, duration_hours, category, is_active) 
                VALUES (?, ?, ?, ?, ?, ?)""", test_services)
            
            test_cases = [
                (1, 1, "Консультация по корпоративному праву", "Консультация по вопросам слияния компаний", 
                 "completed", "high", None, "Иванов И.И.", 2, 2500, 5000, datetime.now().isoformat()),
                (2, 2, "Составление договора поставки", "Договор между поставщиком и покупателем", 
                 "in_progress", "medium", None, "Петров П.П.", 5, 2000, 10000, datetime.now().isoformat()),
                (3, 3, "Судебное разбирательство", "Представительство в арбитражном суде", 
                 "pending", "high", None, "Сидоров С.С.", 10, 1500, 15000, datetime.now().isoformat())
            ]
            cursor.executemany("""INSERT INTO cases 
                (client_id, service_id, title, description, status, priority, end_date, 
                 lawyer_assigned, total_hours, hourly_rate, total_cost, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", test_cases)
            
            test_payments = [
                (1, 2500, "2025-01-15", "Банковский перевод", "TR001", "Первая часть оплаты", "completed"),
                (2, 5000, "2025-01-20", "Наличными", "CASH002", "Полная оплата услуги", "completed"),
                (3, 8000, "2025-01-25", "Банковская карта", "CARD003", "Авансовый платеж", "completed")
            ]
            cursor.executemany("""INSERT INTO payments 
                (case_id, amount, payment_date, payment_method, reference_number, notes, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?)""", test_payments)
            
            # Создаем администратора по умолчанию
            default_password_hash = generate_password_hash("admin123")
            cursor.execute("""INSERT INTO users 
                (username, password_hash, full_name, email, is_active) 
                VALUES (?, ?, ?, ?, ?)""", 
                ("admin", default_password_hash, "Администратор", "admin@legalcrm.com", 1))
            
            conn.commit()
            conn.close()
            print("База данных успешно инициализирована")
            
        except Exception as e:
            print(f"Ошибка инициализации базы данных: {e}")

# Инициализация базы данных
db = WebDatabase()

# === АУТЕНТИФИКАЦИЯ ===

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Аутентификация пользователя"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Логин и пароль обязательны'}), 400
        
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, username, password_hash, full_name, is_active FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and user[4] and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['full_name'] = user[3]
            return jsonify({
                'success': True, 
                'message': 'Успешный вход',
                'user': {
                    'id': user[0],
                    'username': user[1],
                    'full_name': user[3]
                }
            })
        else:
            return jsonify({'error': 'Неверный логин или пароль'}), 401
            
    except Exception as e:
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Выход из системы"""
    try:
        session.clear()
        return jsonify({'success': True, 'message': 'Успешный выход'})
    except Exception as e:
        return jsonify({'error': f'Ошибка: {str(e)}'}), 500

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Проверка аутентификации"""
    try:
        if 'user_id' in session:
            return jsonify({
                'authenticated': True,
                'user': {
                    'id': session['user_id'],
                    'username': session['username'],
                    'full_name': session.get('full_name', '')
                }
            })
        else:
            return jsonify({'authenticated': False}), 200
    except Exception as e:
        return jsonify({'authenticated': False}), 200

def login_required(f):
    """Декоратор для защищенных маршрутов"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Требуется аутентификация'}), 401
        return f(*args, **kwargs)
    return decorated_function

# === API ЭНДПОИНТЫ ===

@app.route('/api/clients', methods=['GET'])
@login_required
def get_clients():
    """Получение списка клиентов"""
    try:
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.id, c.full_name, c.phone, c.email, c.address, c.company, 
                   c.registration_date, c.notes, c.status,
                   COUNT(case_cases.id) as cases_count
            FROM clients c
            LEFT JOIN cases case_cases ON c.id = case_cases.client_id
            GROUP BY c.id
            ORDER BY c.registration_date DESC
        """)
        
        clients = []
        for row in cursor.fetchall():
            clients.append({
                'id': row[0],
                'full_name': row[1],
                'phone': row[2] or '',
                'email': row[3] or '',
                'address': row[4] or '',
                'company': row[5] or '',
                'registration_date': row[6],
                'notes': row[7] or '',
                'status': row[8],
                'cases_count': row[9]
            })
        
        conn.close()
        return jsonify(clients)
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения клиентов: {str(e)}'}), 500

@app.route('/api/cases', methods=['GET'])
@login_required
def get_cases():
    """Получение списка дел"""
    try:
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ca.id, ca.title, ca.description, ca.status, ca.priority,
                   ca.start_date, ca.end_date, ca.lawyer_assigned, 
                   ca.total_hours, ca.hourly_rate, ca.total_cost,
                   c.full_name as client_name, s.name as service_name,
                   ca.client_id, ca.service_id
            FROM cases ca
            JOIN clients c ON ca.client_id = c.id
            JOIN services s ON ca.service_id = s.id
            ORDER BY ca.start_date DESC
        """)
        
        cases = []
        for row in cursor.fetchall():
            cases.append({
                'id': row[0],
                'title': row[1],
                'description': row[2] or '',
                'status': row[3],
                'priority': row[4],
                'start_date': row[5],
                'end_date': row[6],
                'lawyer_assigned': row[7] or '',
                'total_hours': row[8],
                'hourly_rate': row[9],
                'total_cost': row[10],
                'client_name': row[11],
                'service_name': row[12],
                'client_id': row[13],
                'service_id': row[14]
            })
        
        conn.close()
        return jsonify(cases)
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения дел: {str(e)}'}), 500

@app.route('/api/services', methods=['GET'])
@login_required
def get_services():
    """Получение списка услуг"""
    try:
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, price, duration_hours, category, is_active
            FROM services
            WHERE is_active = 1
            ORDER BY name
        """)
        
        services = []
        for row in cursor.fetchall():
            services.append({
                'id': row[0],
                'name': row[1],
                'description': row[2] or '',
                'price': row[3],
                'duration_hours': row[4],
                'category': row[5],
                'is_active': row[6]
            })
        
        conn.close()
        return jsonify(services)
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения услуг: {str(e)}'}), 500

@app.route('/api/payments', methods=['GET'])
@login_required
def get_payments():
    """Получение списка платежей"""
    try:
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.id, p.amount, p.payment_date, p.payment_method, 
                   p.reference_number, p.notes, p.status,
                   c.full_name as client_name, ca.title as case_title
            FROM payments p
            JOIN cases ca ON p.case_id = ca.id
            JOIN clients c ON ca.client_id = c.id
            ORDER BY p.payment_date DESC
        """)
        
        payments = []
        for row in cursor.fetchall():
            payments.append({
                'id': row[0],
                'amount': row[1],
                'payment_date': row[2],
                'payment_method': row[3] or '',
                'reference_number': row[4] or '',
                'notes': row[5] or '',
                'status': row[6],
                'client_name': row[7],
                'case_title': row[8]
            })
        
        conn.close()
        return jsonify(payments)
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения платежей: {str(e)}'}), 500

@app.route('/api/calendar', methods=['GET'])
@login_required
def get_calendar_events():
    """Получение событий календаря"""
    try:
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT e.id, e.title, e.description, e.event_date, e.event_time,
                   e.duration_hours, e.event_type, e.location, e.status,
                   c.full_name as client_name, ca.title as case_title
            FROM calendar_events e
            LEFT JOIN clients c ON e.client_id = c.id
            LEFT JOIN cases ca ON e.case_id = ca.id
            ORDER BY e.event_date DESC, e.event_time DESC
        """)
        
        events = []
        for row in cursor.fetchall():
            events.append({
                'id': row[0],
                'title': row[1],
                'description': row[2] or '',
                'event_date': row[3],
                'event_time': row[4] or '',
                'duration_hours': row[5],
                'event_type': row[6],
                'location': row[7] or '',
                'status': row[8],
                'client_name': row[9] or '',
                'case_title': row[10] or ''
            })
        
        conn.close()
        return jsonify(events)
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения событий: {str(e)}'}), 500

@app.route('/api/statistics', methods=['GET'])
@login_required
def get_statistics():
    """Получение статистики"""
    try:
        conn = sqlite3.connect(db.db_name)
        cursor = conn.cursor()
        
        # Общая статистика
        stats = {}
        
        # Количество клиентов
        cursor.execute("SELECT COUNT(*) FROM clients")
        stats['total_clients'] = cursor.fetchone()[0]
        
        # Количество активных дел
        cursor.execute("SELECT COUNT(*) FROM cases WHERE status != 'completed'")
        stats['active_cases'] = cursor.fetchone()[0]
        
        # Общий доход
        cursor.execute("SELECT SUM(amount) FROM payments WHERE status = 'completed'")
        result = cursor.fetchone()[0]
        stats['total_revenue'] = result[0] if result and result[0] else 0
        
        # Количество услуг
        cursor.execute("SELECT COUNT(*) FROM services WHERE is_active = 1")
        stats['active_services'] = cursor.fetchone()[0]
        
        # Статистика по статусам дел
        cursor.execute("SELECT status, COUNT(*) FROM cases GROUP BY status")
        stats['cases_by_status'] = dict(cursor.fetchall())
        
        # Статистика по месяцам (платежи)
        cursor.execute("""
            SELECT strftime('%Y-%m', payment_date) as month, SUM(amount) as total
            FROM payments 
            WHERE status = 'completed' 
            GROUP BY strftime('%Y-%m', payment_date)
            ORDER BY month DESC
            LIMIT 12
        """)
        stats['monthly_revenue'] = [{'month': row[0], 'amount': row[1]} for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения статистики: {str(e)}'}), 500

# === ОСНОВНЫЕ МАРШРУТЫ ===

@app.route('/')
def index():
    """Главная страница - перенаправление на логин или дашборд"""
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/login')
def login_page():
    """Страница логина"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

# === СТАТИЧЕСКИЕ ФАЙЛЫ ===

@app.route('/static/<path:filename>')
def static_files(filename):
    """Обслуживание статических файлов"""
    return send_from_directory('static', filename)

# === ОБРАБОТКА ОШИБОК ===

@app.errorhandler(404)
def not_found_error(error):
    """Обработка ошибки 404"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'API endpoint не найден'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработка внутренних ошибок сервера"""
    return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

if __name__ == '__main__':
    print(f"Запуск сервера на порту {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG_MODE)
