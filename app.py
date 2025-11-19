"""
Веб-версия Legal CRM - Flask Backend
Система учета клиентов и активностей для юридической практики
Версия с исправленной аутентификацией
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, session
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
import json

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

def is_mobile_device():
    """Определение мобильного устройства по User-Agent"""
    user_agent = request.headers.get('User-Agent', '').lower()
    
    mobile_agents = [
        'mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 
        'windows phone', 'webos', 'opera mobi', 'opera mini'
    ]
    
    return any(agent in user_agent for agent in mobile_agents)

def get_device_info():
    """Получение информации об устройстве"""
    try:
        return {
            'is_mobile': is_mobile_device(),
            'user_agent': request.headers.get('User-Agent', ''),
            'screen_size': request.args.get('screen_size', 'unknown'),
            'timestamp': datetime.now().isoformat()
        }
    except:
        return {
            'is_mobile': False,
            'user_agent': 'unknown',
            'screen_size': 'unknown',
            'timestamp': datetime.now().isoformat()
        }

class WebDatabase:
    def __init__(self, db_name=DATABASE_NAME):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Включаем поддержку внешних ключей
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Создаем таблицы
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
                    FOREIGN KEY (client_id) REFERENCES clients (id),
                    FOREIGN KEY (service_id) REFERENCES services (id)
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
                    FOREIGN KEY (case_id) REFERENCES cases (id)
                )
            """)
            
            # Таблица документов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_id INTEGER,
                    client_id INTEGER,
                    title TEXT NOT NULL,
                    file_path TEXT,
                    file_type TEXT,
                    upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    uploaded_by TEXT,
                    FOREIGN KEY (case_id) REFERENCES cases (id),
                    FOREIGN KEY (client_id) REFERENCES clients (id)
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
                    FOREIGN KEY (case_id) REFERENCES cases (id),
                    FOREIGN KEY (client_id) REFERENCES clients (id)
                )
            """)
            
            # Таблица пользователей для аутентификации
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    full_name TEXT,
                    email TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Добавляем тестовых данных, если таблицы пустые
            cursor.execute("SELECT COUNT(*) FROM clients")
            if cursor.fetchone()[0] == 0:
                test_data = [
                    ("Иванов Иван Иванович", "+7-999-123-45-67", "ivanov@example.com", 
                     "г. Москва, ул. Примерная, д. 1", "ООО Пример", 
                     "Тестовый клиент", "active"),
                    ("Петрова Анна Сергеевна", "+7-999-987-65-43", "petrova@example.com",
                     "г. СПб, пр. Тестовый, д. 5", "", "Другая тестовая запись", "active"),
                    ("Сидоров Михаил Петрович", "+7-999-111-22-33", "sidorov@example.com",
                     "г. Казань, ул. Примерная, д. 15", "ИП Сидоров", "Пробная запись", "active")
                ]
                cursor.executemany("""
                    INSERT INTO clients (full_name, phone, email, address, company, notes, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, test_data)
            
            cursor.execute("SELECT COUNT(*) FROM services")
            if cursor.fetchone()[0] == 0:
                test_services = [
                    ("Консультация", "Первичная правовая консультация", 5000, 2, "Консультация", 1),
                    ("Составление договора", "Подготовка и анализ договора", 15000, 4, "Документооборот", 1),
                    ("Представительство в суде", "Представительство интересов в суде", 25000, 6, "Судебная защита", 1),
                    ("Регистрация ИП", "Регистрация индивидуального предпринимателя", 8000, 3, "Регистрация", 1)
                ]
                cursor.executemany("""
                    INSERT INTO services (name, description, price, duration_hours, category, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, test_services)
            
            # Добавляем пользователя по умолчанию
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO users (username, password, full_name, email)
                    VALUES (?, ?, ?, ?)
                """, ("admin", "admin123", "Администратор", "admin@example.com"))
            
            conn.commit()
            conn.close()
            print("База данных успешно инициализирована")
            
        except Exception as e:
            print(f"Ошибка при инициализации базы данных: {e}")
    
    def get_connection(self):
        """Получение подключения к базе данных"""
        try:
            conn = sqlite3.connect(self.db_name)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            print(f"Ошибка подключения к базе: {e}")
            return None

# Инициализация базы данных
db = WebDatabase()

# ==================== АУТЕНТИФИКАЦИЯ ====================

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    """API для входа в систему"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'error': 'Username и password обязательны'}), 400
        
        conn = db.get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ? AND is_active = 1", 
                      (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'full_name': user['full_name'],
                    'email': user['email']
                }
            })
        else:
            return jsonify({'error': 'Неверные учетные данные'}), 401
            
    except Exception as e:
        print(f"Ошибка аутентификации: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/check')
def api_auth_check():
    """API для проверки аутентификации"""
    try:
        if 'user_id' in session:
            return jsonify({
                'authenticated': True,
                'user': {
                    'id': session['user_id'],
                    'username': session['username'],
                    'full_name': session['full_name']
                }
            })
        else:
            return jsonify({'authenticated': False})
            
    except Exception as e:
        print(f"Ошибка проверки аутентификации: {e}")
        return jsonify({'authenticated': False})

@app.route('/api/auth/logout')
def api_auth_logout():
    """API для выхода из системы"""
    try:
        session.clear()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Ошибка выхода: {e}")
        return jsonify({'error': str(e)}), 500

# ==================== ОСНОВНЫЕ МАРШРУТЫ ====================

@app.route('/')
def index():
    """Главная страница"""
    try:
        template_name = 'index.html'
        return render_template(template_name)
    except Exception as e:
        print(f"Ошибка при загрузке главной страницы: {e}")
        return f"Ошибка при загрузке страницы: {e}", 500

@app.route('/login')
def login():
    """Страница входа"""
    try:
        template_name = 'login.html'
        return render_template(template_name)
    except Exception as e:
        print(f"Ошибка при загрузке страницы входа: {e}")
        return f"Ошибка при загрузке страницы входа: {e}", 500

@app.route('/api/clients')
def api_clients():
    """API для получения списка клиентов"""
    try:
        conn = db.get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*, COUNT(case_id) as cases_count 
            FROM clients c 
            LEFT JOIN cases ca ON c.id = ca.client_id 
            GROUP BY c.id 
            ORDER BY c.registration_date DESC
        """)
        
        clients = []
        for row in cursor.fetchall():
            clients.append({
                'id': row['id'],
                'full_name': row['full_name'],
                'phone': row['phone'],
                'email': row['email'],
                'address': row['address'],
                'company': row['company'],
                'registration_date': row['registration_date'],
                'notes': row['notes'],
                'status': row['status'],
                'cases_count': row['cases_count']
            })
        
        conn.close()
        return jsonify({'clients': clients})
        
    except Exception as e:
        print(f"Ошибка API клиентов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cases')
def api_cases():
    """API для получения списка дел"""
    try:
        conn = db.get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ca.*, c.full_name as client_name, s.name as service_name
            FROM cases ca
            LEFT JOIN clients c ON ca.client_id = c.id
            LEFT JOIN services s ON ca.service_id = s.id
            ORDER BY ca.created_at DESC
        """)
        
        cases = []
        for row in cursor.fetchall():
            cases.append({
                'id': row['id'],
                'client_id': row['client_id'],
                'client_name': row['client_name'],
                'service_id': row['service_id'],
                'service_name': row['service_name'],
                'title': row['title'],
                'description': row['description'],
                'status': row['status'],
                'priority': row['priority'],
                'start_date': row['start_date'],
                'end_date': row['end_date'],
                'lawyer_assigned': row['lawyer_assigned'],
                'total_hours': row['total_hours'],
                'hourly_rate': row['hourly_rate'],
                'total_cost': row['total_cost'],
                'created_at': row['created_at']
            })
        
        conn.close()
        return jsonify({'cases': cases})
        
    except Exception as e:
        print(f"Ошибка API дел: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/services')
def api_services():
    """API для получения списка услуг"""
    try:
        conn = db.get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM services WHERE is_active = 1 ORDER BY name")
        
        services = []
        for row in cursor.fetchall():
            services.append({
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'price': row['price'],
                'duration_hours': row['duration_hours'],
                'category': row['category'],
                'is_active': row['is_active']
            })
        
        conn.close()
        return jsonify({'services': services})
        
    except Exception as e:
        print(f"Ошибка API услуг: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/payments')
def api_payments():
    """API для получения списка платежей"""
    try:
        conn = db.get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, c.title as case_title, cl.full_name as client_name
            FROM payments p
            LEFT JOIN cases c ON p.case_id = c.id
            LEFT JOIN clients cl ON c.client_id = cl.id
            ORDER BY p.payment_date DESC
        """)
        
        payments = []
        for row in cursor.fetchall():
            payments.append({
                'id': row['id'],
                'case_id': row['case_id'],
                'case_title': row['case_title'],
                'client_name': row['client_name'],
                'amount': row['amount'],
                'payment_date': row['payment_date'],
                'payment_method': row['payment_method'],
                'reference_number': row['reference_number'],
                'notes': row['notes'],
                'status': row['status']
            })
        
        conn.close()
        return jsonify({'payments': payments})
        
    except Exception as e:
        print(f"Ошибка API платежей: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/calendar')
def api_calendar():
    """API для получения календарных событий"""
    try:
        conn = db.get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ce.*, c.title as case_title, cl.full_name as client_name
            FROM calendar_events ce
            LEFT JOIN cases c ON ce.case_id = c.id
            LEFT JOIN clients cl ON ce.client_id = cl.id
            ORDER BY ce.event_date, ce.event_time
        """)
        
        events = []
        for row in cursor.fetchall():
            events.append({
                'id': row['id'],
                'case_id': row['case_id'],
                'case_title': row['case_title'],
                'client_id': row['client_id'],
                'client_name': row['client_name'],
                'title': row['title'],
                'description': row['description'],
                'event_date': row['event_date'],
                'event_time': row['event_time'],
                'duration_hours': row['duration_hours'],
                'event_type': row['event_type'],
                'location': row['location'],
                'status': row['status'],
                'created_at': row['created_at']
            })
        
        conn.close()
        return jsonify({'events': events})
        
    except Exception as e:
        print(f"Ошибка API календаря: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents')
def api_documents():
    """API для получения документов"""
    try:
        conn = db.get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.*, c.title as case_title, cl.full_name as client_name
            FROM documents d
            LEFT JOIN cases c ON d.case_id = c.id
            LEFT JOIN clients cl ON d.client_id = cl.id
            ORDER BY d.upload_date DESC
        """)
        
        documents = []
        for row in cursor.fetchall():
            documents.append({
                'id': row['id'],
                'case_id': row['case_id'],
                'case_title': row['case_title'],
                'client_id': row['client_id'],
                'client_name': row['client_name'],
                'title': row['title'],
                'file_path': row['file_path'],
                'file_type': row['file_type'],
                'upload_date': row['upload_date'],
                'uploaded_by': row['uploaded_by']
            })
        
        conn.close()
        return jsonify({'documents': documents})
        
    except Exception as e:
        print(f"Ошибка API документов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard')
def api_dashboard():
    """API для получения статистики дашборда"""
    try:
        conn = db.get_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        
        # Подсчет клиентов
        cursor.execute("SELECT COUNT(*) FROM clients WHERE status = 'active'")
        active_clients = cursor.fetchone()[0]
        
        # Подсчет дел
        cursor.execute("SELECT COUNT(*) FROM cases")
        total_cases = cursor.fetchone()[0]
        
        # Подсчет активных дел
        cursor.execute("SELECT COUNT(*) FROM cases WHERE status != 'completed'")
        active_cases = cursor.fetchone()[0]
        
        # Подсчет платежей за месяц
        cursor.execute("""
            SELECT SUM(amount) FROM payments 
            WHERE strftime('%Y-%m', payment_date) = strftime('%Y-%m', 'now')
        """)
        monthly_revenue = cursor.fetchone()[0] or 0
        
        # Подсчет предстоящих событий
        cursor.execute("""
            SELECT COUNT(*) FROM calendar_events 
            WHERE date(event_date) >= date('now') AND status = 'scheduled'
        """)
        upcoming_events = cursor.fetchone()[0]
        
        # Дела по статусам
        cursor.execute("""
            SELECT status, COUNT(*) as count FROM cases 
            GROUP BY status
        """)
        cases_by_status = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Дела по приоритетам
        cursor.execute("""
            SELECT priority, COUNT(*) as count FROM cases 
            GROUP BY priority
        """)
        cases_by_priority = {row['priority']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        dashboard_data = {
            'active_clients': active_clients,
            'total_cases': total_cases,
            'active_cases': active_cases,
            'monthly_revenue': float(monthly_revenue),
            'upcoming_events': upcoming_events,
            'cases_by_status': cases_by_status,
            'cases_by_priority': cases_by_priority,
            'last_updated': datetime.now().isoformat()
        }
        
        return jsonify(dashboard_data)
        
    except Exception as e:
        print(f"Ошибка API дашборда: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/device-info')
def api_device_info():
    """API для получения информации об устройстве"""
    try:
        return jsonify(get_device_info())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/manifest.json')
def manifest():
    """PWA манифест"""
    try:
        return send_from_directory('static', 'manifest.json')
    except Exception as e:
        print(f"Ошибка загрузки манифеста: {e}")
        return {'error': 'Manifest not found'}, 404

@app.route('/sw.js')
def service_worker():
    """Service Worker для PWA"""
    try:
        return send_from_directory('static', 'sw.js')
    except Exception as e:
        print(f"Ошибка загрузки service worker: {e}")
        return 'Service Worker not found', 404

@app.route('/favicon.ico')
def favicon():
    """Иконка сайта"""
    try:
        return send_from_directory('static', 'favicon.ico')
    except:
        return '', 204

if __name__ == '__main__':
    try:
        print(f"Запуск Legal CRM на порту {PORT}")
        print(f"Режим отладки: {DEBUG_MODE}")
        print(f"База данных: {DATABASE_NAME}")
        print(f"Аутентификация включена")
        print(f"Тестовые учетные данные: admin / admin123")
        app.run(host='0.0.0.0', port=PORT, debug=DEBUG_MODE)
    except Exception as e:
        print(f"Ошибка при запуске приложения: {e}")
