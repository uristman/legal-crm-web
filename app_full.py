"""
Legal CRM Web - API endpoints для полного функционала
Дополнительные методы для редактирования, удаления и получения отдельных записей
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timedelta
import random

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

DATABASE_NAME = 'legal_crm.db'

class WebDatabase:
    def __init__(self, db_name=DATABASE_NAME):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Создаем таблицы (тот же код что и раньше)
        # ... [создание таблиц]
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

db = WebDatabase()

# ==================== ДОПОЛНИТЕЛЬНЫЕ ENDPOINTS ====================

@app.route('/api/clients/<int:client_id>', methods=['GET'])
def get_client(client_id):
    """Получение клиента по ID"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
            client = cursor.fetchone()
            
            if client:
                return jsonify({'success': True, 'data': dict(client)})
            else:
                return jsonify({'success': False, 'error': 'Клиент не найден'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cases/<int:case_id>', methods=['GET'])
def get_case(case_id):
    """Получение дела по ID"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.*, cl.full_name as client_name
                FROM cases c
                JOIN clients cl ON c.client_id = cl.id
                WHERE c.id = ?
            """, (case_id,))
            case = cursor.fetchone()
            
            if case:
                return jsonify({'success': True, 'data': dict(case)})
            else:
                return jsonify({'success': False, 'error': 'Дело не найдено'})
    except Exception as e:
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
        return jsonify({'success': False, 'error': str(e)})

# ==================== DEMO DATA ====================

@app.route('/api/demo-data', methods=['POST'])
def create_demo_data():
    """Создание демонстрационных данных"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Демонстрационные клиенты
            demo_clients = [
                ('Иванов Иван Иванович', '+7-999-123-45-67', 'ivanov@example.com', 'г. Москва, ул. Тверская, д. 10', '4510 123456', '1234567890', 'Постоянный клиент'),
                ('Петрова Елена Алексеевна', '+7-999-234-56-78', 'petrova@example.com', 'г. Санкт-Петербург, пр. Невский, д. 25', '4510 234567', '2345678901', 'Корпоративный клиент'),
                ('Сидоров Михаил Петрович', '+7-999-345-67-89', 'sidorov@example.com', 'г. Екатеринбург, ул. Ленина, д. 50', '4510 345678', '3456789012', 'Новый клиент'),
                ('Козлова Анна Викторовна', '+7-999-456-78-90', 'kozlova@example.com', 'г. Новосибирск, ул. Красный проспект, д. 100', '4510 456789', '4567890123', 'VIP клиент'),
                ('Морозов Дмитрий Сергеевич', '+7-999-567-89-01', 'morozov@example.com', 'г. Казань, ул. Баумана, д. 15', '4510 567890', '5678901234', 'Проблемное дело')
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
                (client_ids[0], 'А40-123456/2024', 'Арбитражный суд г. Москвы', 'Экономический спор', 'ООО "Ромашка"', 'ИП Иванов И.И.', 500000.00, 'Подготовка к судебному заседанию'),
                (client_ids[1], '2-1234/2024', 'Суд общей юрисдикции г. Санкт-Петербурга', 'Семейное право', 'Петрова Е.А.', 'Сидоров С.С.', 0, 'Развод и раздел имущества'),
                (client_ids[2], 'А40-234567/2024', 'Арбитражный суд г. Москвы', 'Трудовой спор', 'ПАО "Газпром"', 'Сидоров М.П.', 150000.00, 'Восстановление на работе'),
                (client_ids[3], '1-123/2024', 'Суд общей юрисдикции г. Новосибирска', 'Уголовное дело', 'Государство', 'Козлов А.В.', 0, 'Защита по уголовному делу'),
                (client_ids[4], 'А40-345678/2024', 'Арбитражный суд г. Москвы', 'Налоговый спор', 'ИФНС России №1', 'Морозов Д.С.', 2500000.00, 'Обжалование решения налоговой')
            ]
            
            case_ids = []
            for case_data in demo_cases:
                cursor.execute("""
                    INSERT INTO cases (client_id, case_number, court_name, case_type,
                                     plaintiff, defendant, claim_amount, case_stage, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, case_data)
                case_ids.append(cursor.lastrowid)
            
            # Демонстрационные услуги
            today = datetime.now()
            demo_services = [
                (client_ids[0], case_ids[0], 'Консультация', 'Первичная консультация по делу', 
                 (today - timedelta(days=30)).strftime('%Y-%m-%d'), 2.0, 15000.00, 'Консультация по экономическому спору'),
                (client_ids[1], case_ids[1], 'Подготовка документов', 'Составление искового заявления', 
                 (today - timedelta(days=25)).strftime('%Y-%m-%d'), 4.0, 25000.00, 'Исковое заявление о разводе'),
                (client_ids[2], case_ids[2], 'Представительство', 'Участие в судебном заседании', 
                 (today - timedelta(days=20)).strftime('%Y-%m-%d'), 6.0, 30000.00, 'Судебное заседание по трудовому спору'),
                (client_ids[3], case_ids[3], 'Защита', 'Подготовка к суду', 
                 (today - timedelta(days=15)).strftime('%Y-%m-%d'), 8.0, 40000.00, 'Подготовка материалов защиты'),
                (client_ids[4], case_ids[4], 'Обжалование', 'Подготовка апелляционной жалобы', 
                 (today - timedelta(days=10)).strftime('%Y-%m-%d'), 12.0, 60000.00, 'Апелляционная жалоба в налоговый спор'),
                (client_ids[0], case_ids[0], 'Обжалование', 'Подготовка апелляции', 
                 (today - timedelta(days=5)).strftime('%Y-%m-%d'), 3.0, 20000.00, 'Апелляционная жалоба')
            ]
            
            for service_data in demo_services:
                cursor.execute("""
                    INSERT INTO services (client_id, case_id, service_type, description,
                                        service_date, hours, cost, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, service_data)
            
            # Демонстрационные платежи
            demo_payments = [
                (client_ids[0], case_ids[0], None, 'Оплата услуг', 20000.00, 
                 (today - timedelta(days=28)).strftime('%Y-%m-%d'), 'Банковский перевод', 'INV-001', 'Аванс за консультацию'),
                (client_ids[1], case_ids[1], None, 'Оплата услуг', 25000.00, 
                 (today - timedelta(days=23)).strftime('%Y-%m-%d'), 'Карта', 'INV-002', 'Оплата за составление иска'),
                (client_ids[2], case_ids[2], None, 'Оплата услуг', 30000.00, 
                 (today - timedelta(days=18)).strftime('%Y-%m-%d'), 'Наличные', 'INV-003', 'Оплата за представительство'),
                (client_ids[3], case_ids[3], None, 'Оплата услуг', 40000.00, 
                 (today - timedelta(days=13)).strftime('%Y-%m-%d'), 'Банковский перевод', 'INV-004', 'Оплата за защиту'),
                (client_ids[4], case_ids[4], None, 'Оплата услуг', 50000.00, 
                 (today - timedelta(days=8)).strftime('%Y-%m-%d'), 'Банковский перевод', 'INV-005', 'Частичная оплата'),
                (client_ids[0], case_ids[0], None, 'Оплата услуг', 15000.00, 
                 (today - timedelta(days=3)).strftime('%Y-%m-%d'), 'Сбербанк Онлайн', 'INV-006', 'Оплата за апелляцию')
            ]
            
            for payment_data in demo_payments:
                cursor.execute("""
                    INSERT INTO payments (client_id, case_id, service_id, payment_type,
                                        amount, payment_date, payment_method, invoice_number, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, payment_data)
            
            # Демонстрационные события
            demo_events = [
                (None, case_ids[0], 'Судебное заседание', 'Предварительное слушание по делу',
                 (today + timedelta(days=7)).strftime('%Y-%m-%d'), '10:00', 
                 'Арбитражный суд г. Москвы, зал 101', 'Подготовить все документы'),
                (None, case_ids[1], 'Встреча с клиентом', 'Обсуждение позиции по делу',
                 (today + timedelta(days=3)).strftime('%Y-%m-%d'), '14:30', 
                 'Офис клиента', 'Обсудить детали дела'),
                (None, case_ids[2], 'Документооборот', 'Подача документов в суд',
                 (today + timedelta(days=1)).strftime('%Y-%m-%d'), '09:00', 
                 'Арбитражный суд г. Москвы', 'Отнести документы в канцелярию'),
                (None, case_ids[4], 'Судебное заседание', 'Рассмотрение апелляционной жалобы',
                 (today + timedelta(days=14)).strftime('%Y-%m-%d'), '11:00', 
                 'Арбитражный суд г. Москвы, зал 205', 'Подготовить выступление'),
                (client_ids[0], None, 'Консультация', 'Плановый звонок клиенту',
                 today.strftime('%Y-%m-%d'), '16:00', 
                 'По телефону', 'Обсудить развитие дела')
            ]
            
            for event_data in demo_events:
                cursor.execute("""
                    INSERT INTO events (client_id, case_id, event_type, title,
                                      description, event_date, event_time, location, reminder)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, event_data)
            
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Демонстрационные данные созданы!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    os.makedirs('static', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    print("🚀 Запуск веб-версии Legal CRM...")
    print("📡 Сервер доступен по адресу: http://localhost:5000")
    print("⚖️  Legal CRM Web - Система для юристов")
    print("💡 Для создания демо-данных перейдите на /api/demo-data (POST)")
    
    app.run(debug=True, host='0.0.0.0', port=5000)