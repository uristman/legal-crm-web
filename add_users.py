#!/usr/bin/env python3
"""
🔐 Скрипт для управления пользователями Legal CRM
Использование: python add_users.py
"""

import sqlite3
import sys
import os
from werkzeug.security import generate_password_hash

# Добавим путь к папке с базой данных
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_db_path():
    """Определяем путь к базе данных"""
    # Для локального запуска
    if os.path.exists('legal_crm.db'):
        return 'legal_crm.db'
    
    # Для запуска в папке проекта
    project_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'legal_crm.db')
    if os.path.exists(project_path):
        return project_path
        
    # Для Render.com - используем переменную окружения или стандартное имя
    db_name = os.environ.get('DATABASE_NAME', 'legal_crm.db')
    return db_name

def add_user(username, password, email, full_name, role='user'):
    """Добавление нового пользователя"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли пользователь
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            print(f"❌ Пользователь '{username}' уже существует!")
            conn.close()
            return False
        
        # Хешируем пароль
        password_hash = generate_password_hash(password)
        
        # Добавляем пользователя
        cursor.execute("""
            INSERT INTO users (username, password_hash, email, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (username, password_hash, email, full_name, role))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Пользователь '{username}' успешно создан!")
        print(f"   📧 Email: {email}")
        print(f"   👤 Полное имя: {full_name}")
        print(f"   🏷️ Роль: {role}")
        print(f"   🔑 Пароль: {password}")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании пользователя: {e}")
        return False

def change_password(username, new_password):
    """Изменение пароля пользователя"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли пользователь
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if not cursor.fetchone():
            print(f"❌ Пользователь '{username}' не найден!")
            conn.close()
            return False
        
        # Хешируем новый пароль
        password_hash = generate_password_hash(new_password)
        
        # Обновляем пароль
        cursor.execute("""
            UPDATE users 
            SET password_hash = ? 
            WHERE username = ?
        """, (password_hash, username))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Пароль для пользователя '{username}' успешно изменен!")
        print(f"   🔑 Новый пароль: {new_password}")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при изменении пароля: {e}")
        return False

def delete_user(username):
    """Удаление пользователя"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли пользователь
        cursor.execute("SELECT id, role FROM users WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        if not user_data:
            print(f"❌ Пользователь '{username}' не найден!")
            conn.close()
            return False
            
        # Нельзя удалять последнего администратора
        if user_data[1] == 'admin':
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            admin_count = cursor.fetchone()[0]
            if admin_count <= 1:
                print(f"❌ Нельзя удалить последнего администратора!")
                conn.close()
                return False
        
        # Удаляем пользователя
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Пользователь '{username}' успешно удален!")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при удалении пользователя: {e}")
        return False

def list_users():
    """Показать всех пользователей"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, full_name, role, created_at 
            FROM users 
            ORDER BY created_at
        """)
        
        users = cursor.fetchall()
        conn.close()
        
        print("👥 Список пользователей:")
        print("=" * 80)
        print(f"{'ID':<3} {'Логин':<15} {'Email':<25} {'Полное имя':<20} {'Роль':<8} {'Создан':<15}")
        print("-" * 80)
        
        for user in users:
            print(f"{user[0]:<3} {user[1]:<15} {user[2]:<25} {user[3]:<20} {user[4]:<8} {user[5]:<15}")
        
        print()
        print(f"Всего пользователей: {len(users)}")
        
        # Показываем статистику по ролям
        role_stats = {}
        for user in users:
            role = user[4]
            role_stats[role] = role_stats.get(role, 0) + 1
        
        print("Статистика по ролям:")
        for role, count in role_stats.items():
            print(f"  {role}: {count}")
        print()
        
        return len(users)
        
    except Exception as e:
        print(f"❌ Ошибка при получении списка пользователей: {e}")
        return 0

def generate_random_password(length=12):
    """Генерация случайного пароля"""
    import random
    import string
    
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choice(chars) for _ in range(length))
    return password

def interactive_mode():
    """Интерактивный режим"""
    print("🔐 Управление пользователями Legal CRM")
    print("=" * 50)
    
    while True:
        print("\nВыберите действие:")
        print("1. Показать всех пользователей")
        print("2. Добавить нового пользователя")
        print("3. Изменить пароль пользователя")
        print("4. Удалить пользователя")
        print("5. Создать случайного пользователя")
        print("0. Выход")
        
        choice = input("\nВведите номер действия: ").strip()
        
        if choice == '1':
            list_users()
            
        elif choice == '2':
            print("\n📝 Добавление нового пользователя:")
            username = input("Логин: ").strip()
            email = input("Email: ").strip()
            full_name = input("Полное имя: ").strip()
            role = input("Роль (user/lawyer/admin) [user]: ").strip() or 'user'
            password = input("Пароль (или оставьте пустым для генерации): ").strip()
            
            if not password:
                password = generate_random_password()
                print(f"🔑 Сгенерированный пароль: {password}")
            
            add_user(username, password, email, full_name, role)
            
        elif choice == '3':
            print("\n🔑 Изменение пароля пользователя:")
            username = input("Логин пользователя: ").strip()
            new_password = input("Новый пароль: ").strip()
            change_password(username, new_password)
            
        elif choice == '4':
            print("\n🗑️ Удаление пользователя:")
            username = input("Логин пользователя для удаления: ").strip()
            confirm = input(f"Вы уверены, что хотите удалить пользователя '{username}'? (да/нет): ").strip().lower()
            if confirm == 'да':
                delete_user(username)
            
        elif choice == '5':
            print("\n🎲 Создание случайного пользователя:")
            username = input("Логин (или оставьте пустым для автоматической генерации): ").strip()
            email = input("Email: ").strip()
            full_name = input("Полное имя: ").strip()
            role = input("Роль (user/lawyer/admin) [user]: ").strip() or 'user'
            
            if not username:
                username = f"user_{generate_random_password(6).lower()}"
            
            password = generate_random_password()
            add_user(username, password, email, full_name, role)
            
        elif choice == '0':
            print("👋 До свидания!")
            break
            
        else:
            print("❌ Неверный выбор!")

def main():
    """Главная функция"""
    if len(sys.argv) > 1:
        # Командная строка
        command = sys.argv[1].lower()
        
        if command == 'list':
            list_users()
        elif command == 'add' and len(sys.argv) >= 6:
            username = sys.argv[2]
            password = sys.argv[3]
            email = sys.argv[4]
            full_name = sys.argv[5]
            role = sys.argv[6] if len(sys.argv) > 6 else 'user'
            add_user(username, password, email, full_name, role)
        elif command == 'change-password' and len(sys.argv) >= 4:
            username = sys.argv[2]
            new_password = sys.argv[3]
            change_password(username, new_password)
        elif command == 'delete' and len(sys.argv) >= 3:
            username = sys.argv[2]
            delete_user(username)
        elif command == 'interactive':
            interactive_mode()
        else:
            print("Использование:")
            print("  python add_users.py list                           # Показать всех пользователей")
            print("  python add_users.py add <логин> <пароль> <email> <имя> [роль]  # Добавить пользователя")
            print("  python add_users.py change-password <логин> <новый_пароль>     # Изменить пароль")
            print("  python add_users.py delete <логин>                # Удалить пользователя")
            print("  python add_users.py interactive                   # Интерактивный режим")
    else:
        # Интерактивный режим по умолчанию
        interactive_mode()

if __name__ == "__main__":
    main()