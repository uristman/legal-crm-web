"""
Модуль для работы с Яндекс.Диском через HTTP API
Использует OAuth авторизацию для безопасного доступа к данным
"""

import os
import json
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple
import urllib.parse

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    print("⚠️  Установка requests...")
    os.system("pip install requests")
    import requests

class YandexDiskWebDAV:
    """Класс для работы с Яндекс.Диском через HTTP API с OAuth авторизацией"""
    
    def __init__(self, access_token: str):
        """
        Инициализация клиента для Яндекс.Диска
        
        Args:
            access_token: Токен доступа OAuth
        """
        self.access_token = access_token
        self.base_url = "https://cloud-api.yandex.net/v1/disk"
        self.session = requests.Session()
        
        # OAuth авторизация
        self.session.headers.update({
            'Authorization': f'OAuth {access_token}',
            'User-Agent': 'LegalCRM/1.0',
            'Accept': 'application/json'
        })
        
        logger.info(f"HTTP клиент инициализирован для Яндекс.Диска")
    
    def test_connection(self) -> bool:
        """Тестирование подключения к Яндекс.Диску"""
        try:
            response = self.session.get(f"{self.base_url}/resources")
            if response.status_code == 200:
                logger.info("✅ Подключение к Яндекс.Диску успешно")
                return True
            else:
                logger.error(f"❌ Ошибка подключения: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Яндекс.Диску: {e}")
            return False
    
    def _ensure_directory(self, path: str) -> bool:
        """Создание директории если она не существует"""
        try:
            # Проверяем существование директории
            encoded_path = urllib.parse.quote(path, safe='')
            response = self.session.get(f"{self.base_url}/resources?path={encoded_path}")
            
            if response.status_code == 200:
                return True  # Директория уже существует
            
            # Создаем директорию
            response = self.session.put(
                f"{self.base_url}/resources?path={encoded_path}",
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Директория создана: {path}")
                return True
            else:
                logger.warning(f"⚠️  Не удалось создать директорию {path}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания директории {path}: {e}")
            return False
    
    def upload_file(self, local_path: str, remote_path: str, content_type: str = 'application/json') -> bool:
        """
        Загрузка файла на Яндекс.Диск
        
        Args:
            local_path: Локальный путь к файлу
            remote_path: Удаленный путь на Яндекс.Диске
            content_type: MIME тип содержимого файла
            
        Returns:
            bool: True если файл успешно загружен
        """
        try:
            # Создаем директорию если она не существует
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                self._ensure_directory(remote_dir)
            
            # Читаем файл
            with open(local_path, 'rb') as f:
                file_data = f.read()
            
            # Загружаем файл с правильным Content-Type
            encoded_path = urllib.parse.quote(remote_path, safe='')
            response = self.session.put(
                f"{self.base_url}/resources/upload?path={encoded_path}",
                data=file_data,
                headers={'Content-Type': content_type}
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"✅ Файл загружен: {remote_path}")
                return True
            else:
                logger.error(f"❌ Ошибка загрузки файла {remote_path}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки файла {remote_path}: {e}")
            return False
    
    def upload_json_data(self, data: Dict, remote_path: str) -> bool:
        """
        Загрузка JSON данных на Яндекс.Диск
        
        Args:
            data: Данные для загрузки
            remote_path: Удаленный путь на Яндекс.Диске
            
        Returns:
            bool: True если данные успешно загружены
        """
        try:
            # Создаем директорию если она не существует
            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                self._ensure_directory(remote_dir)
            
            # Конвертируем данные в JSON
            json_data = json.dumps(data, ensure_ascii=False, indent=2)
            
            # Загружаем данные
            encoded_path = urllib.parse.quote(remote_path, safe='')
            response = self.session.put(
                f"{self.base_url}/resources/upload?path={encoded_path}",
                data=json_data.encode('utf-8'),
                headers={'Content-Type': 'application/json; charset=utf-8'}
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"✅ JSON данные загружены: {remote_path}")
                return True
            else:
                logger.error(f"❌ Ошибка загрузки JSON {remote_path}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки JSON {remote_path}: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Скачивание файла с Яндекс.Диска
        
        Args:
            remote_path: Удаленный путь на Яндекс.Диске
            local_path: Локальный путь для сохранения
            
        Returns:
            bool: True если файл успешно скачан
        """
        try:
            # Создаем локальную директорию если она не существует
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            
            # Получаем ссылку для скачивания
            encoded_path = urllib.parse.quote(remote_path, safe='')
            response = self.session.get(f"{self.base_url}/resources/download?path={encoded_path}")
            
            if response.status_code != 200:
                logger.error(f"❌ Не удалось получить ссылку для скачивания {remote_path}: {response.status_code}")
                return False
            
            # Скачиваем файл по ссылке
            download_data = response.json()
            download_url = download_data.get('href')
            
            if not download_url:
                logger.error(f"❌ Не удалось получить ссылку для скачивания {remote_path}")
                return False
            
            # Скачиваем файл
            file_response = requests.get(download_url)
            if file_response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(file_response.content)
                logger.info(f"✅ Файл скачан: {remote_path}")
                return True
            else:
                logger.error(f"❌ Ошибка скачивания файла {remote_path}: {file_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания файла {remote_path}: {e}")
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """
        Удаление файла с Яндекс.Диска
        
        Args:
            remote_path: Удаленный путь на Яндекс.Диске
            
        Returns:
            bool: True если файл успешно удален
        """
        try:
            encoded_path = urllib.parse.quote(remote_path, safe='')
            response = self.session.delete(f"{self.base_url}/resources?path={encoded_path}")
            
            if response.status_code in [200, 204]:
                logger.info(f"✅ Файл удален: {remote_path}")
                return True
            else:
                logger.warning(f"⚠️  Не удалось удалить файл {remote_path}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка удаления файла {remote_path}: {e}")
            return False
    
    def list_files(self, remote_path: str = '/') -> List[str]:
        """
        Получение списка файлов в директории
        
        Args:
            remote_path: Удаленный путь директории
            
        Returns:
            List[str]: Список файлов
        """
        try:
            encoded_path = urllib.parse.quote(remote_path, safe='')
            response = self.session.get(f"{self.base_url}/resources?path={encoded_path}")
            
            if response.status_code != 200:
                logger.error(f"❌ Ошибка получения списка файлов {remote_path}: {response.status_code}")
                return []
            
            data = response.json()
            files = []
            
            if '_embedded' in data and 'items' in data['_embedded']:
                for item in data['_embedded']['items']:
                    if item.get('type') == 'file':
                        files.append({
                            'name': item.get('name', ''),
                            'size': item.get('size', 0),
                            'modified': item.get('modified', ''),
                            'path': item.get('path', '')
                        })
            
            return files
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка файлов {remote_path}: {e}")
            return []
    
    def file_exists(self, remote_path: str) -> bool:
        """
        Проверка существования файла
        
        Args:
            remote_path: Удаленный путь на Яндекс.Диске
            
        Returns:
            bool: True если файл существует
        """
        try:
            encoded_path = urllib.parse.quote(remote_path, safe='')
            response = self.session.get(f"{self.base_url}/resources?path={encoded_path}")
            return response.status_code == 200
        except Exception:
            return False


class DatabaseSyncManager:
    """Менеджер синхронизации базы данных с Яндекс.Диском"""
    
    def __init__(self, db_path: str, yandex_disk: YandexDiskWebDAV, remote_path: str = '/legal_crm/'):
        """
        Инициализация менеджера синхронизации
        
        Args:
            db_path: Путь к локальной базе данных
            yandex_disk: Экземпляр YandexDiskWebDAV
            remote_path: Удаленный путь на Яндекс.Диске
        """
        self.db_path = db_path
        self.yandex_disk = yandex_disk
        self.remote_path = remote_path
        self.backup_dir = os.path.join(os.path.dirname(db_path), 'temp_backups')
        
        # Создаем директорию для временных бэкапов
        os.makedirs(self.backup_dir, exist_ok=True)
        
        logger.info(f"DatabaseSyncManager инициализирован: {db_path} -> {remote_path}")
    
    def export_database_to_json(self) -> Dict:
        """
        Экспорт всей базы данных в JSON формат
        
        Returns:
            Dict: Данные всех таблиц в JSON формате
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Получаем список всех таблиц
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            data = {
                'export_info': {
                    'timestamp': datetime.now().isoformat(),
                    'database_path': self.db_path,
                    'tables_count': len(tables),
                    'tables': tables
                },
                'tables': {}
            }
            
            # Экспортируем каждую таблицу
            for table in tables:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                
                # Преобразуем в список словарей
                table_data = []
                for row in rows:
                    row_dict = dict(row)
                    # Преобразуем datetime объекты в строки
                    for key, value in row_dict.items():
                        if isinstance(value, datetime):
                            row_dict[key] = value.isoformat()
                    table_data.append(row_dict)
                
                data['tables'][table] = table_data
            
            conn.close()
            logger.info(f"✅ База данных экспортирована в JSON: {len(tables)} таблиц")
            return data
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта базы данных: {e}")
            raise
    
    def import_database_from_json(self, data: Dict) -> bool:
        """
        Импорт базы данных из JSON формата
        
        Args:
            data: Данные в JSON формате
            
        Returns:
            bool: True если импорт успешен
        """
        try:
            # Создаем резервную копию текущей базы
            backup_path = self._create_local_backup()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Отключаем проверки внешних ключей для быстрого импорта
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Удаляем все существующие таблицы (кроме системных)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            for table in existing_tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
            
            # Импортируем каждую таблицу из JSON
            if 'tables' in data:
                for table_name, table_data in data['tables'].items():
                    if table_data:  # Если таблица не пуста
                        self._create_table_from_data(cursor, table_name, table_data)
            
            # Включаем проверки внешних ключей обратно
            cursor.execute("PRAGMA foreign_keys = ON")
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ База данных импортирована из JSON: {len(data.get('tables', {}))} таблиц")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка импорта базы данных: {e}")
            # Восстанавливаем из резервной копии
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, self.db_path)
                logger.info("🔄 База данных восстановлена из резервной копии")
            return False
    
    def _create_table_from_data(self, cursor, table_name: str, table_data: List[Dict]):
        """Создание таблицы и заполнение данными из JSON"""
        if not table_data:
            return
        
        # Получаем колонки из первого элемента
        columns = list(table_data[0].keys())
        
        # Создаем таблицу
        create_sql = f"CREATE TABLE {table_name} ({', '.join([f'{col} TEXT' for col in columns])})"
        cursor.execute(create_sql)
        
        # Вставляем данные
        for row_data in table_data:
            values = [str(row_data.get(col, '')) for col in columns]
            placeholders = ', '.join(['?' for _ in columns])
            insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
            cursor.execute(insert_sql, values)
    
    def _create_local_backup(self) -> Optional[str]:
        """Создание локальной резервной копии"""
        try:
            if not os.path.exists(self.db_path):
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}.db")
            
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"📁 Локальная резервная копия создана: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания локальной резервной копии: {e}")
            return None
    
    def upload_to_cloud(self) -> bool:
        """
        Загрузка базы данных на Яндекс.Диск в единый файл
        
        Returns:
            bool: True если загрузка успешна
        """
        try:
            # Экспортируем базу данных в JSON
            data = self.export_database_to_json()
            
            # Загружаем данные напрямую на Яндекс.Диск без создания временного файла
            remote_file_path = f"{self.remote_path}legal_crm_database.json"
            
            success = self.yandex_disk.upload_json_data(data, remote_file_path)
            
            if success:
                logger.info(f"✅ База данных загружена на Яндекс.Диск: {remote_file_path}")
                return True
            else:
                logger.error("❌ Не удалось загрузить базу данных на Яндекс.Диск")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки на облако: {e}")
            return False
    
    def download_from_cloud(self) -> Dict:
        """
        Скачивание базы данных с Яндекс.Диска
        
        Returns:
            Dict: Результат операции
        """
        try:
            remote_file_path = f"{self.remote_path}legal_crm_database.json"
            
            # Проверяем существование файла
            if not self.yandex_disk.file_exists(remote_file_path):
                return {
                    'success': False,
                    'error': 'Файл базы данных не найден на Яндекс.Диске'
                }
            
            # Скачиваем файл
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_json_path = os.path.join(self.backup_dir, f"downloaded_data_{timestamp}.json")
            
            success = self.yandex_disk.download_file(remote_file_path, temp_json_path)
            
            if not success:
                return {
                    'success': False,
                    'error': 'Не удалось скачать файл с Яндекс.Диска'
                }
            
            # Читаем данные
            with open(temp_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Импортируем в локальную базу данных
            import_success = self.import_database_from_json(data)
            
            # Удаляем временный файл
            if os.path.exists(temp_json_path):
                os.remove(temp_json_path)
            
            if import_success:
                logger.info(f"✅ База данных загружена из облака: {remote_file_path}")
                return {
                    'success': True,
                    'message': 'База данных успешно загружена из облака'
                }
            else:
                return {
                    'success': False,
                    'error': 'Не удалось импортировать данные в локальную базу'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания из облака: {e}")
            return {
                'success': False,
                'error': f'Ошибка скачивания: {str(e)}'
            }
    
    def list_backups(self) -> List[Dict]:
        """
        Получение списка резервных копий на Яндекс.Диске
        
        Returns:
            List[Dict]: Список резервных копий
        """
        try:
            # Получаем список файлов в директории синхронизации
            files = self.yandex_disk.list_files(self.remote_path)
            
            backups = []
            for file_info in files:
                if isinstance(file_info, dict) and 'name' in file_info:
                    filename = file_info['name']
                    if filename.endswith('.json') and 'legal_crm' in filename:
                        backup_info = {
                            'filename': filename,
                            'size': file_info.get('size', 0),
                            'modified': file_info.get('modified', ''),
                            'path': file_info.get('path', '')
                        }
                        backups.append(backup_info)
            
            # Сортируем по дате модификации (новые первыми)
            backups.sort(key=lambda x: x['modified'], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка резервных копий: {e}")
            return []
    
    def restore_backup(self, backup_filename: str) -> Dict:
        """
        Восстановление из резервной копии
        
        Args:
            backup_filename: Имя файла резервной копии
            
        Returns:
            Dict: Результат операции
        """
        try:
            remote_file_path = f"{self.remote_path}{backup_filename}"
            
            # Скачиваем резервную копию
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_json_path = os.path.join(self.backup_dir, f"restore_backup_{timestamp}.json")
            
            success = self.yandex_disk.download_file(remote_file_path, temp_json_path)
            
            if not success:
                return {
                    'success': False,
                    'error': 'Не удалось скачать резервную копию'
                }
            
            # Читаем данные
            with open(temp_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Импортируем в локальную базу данных
            import_success = self.import_database_from_json(data)
            
            # Удаляем временный файл
            if os.path.exists(temp_json_path):
                os.remove(temp_json_path)
            
            if import_success:
                logger.info(f"✅ Восстановление из резервной копии завершено: {backup_filename}")
                return {
                    'success': True,
                    'message': f'Успешно восстановлено из резервной копии: {backup_filename}'
                }
            else:
                return {
                    'success': False,
                    'error': 'Не удалось импортировать данные из резервной копии'
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления из резервной копии: {e}")
            return {
                'success': False,
                'error': f'Ошибка восстановления: {str(e)}'
            }
    
    def cleanup_old_backups(self, retention_days: int = 30) -> Dict:
        """
        Очистка старых резервных копий
        
        Args:
            retention_days: Количество дней для хранения резервных копий
            
        Returns:
            Dict: Результат операции
        """
        try:
            backups = self.list_backups()
            
            if not backups:
                return {
                    'success': True,
                    'message': 'Резервные копии не найдены'
                }
            
            # Удаляем старые резервные копии (оставляем только последние)
            cutoff_date = datetime.now()
            
            deleted_count = 0
            for backup in backups:
                backup_date = backup.get('modified', '')
                if backup_date:
                    try:
                        # Парсим дату модификации
                        backup_datetime = datetime.fromisoformat(backup_date.replace('Z', '+00:00'))
                        
                        # Если резервная копия старше retention_days, удаляем её
                        if (cutoff_date - backup_datetime.replace(tzinfo=None)).days > retention_days:
                            success = self.yandex_disk.delete_file(backup['path'])
                            if success:
                                deleted_count += 1
                    except Exception as e:
                        logger.warning(f"⚠️  Не удалось обработать резервную копию {backup['filename']}: {e}")
            
            return {
                'success': True,
                'message': f'Удалено {deleted_count} старых резервных копий'
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки резервных копий: {e}")
            return {
                'success': False,
                'error': f'Ошибка очистки: {str(e)}'
            }


class YandexOAuthClient:
    """Клиент для работы с OAuth авторизацией Яндекс"""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Инициализация OAuth клиента
        
        Args:
            client_id: ID приложения
            client_secret: Секретный ключ
            redirect_uri: URI для редиректа
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = "https://oauth.yandex.ru"
    
    def get_auth_url(self) -> str:
        """Получение URL для авторизации"""
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'disk:write disk:read'
        }
        
        url_params = urllib.parse.urlencode(params)
        return f"{self.base_url}/authorize?{url_params}"
    
    def exchange_code_for_token(self, auth_code: str) -> Dict:
        """Обмен кода авторизации на токен"""
        try:
            data = {
                'grant_type': 'authorization_code',
                'code': auth_code,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(f"{self.base_url}/token", data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                return {
                    'success': True,
                    'access_token': token_data.get('access_token'),
                    'token_type': token_data.get('token_type', 'Bearer')
                }
            else:
                return {
                    'success': False,
                    'error': f'Ошибка получения токена: {response.status_code} - {response.text}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка обмена кода на токен: {str(e)}'
            }
