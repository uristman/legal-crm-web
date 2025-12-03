"""
OAuth2 клиент для работы с Яндекс.Диском с поддержкой двухфакторной аутентификации
Обеспечивает авторизацию через OAuth2 и обмен кода подтверждения на токены
"""

import requests
import json
import uuid
import base64
import hashlib
import secrets
import urllib.parse
from typing import Dict, Optional, Tuple


class YandexOAuthClient:
    """OAuth2 клиент для Яндекс.Диска с поддержкой 2FA"""
    
    def __init__(self, client_id: str, client_secret: str = None):
        """
        Инициализация OAuth клиента
        
        Args:
            client_id (str): ID зарегистрированного приложения
            client_secret (str): Секретный ключ приложения (опционально для PKCE)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_url = "https://oauth.yandex.ru/authorize"
        self.token_url = "https://oauth.yandex.ru/token"
        self.redirect_uri = None
        self.state = None
        self.code_verifier = None
        self.code_challenge = None
        
        # Scopes для доступа к Яндекс.Диску
        self.scopes = [
            "disk:read",
            "disk:write"  # Права на запись в любом месте на Диске
        ]
        
    def generate_pkce_pair(self) -> Tuple[str, str]:
        """
        Генерирует PKCE код verifier и challenge
        
        Returns:
            Tuple[str, str]: (code_verifier, code_challenge)
        """
        # Генерируем случайный code_verifier
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        
        # Создаем code_challenge через SHA256
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_authorization_url(self, redirect_uri: str, login_hint: str = None, state: str = None) -> str:
        """
        Получает URL для авторизации пользователя
        
        Args:
            redirect_uri (str): URI для перенаправления после авторизации
            login_hint (str): Предварительное заполнение логина (опционально)
            state (str): Состояние для защиты от CSRF (опционально)
            
        Returns:
            str: URL для авторизации
        """
        self.redirect_uri = redirect_uri
        
        # Генерируем PKCE пару если client_secret не предоставлен
        if not self.client_secret:
            self.code_verifier, self.code_challenge = self.generate_pkce_pair()
        else:
            self.code_verifier = None
            self.code_challenge = None
        
        # Генерируем состояние если не предоставлено
        if state is None:
            state = str(uuid.uuid4())
        self.state = state
        
        # Формируем параметры запроса
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self.scopes),
            "state": state
        }
        
        # Добавляем login_hint если предоставлен
        if login_hint:
            params["login_hint"] = login_hint
            
        # Добавляем PKCE параметры если используем PKCE
        if self.code_challenge:
            params["code_challenge"] = self.code_challenge
            params["code_challenge_method"] = "S256"
        
        # Формируем URL
        query_string = urllib.parse.urlencode(params)
        return f"{self.auth_url}?{query_string}"
    
    def parse_authorization_response(self, response_url: str) -> Tuple[str, Optional[str]]:
        """
        Парсит ответ авторизации и извлекает код подтверждения
        
        Args:
            response_url (str): URL с ответом авторизации
            
        Returns:
            Tuple[str, Optional[str]]: (код подтверждения, состояние)
        """
        parsed = urllib.parse.urlparse(response_url)
        query_params = urllib.parse.parse_qs(parsed.query)
        
        # Извлекаем код подтверждения
        if "code" in query_params:
            confirmation_code = query_params["code"][0]
            state = query_params.get("state", [None])[0]
            return confirmation_code, state
        else:
            # Обрабатываем ошибки
            error = query_params.get("error", ["unknown_error"])[0]
            error_description = query_params.get("error_description", ["No description"])[0]
            raise Exception(f"OAuth authorization error: {error} - {error_description}")
    
    def exchange_code_for_token(self, confirmation_code: str, redirect_uri: str = None) -> Dict:
        """
        Обменивает код подтверждения на OAuth токен
        
        Args:
            confirmation_code (str): Код подтверждения из OAuth ответа
            redirect_uri (str): URI перенаправления (должен совпадать с авторизацией)
            
        Returns:
            Dict: Ответ с токенами
        """
        if redirect_uri is None:
            redirect_uri = self.redirect_uri
        
        # Параметры запроса
        data = {
            "grant_type": "authorization_code",
            "code": confirmation_code,
            "redirect_uri": redirect_uri
        }
        
        # Добавляем PKCE verifier если используем PKCE
        if self.code_verifier:
            data["code_verifier"] = self.code_verifier
        
        # Настройки заголовков
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Добавляем Basic Auth если есть client_secret
        if self.client_secret:
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_string.encode('utf-8')
            auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
            headers["Authorization"] = f"Basic {auth_b64}"
        else:
            # Добавляем client_id в тело запроса для PKCE
            data["client_id"] = self.client_id
        
        # Выполняем запрос
        response = requests.post(self.token_url, data=data, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('error_description', f"HTTP {response.status_code}")
            error_code = error_data.get('error', 'unknown_error')
            raise Exception(f"Token exchange failed: {error_code} - {error_msg}")
    
    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Обновляет access token используя refresh token
        
        Args:
            refresh_token (str): Refresh token для обновления
            
        Returns:
            Dict: Ответ с новыми токенами
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Добавляем Basic Auth если есть client_secret
        if self.client_secret:
            auth_string = f"{self.client_id}:{self.client_secret}"
            auth_bytes = auth_string.encode('utf-8')
            auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
            headers["Authorization"] = f"Basic {auth_b64}"
        else:
            data["client_id"] = self.client_id
        
        response = requests.post(self.token_url, data=data, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('error_description', f"HTTP {response.status_code}")
            error_code = error_data.get('error', 'unknown_error')
            raise Exception(f"Token refresh failed: {error_code} - {error_msg}")


class YandexDiskOAuthWebDAV:
    """WebDAV клиент для Яндекс.Диска с OAuth2 авторизацией"""
    
    def __init__(self, access_token: str):
        """
        Инициализация WebDAV клиента
        
        Args:
            access_token (str): OAuth access token
        """
        self.access_token = access_token
        self.base_url = "https://webdav.yandex.ru"
        self.session = requests.Session()
        
        # Настраиваем авторизацию через Bearer token
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}"
        })
    
    def test_connection(self) -> bool:
        """
        Проверяет подключение к Яндекс.Диску
        
        Returns:
            bool: True при успехе, False при ошибке
        """
        try:
            response = self.session.request('PROPFIND', self.base_url, 
                                          headers={'Depth': '0'})
            return response.status_code in [200, 207]  # 207 Multi-Status
        except Exception:
            return False
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Загружает файл на Яндекс.Диск
        
        Args:
            local_path (str): Локальный путь к файлу
            remote_path (str): Удаленный путь на Яндекс.Диске
            
        Returns:
            bool: True при успехе, False при ошибке
        """
        try:
            import os
            if not os.path.exists(local_path):
                return False
            
            with open(local_path, 'rb') as f:
                file_data = f.read()
            
            url = f"{self.base_url}{remote_path}"
            response = self.session.put(url, data=file_data)
            
            return response.status_code in [200, 201, 204]
        except Exception as e:
            print(f"Ошибка загрузки файла: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Скачивает файл с Яндекс.Диска
        
        Args:
            remote_path (str): Удаленный путь на Яндекс.Диске
            local_path (str): Локальный путь для сохранения
            
        Returns:
            bool: True при успехе, False при ошибке
        """
        try:
            import os
            url = f"{self.base_url}{remote_path}"
            response = self.session.get(url)
            
            if response.status_code == 200:
                # Создаем директорию если не существует
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                return True
            return False
        except Exception as e:
            print(f"Ошибка скачивания файла: {e}")
            return False
    
    def list_directory(self, remote_path: str = "/") -> list:
        """
        Возвращает список файлов в директории
        
        Args:
            remote_path (str): Удаленный путь на Яндекс.Диске
            
        Returns:
            list: Список файлов и директорий
        """
        try:
            url = f"{self.base_url}{remote_path}"
            response = self.session.request('PROPFIND', url, 
                                          headers={'Depth': '1'})
            
            if response.status_code in [200, 207]:
                # Парсим XML ответ
                files = []
                root = ET.fromstring(response.content)
                
                for response_elem in root.findall('.//{DAV:}response'):
                    href = response_elem.find('.//{DAV:}href')
                    if href is not None and href.text:
                        files.append(href.text)
                
                return files
            return []
        except Exception as e:
            print(f"Ошибка получения списка файлов: {e}")
            return []
    
    def create_directory(self, remote_path: str) -> bool:
        """
        Создает директорию на Яндекс.Диске
        
        Args:
            remote_path (str): Путь для создания директории
            
        Returns:
            bool: True при успехе, False при ошибке
        """
        try:
            url = f"{self.base_url}{remote_path}"
            response = self.session.request('MKCOL', url)
            
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"Ошибка создания директории: {e}")
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """
        Удаляет файл с Яндекс.Диска
        
        Args:
            remote_path (str): Путь к файлу для удаления
            
        Returns:
            bool: True при успехе, False при ошибке
        """
        try:
            url = f"{self.base_url}{remote_path}"
            response = self.session.request('DELETE', url)
            
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Ошибка удаления файла: {e}")
            return False
