#!/usr/bin/env python3
"""
Тест системы аутентификации Legal CRM Web
Проверяет работу всех компонентов безопасности
"""

import requests
import json
import time
import sys

class AuthTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def print_test(self, test_name, status, message=""):
        """Красивый вывод результатов теста"""
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {test_name}")
        if message:
            print(f"   {message}")
        print()
    
    def test_1_check_auth_required(self):
        """Тест 1: Проверка требования аутентификации"""
        try:
            response = self.session.get(f"{self.base_url}/api/clients")
            
            if response.status_code == 401:
                self.print_test("Тест 1: API требует аутентификацию", True, "API корректно блокирует доступ")
                return True
            else:
                self.print_test("Тест 1: API требует аутентификацию", False, f"Статус: {response.status_code} (ожидался 401)")
                return False
        except Exception as e:
            self.print_test("Тест 1: API требует аутентификацию", False, f"Ошибка: {str(e)}")
            return False
    
    def test_2_login_page_accessible(self):
        """Тест 2: Проверка доступности страницы входа"""
        try:
            response = self.session.get(f"{self.base_url}/login")
            
            if response.status_code == 200:
                self.print_test("Тест 2: Страница входа доступна", True, "Страница /login загружается")
                return True
            else:
                self.print_test("Тест 2: Страница входа доступна", False, f"Статус: {response.status_code}")
                return False
        except Exception as e:
            self.print_test("Тест 2: Страница входа доступна", False, f"Ошибка: {str(e)}")
            return False
    
    def test_3_successful_login(self):
        """Тест 3: Успешная аутентификация"""
        try:
            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('user'):
                    self.print_test("Тест 3: Успешная аутентификация", True, 
                                  f"Пользователь: {data['user']['username']}")
                    return True
                else:
                    self.print_test("Тест 3: Успешная аутентификация", False, 
                                  f"Неверный ответ: {data}")
                    return False
            else:
                self.print_test("Тест 3: Успешная аутентификация", False, 
                              f"Статус: {response.status_code}")
                return False
        except Exception as e:
            self.print_test("Тест 3: Успешная аутентификация", False, f"Ошибка: {str(e)}")
            return False
    
    def test_4_api_access_after_login(self):
        """Тест 4: Доступ к API после аутентификации"""
        try:
            response = self.session.get(f"{self.base_url}/api/clients")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.print_test("Тест 4: API доступен после аутентификации", True, 
                                  "Запросы к API работают корректно")
                    return True
                else:
                    self.print_test("Тест 4: API доступен после аутентификации", False, 
                                  f"Неверный ответ API: {data}")
                    return False
            else:
                self.print_test("Тест 4: API доступен после аутентификации", False, 
                              f"Статус: {response.status_code}")
                return False
        except Exception as e:
            self.print_test("Тест 4: API доступен после аутентификации", False, f"Ошибка: {str(e)}")
            return False
    
    def test_5_invalid_login(self):
        """Тест 5: Неверные учетные данные"""
        try:
            login_data = {
                "username": "admin",
                "password": "wrong_password"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 401:
                self.print_test("Тест 5: Неверные учетные данные", True, 
                              "Система корректно отклоняет неверные пароли")
                return True
            else:
                self.print_test("Тест 5: Неверные учетные данные", False, 
                              f"Статус: {response.status_code} (ожидался 401)")
                return False
        except Exception as e:
            self.print_test("Тест 5: Неверные учетные данные", False, f"Ошибка: {str(e)}")
            return False
    
    def test_6_logout(self):
        """Тест 6: Выход из системы"""
        try:
            response = self.session.post(f"{self.base_url}/api/auth/logout")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    # Проверяем, что после выхода API снова блокируется
                    time.sleep(1)
                    api_response = self.session.get(f"{self.base_url}/api/clients")
                    if api_response.status_code == 401:
                        self.print_test("Тест 6: Выход из системы", True, 
                                      "Выход работает корректно")
                        return True
                    else:
                        self.print_test("Тест 6: Выход из системы", False, 
                                      "API остается доступным после выхода")
                        return False
                else:
                    self.print_test("Тест 6: Выход из системы", False, 
                                  f"Неверный ответ: {data}")
                    return False
            else:
                self.print_test("Тест 6: Выход из системы", False, 
                              f"Статус: {response.status_code}")
                return False
        except Exception as e:
            self.print_test("Тест 6: Выход из системы", False, f"Ошибка: {str(e)}")
            return False
    
    def test_7_authentication_check(self):
        """Тест 7: Проверка статуса аутентификации"""
        try:
            response = self.session.get(f"{self.base_url}/api/auth/check")
            
            if response.status_code == 200:
                data = response.json()
                if 'authenticated' in data:
                    self.print_test("Тест 7: Проверка статуса аутентификации", True, 
                                  "Endpoint /api/auth/check работает")
                    return True
                else:
                    self.print_test("Тест 7: Проверка статуса аутентификации", False, 
                                  f"Неверный ответ: {data}")
                    return False
            else:
                self.print_test("Тест 7: Проверка статуса аутентификации", False, 
                              f"Статус: {response.status_code}")
                return False
        except Exception as e:
            self.print_test("Тест 7: Проверка статуса аутентификации", False, f"Ошибка: {str(e)}")
            return False
    
    def test_8_session_security(self):
        """Тест 8: Безопасность сессий"""
        try:
            # Заходим под правильными учетными данными
            login_data = {"username": "admin", "password": "admin123"}
            self.session.post(f"{self.base_url}/api/auth/login", json=login_data)
            
            # Проверяем, что сессия активна
            response1 = self.session.get(f"{self.base_url}/api/auth/check")
            data1 = response1.json()
            
            # Попытка получить доступ с другим session
            other_session = requests.Session()
            response2 = other_session.get(f"{self.base_url}/api/auth/check")
            data2 = response2.json()
            
            if data1.get('authenticated') == True and data2.get('authenticated') == False:
                self.print_test("Тест 8: Безопасность сессий", True, 
                              "Сессии корректно изолированы")
                return True
            else:
                self.print_test("Тест 8: Безопасность сессий", False, 
                              "Сессии работают некорректно")
                return False
        except Exception as e:
            self.print_test("Тест 8: Безопасность сессий", False, f"Ошибка: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        print("=" * 60)
        print("🧪 ТЕСТИРОВАНИЕ СИСТЕМЫ АУТЕНТИФИКАЦИИ LEGAL CRM")
        print("=" * 60)
        print()
        
        # Ждем запуска сервера
        print("⏳ Подключение к серверу...")
        try:
            response = requests.get(f"{self.base_url}/login", timeout=5)
            print("✅ Сервер доступен")
        except:
            print("❌ Сервер недоступен. Запустите приложение командой: python app.py")
            return False
        
        print()
        
        # Запуск тестов
        tests = [
            self.test_1_check_auth_required,
            self.test_2_login_page_accessible,
            self.test_7_authentication_check,
            self.test_3_successful_login,
            self.test_4_api_access_after_login,
            self.test_5_invalid_login,
            self.test_6_logout,
            self.test_8_session_security
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
            time.sleep(0.5)  # Пауза между тестами
        
        print("=" * 60)
        print(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        print("=" * 60)
        print(f"Пройдено тестов: {passed}/{total}")
        
        if passed == total:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система аутентификации работает корректно.")
            return True
        else:
            print("⚠️  Некоторые тесты не пройдены. Проверьте настройки.")
            return False

if __name__ == "__main__":
    # Проверяем аргументы командной строки
    base_url = "http://localhost:5000"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print(f"Тестирование системы аутентификации на: {base_url}")
    print()
    
    tester = AuthTester(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)