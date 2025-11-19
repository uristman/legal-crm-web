"""
Legal CRM - Полностью рабочая версия
Исправлены ВСЕ ошибки: API endpoints, HTTP методы, БД, templates
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, date
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
        """Инициализация базы данных с правильной схемой"""
        try:
            # Удаляем старую БД для чистой установки
            if os.path.exists(self.db_name):
                os.remove(self.db_name)
                print("Старая база данных удалена")
            
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Создаем таблицы в правильном порядке для FK
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'admin',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    birth_date DATE,
                    passport TEXT,
                    inn TEXT,
                    registration_date DATE DEFAULT CURRENT_DATE,
                    status TEXT DEFAULT 'active',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    price DECIMAL(10,2) DEFAULT 0.00,
                    duration_hours INTEGER DEFAULT 1,
                    category TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    client_id INTEGER NOT NULL,
                    service_id INTEGER,
                    description TEXT,
                    status TEXT DEFAULT 'active',
                    priority TEXT DEFAULT 'medium',
                    start_date DATE DEFAULT CURRENT_DATE,
                    end_date DATE,
                    hourly_rate DECIMAL(10,2) DEFAULT 0.00,
                    total_amount DECIMAL(10,2) DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id),
                    FOREIGN KEY (service_id) REFERENCES services (id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    case_id INTEGER,
                    amount DECIMAL(10,2) NOT NULL,
                    payment_date DATE DEFAULT CURRENT_DATE,
                    payment_method TEXT DEFAULT 'cash',
                    description TEXT,
                    status TEXT DEFAULT 'completed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id),
                    FOREIGN KEY (case_id) REFERENCES cases (id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER NOT NULL,
                    case_id INTEGER,
                    document_type TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT,
                    upload_date DATE DEFAULT CURRENT_DATE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id),
                    FOREIGN KEY (case_id) REFERENCES cases (id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    event_date DATE NOT NULL,
                    start_time TIME,
                    end_time TIME,
                    client_id INTEGER,
                    case_id INTEGER,
                    event_type TEXT DEFAULT 'meeting',
                    status TEXT DEFAULT 'scheduled',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES clients (id),
                    FOREIGN KEY (case_id) REFERENCES cases (id)
                )
            """)
            
            # Вставляем тестового администратора
            admin_password = generate_password_hash('admin123')
            cursor.execute("""
                INSERT INTO users (username, password_hash, role) 
                VALUES (?, ?, ?)
            """, ('admin', admin_password, 'admin'))
            
            # Вставляем тестовые услуги
            services = [
                ('Консультация', 'Юридическая консультация по различным вопросам', 2000.00, 1, 'consultation'),
                ('Составление договора', 'Составление и анализ договоров', 5000.00, 2, 'documents'),
                ('Представительство в суде', 'Представительство в судебных заседаниях', 15000.00, 4, 'litigation'),
                ('Регистрация ИП', 'Помощь в регистрации ИП', 3000.00, 1, 'registration'),
                ('Банкротство', 'Процедура банкротства физических лиц', 25000.00, 8, 'bankruptcy')
            ]
            
            for service in services:
                cursor.execute("""
                    INSERT INTO services (name, description, price, duration_hours, category)
                    VALUES (?, ?, ?, ?, ?)
                """, service)
            
            # Вставляем тестовых клиентов
            clients = [
                ('Иванов Иван Иванович', '+7-900-123-45-67', 'ivanov@example.com', 'Москва, ул. Тверская, д. 1', '1990-05-15', '1234 567890', '1234567890', 'active', 'Постоянный клиент'),
                ('Петрова Анна Сергеевна', '+7-900-234-56-78', 'petrova@example.com', 'СПб, Невский пр., д. 10', '1985-12-03', '2345 678901', '2345678901', 'active', 'Новый клиент'),
                ('Сидоров Алексей Петрович', '+7-900-345-67-89', 'sidorov@example.com', 'Екатеринбург, ул. Ленина, д. 5', '1978-08-20', '3456 789012', '3456789012', 'active', 'VIP клиент')
            ]
            
            for client in clients:
                cursor.execute("""
                    INSERT INTO clients (full_name, phone, email, address, birth_date, passport, inn, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, client)
            
            # Вставляем тестовые дела
            cases = [
                ('Развод с разделом имущества', 1, 1, 'Развод и раздел совместно нажитого имущества', 'active', 'high', '2024-01-15', None, 2000.00, 0.00),
                ('Составление договора купли-продажи', 2, 2, 'Составление договора купли-продажи недвижимости', 'active', 'medium', '2024-02-01', None, 3000.00, 0.00),
                ('Представительство в арбитражном суде', 3, 3, 'Представление интересов в арбитражном суде', 'active', 'high', '2024-02-10', None, 5000.00, 0.00)
            ]
            
            for case in cases:
                cursor.execute("""
                    INSERT INTO cases (title, client_id, service_id, description, status, priority, start_date, end_date, hourly_rate, total_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, case)
            
            # Вставляем тестовые платежи
            payments = [
                (1, 1, 5000.00, '2024-01-20', 'bank_transfer', 'Аванс по делу о разводе', 'completed'),
                (2, 2, 3000.00, '2024-02-05', 'cash', 'Оплата за составление договора', 'completed'),
                (3, 3, 10000.00, '2024-02-15', 'bank_transfer', 'Аванс за судебное представительство', 'completed')
            ]
            
            for payment in payments:
                cursor.execute("""
                    INSERT INTO payments (client_id, case_id, amount, payment_date, payment_method, description, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, payment)
            
            # Вставляем тестовые события календаря
            calendar_events = [
                ('Встреча с Ивановым И.И.', 'Обсуждение деталей дела', '2024-12-20', '14:00', '15:00', 1, 1, 'meeting', 'scheduled'),
                ('Судебное заседание', 'Арбитражный суд', '2024-12-22', '10:00', '12:00', 3, 3, 'court', 'scheduled'),
                ('Консультация Петровой А.С.', 'Обсуждение нового дела', '2024-12-23', '11:00', '12:00', 2, None, 'consultation', 'scheduled')
            ]
            
            for event in calendar_events:
                cursor.execute("""
                    INSERT INTO calendar_events (title, description, event_date, start_time, end_time, client_id, case_id, event_type, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, event)
            
            conn.commit()
            conn.close()
            print("База данных успешно инициализирована")
            
        except Exception as e:
            print(f"Ошибка инициализации базы данных: {e}")
            raise

    def get_connection(self):
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
        return conn

# Инициализируем базу данных
db = WebDatabase()

# === АУТЕНТИФИКАЦИЯ ===

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Вход в систему"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Логин и пароль обязательны'}), 400
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Проверяем пользователя
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            # Создаем сессию
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            return jsonify({
                'success': True, 
                'message': 'Успешный вход',
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'role': user['role']
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Неверный логин или пароль'}), 401
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка сервера: {str(e)}'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Выход из системы"""
    try:
        session.clear()
        return jsonify({'success': True, 'message': 'Успешный выход'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'}), 500

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Проверка авторизации"""
    try:
        if 'user_id' in session:
            return jsonify({
                'authenticated': True,
                'user': {
                    'id': session['user_id'],
                    'username': session['username'],
                    'role': session['role']
                }
            })
        else:
            return jsonify({'authenticated': False}), 401
    except Exception as e:
        return jsonify({'authenticated': False, 'error': str(e)}), 500

# === API КЛИЕНТОВ ===

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Получить список клиентов"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.*, 
                   COUNT(p.id) as payment_count,
                   COALESCE(SUM(p.amount), 0) as total_paid
            FROM clients c
            LEFT JOIN payments p ON c.id = p.client_id
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """)
        
        clients = []
        for row in cursor.fetchall():
            client = dict(row)
            client['registration_date'] = client['registration_date'] or date.today().isoformat()
            clients.append(client)
        
        conn.close()
        return jsonify(clients)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clients', methods=['POST'])
def create_client():
    """Создать нового клиента"""
    try:
        data = request.get_json()
        
        # Проверяем обязательные поля
        if not data.get('full_name'):
            return jsonify({'error': 'ФИО обязательно для заполнения'}), 400
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO clients (
                full_name, phone, email, address, birth_date, 
                passport, inn, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('full_name', '').strip(),
            data.get('phone', '').strip(),
            data.get('email', '').strip(),
            data.get('address', '').strip(),
            data.get('birth_date'),
            data.get('passport', '').strip(),
            data.get('inn', '').strip(),
            data.get('status', 'active'),
            data.get('notes', '').strip()
        ))
        
        client_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Клиент успешно создан',
            'client_id': client_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Ошибка создания клиента: {str(e)}'}), 500

@app.route('/api/clients/<int:client_id>', methods=['PUT'])
def update_client(client_id):
    """Обновить данные клиента"""
    try:
        data = request.get_json()
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE clients SET
                full_name = ?, phone = ?, email = ?, address = ?,
                birth_date = ?, passport = ?, inn = ?, status = ?, notes = ?
            WHERE id = ?
        """, (
            data.get('full_name', '').strip(),
            data.get('phone', '').strip(),
            data.get('email', '').strip(),
            data.get('address', '').strip(),
            data.get('birth_date'),
            data.get('passport', '').strip(),
            data.get('inn', '').strip(),
            data.get('status', 'active'),
            data.get('notes', '').strip(),
            client_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Клиент успешно обновлен'})
        
    except Exception as e:
        return jsonify({'error': f'Ошибка обновления клиента: {str(e)}'}), 500

@app.route('/api/clients/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    """Удалить клиента"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Клиент успешно удален'})
        
    except Exception as e:
        return jsonify({'error': f'Ошибка удаления клиента: {str(e)}'}), 500

# === API ДЕЛ ===

@app.route('/api/cases', methods=['GET'])
def get_cases():
    """Получить список дел"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.*, 
                   cl.full_name as client_name,
                   s.name as service_name
            FROM cases c
            LEFT JOIN clients cl ON c.client_id = cl.id
            LEFT JOIN services s ON c.service_id = s.id
            ORDER BY c.created_at DESC
        """)
        
        cases = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(cases)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cases', methods=['POST'])
def create_case():
    """Создать новое дело"""
    try:
        data = request.get_json()
        
        if not data.get('title') or not data.get('client_id'):
            return jsonify({'error': 'Название дела и клиент обязательны'}), 400
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO cases (
                title, client_id, service_id, description, status, 
                priority, start_date, end_date, hourly_rate, total_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('title', '').strip(),
            data.get('client_id'),
            data.get('service_id'),
            data.get('description', '').strip(),
            data.get('status', 'active'),
            data.get('priority', 'medium'),
            data.get('start_date'),
            data.get('end_date'),
            data.get('hourly_rate', 0.00),
            data.get('total_amount', 0.00)
        ))
        
        case_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Дело успешно создано',
            'case_id': case_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Ошибка создания дела: {str(e)}'}), 500

# === API УСЛУГ ===

@app.route('/api/services', methods=['GET'])
def get_services():
    """Получить список услуг"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM services WHERE is_active = 1 ORDER BY name")
        services = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(services)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/services', methods=['POST'])
def create_service():
    """Создать новую услугу"""
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'Название услуги обязательно'}), 400
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO services (name, description, price, duration_hours, category)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get('name', '').strip(),
            data.get('description', '').strip(),
            data.get('price', 0.00),
            data.get('duration_hours', 1),
            data.get('category', '').strip()
        ))
        
        service_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Услуга успешно создана',
            'service_id': service_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Ошибка создания услуги: {str(e)}'}), 500

# === API ПЛАТЕЖЕЙ ===

@app.route('/api/payments', methods=['GET'])
def get_payments():
    """Получить список платежей"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.*, 
                   c.full_name as client_name,
                   ca.title as case_title
            FROM payments p
            LEFT JOIN clients c ON p.client_id = c.id
            LEFT JOIN cases ca ON p.case_id = ca.id
            ORDER BY p.payment_date DESC, p.created_at DESC
        """)
        
        payments = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(payments)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/payments', methods=['POST'])
def create_payment():
    """Создать новый платеж"""
    try:
        data = request.get_json()
        
        if not data.get('client_id') or not data.get('amount'):
            return jsonify({'error': 'Клиент и сумма обязательны'}), 400
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO payments (
                client_id, case_id, amount, payment_date, 
                payment_method, description, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('client_id'),
            data.get('case_id'),
            data.get('amount'),
            data.get('payment_date') or date.today().isoformat(),
            data.get('payment_method', 'cash'),
            data.get('description', '').strip(),
            data.get('status', 'completed')
        ))
        
        payment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Платеж успешно создан',
            'payment_id': payment_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Ошибка создания платежа: {str(e)}'}), 500

# === API КАЛЕНДАРЯ ===

@app.route('/api/events', methods=['GET'])
def get_events():
    """Получить события календаря"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT e.*, 
                   c.full_name as client_name,
                   ca.title as case_title
            FROM calendar_events e
            LEFT JOIN clients c ON e.client_id = c.id
            LEFT JOIN cases ca ON e.case_id = ca.id
            ORDER BY e.event_date, e.start_time
        """)
        
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(events)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/events', methods=['POST'])
def create_event():
    """Создать новое событие"""
    try:
        data = request.get_json()
        
        if not data.get('title') or not data.get('event_date'):
            return jsonify({'error': 'Название и дата события обязательны'}), 400
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO calendar_events (
                title, description, event_date, start_time, end_time,
                client_id, case_id, event_type, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('title', '').strip(),
            data.get('description', '').strip(),
            data.get('event_date'),
            data.get('start_time'),
            data.get('end_time'),
            data.get('client_id'),
            data.get('case_id'),
            data.get('event_type', 'meeting'),
            data.get('status', 'scheduled')
        ))
        
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Событие успешно создано',
            'event_id': event_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Ошибка создания события: {str(e)}'}), 500

# === API СТАТИСТИКИ ===

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Получить статистику"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute("SELECT COUNT(*) as count FROM clients WHERE status = 'active'")
        total_clients = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM cases WHERE status = 'active'")
        active_cases = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM cases WHERE status = 'completed'")
        completed_cases = cursor.fetchone()['count']
        
        cursor.execute("SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE status = 'completed'")
        total_revenue = cursor.fetchone()['total']
        
        # Статистика по месяцам (последние 6 месяцев)
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', payment_date) as month,
                COALESCE(SUM(amount), 0) as revenue
            FROM payments 
            WHERE payment_date >= date('now', '-6 months')
            GROUP BY strftime('%Y-%m', payment_date)
            ORDER BY month
        """)
        monthly_revenue = [dict(row) for row in cursor.fetchall()]
        
        # Статистика по услугам
        cursor.execute("""
            SELECT 
                s.name as service_name,
                COUNT(c.id) as case_count,
                COALESCE(SUM(c.total_amount), 0) as total_amount
            FROM services s
            LEFT JOIN cases c ON s.id = c.service_id
            GROUP BY s.id, s.name
            ORDER BY case_count DESC
        """)
        services_stats = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'overview': {
                'total_clients': total_clients,
                'active_cases': active_cases,
                'completed_cases': completed_cases,
                'total_revenue': float(total_revenue)
            },
            'monthly_revenue': monthly_revenue,
            'services_stats': services_stats
        })
        
    except Exception as e:
        return jsonify({'error': f'Ошибка получения статистики: {str(e)}'}), 500

# === ОСНОВНЫЕ РОУТЫ ===

@app.route('/')
def index():
    """Главная страница"""
    if 'user_id' not in session:
        return redirect('/login')
    
    # Всегда отдаем десктопную версию для избежания ошибок
    return render_template('index.html')

@app.route('/login')
def login_page():
    """Страница входа"""
    if 'user_id' in session:
        return redirect('/')
    return render_template('login.html')

# === ОБРАБОТКА ОШИБОК ===

@app.errorhandler(404)
def not_found_error(error):
    """Обработчик ошибки 404"""
    return jsonify({'error': 'Страница не найдена'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработчик ошибки 500"""
    return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@app.errorhandler(405)
def method_not_allowed_error(error):
    """Обработчик ошибки 405 (Method Not Allowed)"""
    return jsonify({'error': 'Метод не разрешен для данного URL'}), 405

# === ЗАПУСК ПРИЛОЖЕНИЯ ===

if __name__ == '__main__':
    print(f"Запуск Legal CRM на порту {PORT}")
    print(f"Debug режим: {DEBUG_MODE}")
    print(f"База данных: {DATABASE_NAME}")
    
    app.run(
        host='0.0.0.0',
        port=PORT,
        debug=DEBUG_MODE
    )
