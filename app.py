"""
Legal CRM Web - Полностью переписанная версия
Система управления юридической практикой
Автор: MiniMax Agent
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Константы приложения
DATABASE_NAME = os.environ.get('DATABASE_NAME', 'legal_crm.db')
DEBUG_MODE = os.environ.get('DEBUG', 'False').lower() == 'true'
PORT = int(os.environ.get('PORT', 5000))

# Настройки Flask
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'legal-crm-web-secret-key-2025')
app.config['DEBUG'] = DEBUG_MODE
app.secret_key = os.environ.get('SECRET_KEY', 'legal-crm-web-secret-key-2025')

class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_name=DATABASE_NAME):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных и таблиц"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Включаем поддержку внешних ключей
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Создаем таблицы
        self.create_tables(cursor)
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")
    
    def create_tables(self, cursor):
        """Создание всех таблиц"""
        
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
                claim_amount REAL DEFAULT 0,
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
                hours REAL DEFAULT 0,
                cost REAL DEFAULT 0,
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
    
    def get_connection(self):
        """Получение соединения с базой данных"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

# Инициализация базы данных
db = Database()

# ==================== API ENDPOINTS ====================

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/login')
def login():
    """Страница входа"""
    return render_template('login.html')

# ==================== AUTH ENDPOINTS ====================

from flask import session

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """Проверка аутентификации"""
    return jsonify({'authenticated': session.get('logged_in', False), 'username': session.get('username')})

@app.route('/api/auth/login', methods=['POST'])
def login_api():
    """Вход в систему"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Логин и пароль обязательны'})
        
        # Простая проверка авторизации
        if username == 'admin' and password == '12345':
            session['logged_in'] = True
            session['username'] = username
            return jsonify({'success': True, 'message': 'Успешный вход'})
        else:
            return jsonify({'success': False, 'error': 'Неверный логин или пароль'})
            
    except Exception as e:
        logger.error(f"Ошибка авторизации: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Выход из системы"""
    session.clear()
    return jsonify({'success': True, 'message': 'Выход выполнен успешно'})

# ==================== CLIENTS API ====================

@app.route('/api/clients', methods=['GET'])
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
        logger.error(f"Ошибка получения клиентов: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clients', methods=['POST'])
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
        logger.error(f"Ошибка добавления клиента: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clients/<int:client_id>', methods=['PUT'])
def update_client(client_id):
    """Обновление клиента"""
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
                values.append(client_id)
                query = f"UPDATE clients SET {', '.join(fields)} WHERE id = ?"
                cursor.execute(query, values)
                conn.commit()
            
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка обновления клиента: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/clients/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    """Удаление клиента"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            conn.commit()
            
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка удаления клиента: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== CASES API ====================

@app.route('/api/cases', methods=['GET'])
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
        logger.error(f"Ошибка получения дел: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cases', methods=['POST'])
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
        logger.error(f"Ошибка добавления дела: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cases/<int:case_id>', methods=['PUT'])
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
        logger.error(f"Ошибка обновления дела: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cases/<int:case_id>', methods=['DELETE'])
def delete_case(case_id):
    """Удаление дела"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cases WHERE id = ?", (case_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка удаления дела: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== SERVICES API ====================

@app.route('/api/services', methods=['GET'])
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
        logger.error(f"Ошибка получения услуг: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/services', methods=['POST'])
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
        logger.error(f"Ошибка добавления услуги: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/services/<int:service_id>', methods=['PUT'])
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
        logger.error(f"Ошибка обновления услуги: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/services/<int:service_id>', methods=['DELETE'])
def delete_service(service_id):
    """Удаление услуги"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка удаления услуги: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== PAYMENTS API ====================

@app.route('/api/payments', methods=['GET'])
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
        logger.error(f"Ошибка получения платежей: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/payments', methods=['POST'])
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
        logger.error(f"Ошибка добавления платежа: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/payments/<int:payment_id>', methods=['PUT'])
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
        logger.error(f"Ошибка обновления платежа: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/payments/<int:payment_id>', methods=['DELETE'])
def delete_payment(payment_id):
    """Удаление платежа"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка удаления платежа: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== EVENTS API ====================

@app.route('/api/events', methods=['GET'])
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
        logger.error(f"Ошибка получения событий: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/events/<int:event_id>', methods=['GET'])
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
        logger.error(f"Ошибка получения события: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/events', methods=['POST'])
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
        logger.error(f"Ошибка добавления события: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/events/<int:event_id>', methods=['PUT'])
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
        logger.error(f"Ошибка обновления события: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """Удаление события"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка удаления события: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== STATISTICS API ====================

@app.route('/api/statistics', methods=['GET'])
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
        logger.error(f"Ошибка получения статистики: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== DEMO DATA ====================

@app.route('/api/demo-data', methods=['POST'])
def create_demo_data():
    """Создание демонстрационных данных"""
    try:
        from datetime import timedelta
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Очищаем таблицы
            cursor.execute("DELETE FROM events")
            cursor.execute("DELETE FROM payments")
            cursor.execute("DELETE FROM services")
            cursor.execute("DELETE FROM cases")
            cursor.execute("DELETE FROM clients")
            
            # Демонстрационные клиенты
            demo_clients = [
                ('Иванов Иван Иванович', '+7-999-123-45-67', 'ivanov@example.com', 'г. Москва, ул. Тверская, д. 10', '4510 123456', '1234567890', 'Постоянный клиент'),
                ('Петрова Елена Алексеевна', '+7-999-234-56-78', 'petrova@example.com', 'г. Санкт-Петербург, пр. Невский, д. 25', '4510 234567', '2345678901', 'Корпоративный клиент'),
                ('Сидоров Алексей Петрович', '+7-999-345-67-89', 'sidorov@example.com', 'г. Казань, ул. Баумана, д. 58', '4510 345678', '3456789012', 'Новый клиент')
            ]
            
            client_ids = []
            for client_data in demo_clients:
                cursor.execute("""
                    INSERT INTO clients (full_name, phone, email, address, passport_data, inn, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, client_data)
                client_ids.append(cursor.lastrowid)
            
            # Демонстрационные дела
            demo_cases = [
                (client_ids[0], 'А40-123456/2024', 'Арбитражный суд г. Москвы', 'Экономический спор', 'ООО "Ромашка"', 'ИП Иванов И.И.', 500000.00),
                (client_ids[1], '2-1234/2024', 'Суд общей юрисдикции г. Санкт-Петербурга', 'Семейное право', 'Петрова Е.А.', 'Сидоров С.С.', 0),
                (client_ids[2], 'А45-789012/2024', 'Арбитражный суд г. Казани', 'Трудовой спор', 'ООО "Техно"', 'ИП Сидоров А.П.', 150000.00)
            ]
            
            case_ids = []
            for case_data in demo_cases:
                cursor.execute("""
                    INSERT INTO cases (client_id, case_number, court_name, case_type,
                                     plaintiff, defendant, claim_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, case_data)
                case_ids.append(cursor.lastrowid)
            
            # Демонстрационные услуги
            today = datetime.now()
            demo_services = [
                (client_ids[0], case_ids[0], 'Консультация', 'Первичная консультация по делу', 
                 (today - timedelta(days=30)).strftime('%Y-%m-%d'), 2.0, 15000.00),
                (client_ids[1], case_ids[1], 'Подготовка документов', 'Составление искового заявления', 
                 (today - timedelta(days=25)).strftime('%Y-%m-%d'), 4.0, 25000.00),
                (client_ids[2], case_ids[2], 'Представительство', 'Представительство в суде', 
                 (today - timedelta(days=15)).strftime('%Y-%m-%d'), 6.0, 35000.00)
            ]
            
            for service_data in demo_services:
                cursor.execute("""
                    INSERT INTO services (client_id, case_id, service_type, description,
                                        service_date, hours, cost)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, service_data)
            
            # Демонстрационные платежи
            demo_payments = [
                (client_ids[0], case_ids[0], None, 'Оплата услуг', 20000.00, 
                 (today - timedelta(days=28)).strftime('%Y-%m-%d'), 'Банковский перевод', 'INV-001'),
                (client_ids[1], case_ids[1], None, 'Оплата услуг', 25000.00, 
                 (today - timedelta(days=23)).strftime('%Y-%m-%d'), 'Карта', 'INV-002'),
                (client_ids[2], case_ids[2], None, 'Аванс', 20000.00, 
                 (today - timedelta(days=20)).strftime('%Y-%m-%d'), 'Наличные', 'INV-003')
            ]
            
            for payment_data in demo_payments:
                cursor.execute("""
                    INSERT INTO payments (client_id, case_id, service_id, payment_type,
                                        amount, payment_date, payment_method, invoice_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, payment_data)
            
            # Демонстрационные события
            demo_events = [
                (client_ids[0], case_ids[0], 'Судебное заседание', 'Предварительное слушание', 
                 (today + timedelta(days=5)).strftime('%Y-%m-%d'), '10:00', 'Арбитражный суд г. Москвы'),
                (client_ids[1], case_ids[1], 'Консультация', 'Встреча с клиентом', 
                 (today + timedelta(days=2)).strftime('%Y-%m-%d'), '14:00', 'Офис'),
                (client_ids[2], case_ids[2], 'Подача документов', 'Подача апелляции', 
                 (today + timedelta(days=10)).strftime('%Y-%m-%d'), '09:30', 'Арбитражный суд г. Казани')
            ]
            
            for event_data in demo_events:
                cursor.execute("""
                    INSERT INTO events (client_id, case_id, event_type, title,
                                      description, event_date, event_time, location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, event_data)
            
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Демонстрационные данные созданы!'})
    except Exception as e:
        logger.error(f"Ошибка создания демо-данных: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== REPORTS API ====================

@app.route('/api/reports/generate', methods=['POST'])
def generate_report():
    """Генерация отчетов"""
    try:
        data = request.get_json()
        report_type = data.get('type', 'clients')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        status = data.get('status')
        client_id = data.get('client_id')
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Базовый SQL с фильтрами
        base_queries = {
            'clients': "SELECT * FROM clients WHERE 1=1",
            'cases': "SELECT * FROM cases WHERE 1=1",
            'services': "SELECT * FROM services WHERE 1=1",
            'payments': "SELECT * FROM payments WHERE 1=1",
            'events': "SELECT * FROM events WHERE 1=1"
        }
        
        if report_type not in base_queries:
            return jsonify({'success': False, 'error': 'Неверный тип отчета'})
        
        query = base_queries[report_type]
        params = []
        
        # Добавляем фильтры
        if start_date:
            if report_type in ['clients', 'cases', 'services', 'payments', 'events']:
                if report_type == 'clients':
                    query += " AND date(created_date) >= ?"
                elif report_type in ['cases', 'payments']:
                    query += " AND date(start_date) >= ?"
                elif report_type == 'services':
                    query += " AND date(service_date) >= ?"
                elif report_type == 'events':
                    query += " AND date(event_date) >= ?"
                params.append(start_date)
        
        if end_date:
            if report_type in ['clients', 'cases', 'services', 'payments', 'events']:
                if report_type == 'clients':
                    query += " AND date(created_date) <= ?"
                elif report_type in ['cases', 'payments']:
                    query += " AND date(start_date) <= ?"
                elif report_type == 'services':
                    query += " AND date(service_date) <= ?"
                elif report_type == 'events':
                    query += " AND date(event_date) <= ?"
                params.append(end_date)
        
        if client_id and report_type != 'clients':
            query += " AND client_id = ?"
            params.append(client_id)
        
        if status:
            if report_type == 'clients':
                query += " AND status = ?"
            elif report_type == 'cases':
                query += " AND case_stage = ?"
            params.append(status)
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        logger.error(f"Ошибка генерации отчета: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reports/export')
def export_report():
    """Экспорт отчета в Excel"""
    try:
        report_type = request.args.get('type', 'clients')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Заглушка - возвращаем JSON вместо Excel
        # В реальном приложении здесь был бы генератор Excel
        return jsonify({
            'success': True,
            'message': f'Экспорт типа {report_type} за период {start_date} - {end_date}'
        })
    except Exception as e:
        logger.error(f"Ошибка экспорта отчета: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found_error(error):
    """Обработчик 404 ошибок"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработчик 500 ошибок"""
    logger.error(f"Внутренняя ошибка сервера: {error}")
    return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500

# ==================== APPLICATION START ====================

if __name__ == '__main__':
    # Создаем необходимые папки
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    logger.info("🚀 Запуск Legal CRM Web...")
    logger.info(f"📡 Сервер: http://localhost:{PORT}")
    logger.info("⚖️  Legal CRM Web - Полностью переписанная версия")
    
    app.run(debug=DEBUG_MODE, host='0.0.0.0', port=PORT)
