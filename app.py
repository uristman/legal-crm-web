"""
Веб-версия Legal CRM - Flask Backend (ИСПРАВЛЕННАЯ ВЕРСИЯ)
Система учета клиентов и активностей для юридической практики
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session, flash
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
import sqlite3
import os
from datetime import datetime
import json
import uuid

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
            
            # Таблица действий
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
                'recent_activities': recent_activities
            }
            
            return jsonify({'success': True, 'stats': stats})
            
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
    print(f"🌐 Сервер запущен на порту {PORT}")
    
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG_MODE)
