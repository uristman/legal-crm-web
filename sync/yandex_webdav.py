"""
Модуль для работы с Яндекс.Диском через WebDAV API
Обеспечивает автоматическую синхронизацию базы данных Legal CRM
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
import hashlib
import sqlite3

class YandexDiskWebDAV:
    """Клиент для работы с Яндекс.Диском через WebDAV"""
    
    def __init__(self, username, password):
        """
        Инициализация клиента
        
        Args:
            username (str): Логин Яндекс.Паспорта
            password (str): Пароль Яндекс.Паспорта или пароль приложения
        """
        self.base_url = "https://webdav.yandex.ru"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        
        # Проверяем подключение при инициализации
        if not self.test_connection():
            raise ConnectionError("Не удалось подключиться к Яндекс.Диску")
    
    def test_connection(self):
        """Проверяет подключение к Яндекс.Диску"""
        try:
            response = self.session.request('PROPFIND', self.base_url, 
                                          headers={'Depth': '0'})
            return response.status_code in [200, 207]  # 207 Multi-Status
        except Exception:
            return False
    
    def upload_file(self, local_path, remote_path):
        """
        Загружает файл на Яндекс.Диск
        
        Args:
            local_path (str): Локальный путь к файлу
            remote_path (str): Удаленный путь на Яндекс.Диске
        
        Returns:
            bool: True при успехе, False при ошибке
        """
        try:
            if not os.path.exists(local_path):
                return False
            
            with open(local_path, 'rb') as f:
                file_data = f.read()
            
            url = f"{self.base_url}{quote(remote_path)}"
            response = self.session.put(url, data=file_data)
            
            return response.status_code in [200, 201, 204]
        except Exception as e:
            print(f"Ошибка загрузки файла: {e}")
            return False
    
    def download_file(self, remote_path, local_path):
        """
        Скачивает файл с Яндекс.Диска
        
        Args:
            remote_path (str): Удаленный путь на Яндекс.Диске
            local_path (str): Локальный путь для сохранения
        
        Returns:
            bool: True при успехе, False при ошибке
        """
        try:
            url = f"{self.base_url}{quote(remote_path)}"
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
    
    def list_directory(self, remote_path="/"):
        """
        Получает список файлов и папок в директории
        
        Args:
            remote_path (str): Путь к директории
        
        Returns:
            list: Список элементов с информацией о файлах
        """
        try:
            url = f"{self.base_url}{quote(remote_path)}"
            response = self.session.request('PROPFIND', url, 
                                          headers={'Depth': '1'})
            
            if response.status_code != 207:
                return []
            
            # Парсим XML ответ
            root = ET.fromstring(response.content)
            
            # Определяем namespaces
            namespaces = {
                'd': 'DAV:',
                'ns0': 'DAV:'
            }
            
            files = []
            for response_elem in root.findall('.//d:response', namespaces):
                href = response_elem.find('d:href', namespaces)
                prop = response_elem.find('d:propstat/d:prop', namespaces)
                
                if href is not None and prop is not None:
                    name = href.text
                    if name.startswith('/'):
                        name = name[1:]
                    
                    # Определяем тип
                    is_collection = prop.find('d:resourcetype/d:collection', namespaces) is not None
                    
                    # Получаем размер файла
                    content_length = prop.find('d:content-length')
                    size = int(content_length.text) if content_length is not None else 0
                    
                    # Получаем дату модификации
                    last_modified = prop.find('d:getlastmodified')
                    modified_date = last_modified.text if last_modified is not None else None
                    
                    files.append({
                        'name': name,
                        'path': href.text,
                        'is_directory': is_collection,
                        'size': size,
                        'modified': modified_date
                    })
            
            return files
        except Exception as e:
            print(f"Ошибка получения списка файлов: {e}")
            return []
    
    def create_directory(self, remote_path):
        """
        Создает директорию на Яндекс.Диске
        
        Args:
            remote_path (str): Путь к новой директории
        
        Returns:
            bool: True при успехе, False при ошибке
        """
        try:
            url = f"{self.base_url}{quote(remote_path)}"
            response = self.session.request('MKCOL', url)
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"Ошибка создания директории: {e}")
            return False
    
    def delete_file(self, remote_path):
        """
        Удаляет файл или директорию с Яндекс.Диска
        
        Args:
            remote_path (str): Путь к файлу/директории
        
        Returns:
            bool: True при успехе, False при ошибке
        """
        try:
            url = f"{self.base_url}{quote(remote_path)}"
            response = self.session.request('DELETE', url)
            return response.status_code in [200, 204]
        except Exception as e:
            print(f"Ошибка удаления файла: {e}")
            return False
    
    def get_file_info(self, remote_path):
        """
        Получает информацию о файле
        
        Args:
            remote_path (str): Путь к файлу
        
        Returns:
            dict: Информация о файле или None при ошибке
        """
        try:
            url = f"{self.base_url}{quote(remote_path)}"
            response = self.session.request('PROPFIND', url, 
                                          headers={'Depth': '0'})
            
            if response.status_code != 207:
                return None
            
            root = ET.fromstring(response.content)
            namespaces = {
                'd': 'DAV:',
                'ns0': 'DAV:'
            }
            
            response_elem = root.find('.//d:response', namespaces)
            if response_elem is not None:
                href = response_elem.find('d:href', namespaces)
                prop = response_elem.find('d:propstat/d:prop', namespaces)
                
                if href is not None and prop is not None:
                    # Определяем тип
                    is_collection = prop.find('d:resourcetype/d:collection', namespaces) is not None
                    
                    # Получаем размер файла
                    content_length = prop.find('d:content-length')
                    size = int(content_length.text) if content_length is not None else 0
                    
                    # Получаем дату модификации
                    last_modified = prop.find('d:getlastmodified')
                    modified_date = last_modified.text if last_modified is not None else None
                    
                    return {
                        'name': href.text,
                        'is_directory': is_collection,
                        'size': size,
                        'modified': modified_date
                    }
            return None
        except Exception as e:
            print(f"Ошибка получения информации о файле: {e}")
            return None


class DatabaseSyncManager:
    """Менеджер синхронизации базы данных с Яндекс.Диском"""
    
    def __init__(self, db_path, yandex_disk, remote_path="/legal_crm/"):
        """
        Инициализация менеджера синхронизации
        
        Args:
            db_path (str): Путь к локальной базе данных
            yandex_disk (YandexDiskWebDAV): Экземпляр клиента Яндекс.Диска
            remote_path (str): Удаленный путь для хранения данных
        """
        self.db_path = db_path
        self.yandex_disk = yandex_disk
        self.remote_path = remote_path
        self.last_backup_hash = None
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Создаем директорию на Яндекс.Диске если не существует
        self._ensure_remote_directory()
    
    def _ensure_remote_directory(self):
        """Создает директорию на Яндекс.Диске если не существует"""
        self.yandex_disk.create_directory(self.remote_path)
    
    def _get_db_hash(self):
        """Вычисляет хеш текущей базы данных"""
        try:
            with open(self.db_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None
    
    def _create_backup(self):
        """Создает резервную копию локальной базы данных"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"legal_crm_backup_{timestamp}.db"
        backup_path = self.backup_dir / backup_filename
        
        try:
            shutil.copy2(self.db_path, backup_path)
            return backup_path, backup_filename
        except Exception as e:
            print(f"Ошибка создания резервной копии: {e}")
            return None, None
    
    def upload_to_cloud(self):
        """
        Загружает базу данных на Яндекс.Диск
        
        Returns:
            dict: Результат операции
        """
        try:
            # Создаем резервную копию
            local_backup_path, backup_filename = self._create_backup()
            if not local_backup_path:
                return {
                    'success': False,
                    'error': 'Не удалось создать резервную копию'
                }
            
            # Загружаем на Яндекс.Диск
            remote_path = f"{self.remote_path}{backup_filename}"
            success = self.yandex_disk.upload_file(str(local_backup_path), remote_path)
            
            # Обновляем основную базу данных
            main_db_path = f"{self.remote_path}legal_crm.db"
            main_success = self.yandex_disk.upload_file(self.db_path, main_db_path)
            
            # Обновляем хеш последней версии
            self.last_backup_hash = self._get_db_hash()
            
            # Очищаем локальную резервную копию
            local_backup_path.unlink(missing_ok=True)
            
            return {
                'success': success and main_success,
                'backup_filename': backup_filename,
                'uploaded_to_cloud': True
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_from_cloud(self):
        """
        Скачивает последнюю версию базы данных с Яндекс.Диска
        
        Returns:
            dict: Результат операции
        """
        try:
            remote_db_path = f"{self.remote_path}legal_crm.db"
            
            # Проверяем, существует ли файл на облаке
            file_info = self.yandex_disk.get_file_info(remote_db_path)
            if not file_info:
                return {
                    'success': False,
                    'error': 'Файл базы данных не найден на Яндекс.Диске'
                }
            
            # Скачиваем базу данных
            success = self.yandex_disk.download_file(remote_db_path, self.db_path)
            
            if success:
                self.last_backup_hash = self._get_db_hash()
                return {
                    'success': True,
                    'downloaded_from_cloud': True,
                    'file_info': file_info
                }
            else:
                return {
                    'success': False,
                    'error': 'Не удалось скачать файл'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_status(self):
        """
        Проверяет статус синхронизации
        
        Returns:
            dict: Информация о состоянии синхронизации
        """
        try:
            current_hash = self._get_db_hash()
            
            # Получаем информацию о файле на облаке
            remote_db_path = f"{self.remote_path}legal_crm.db"
            cloud_file_info = self.yandex_disk.get_file_info(remote_db_path)
            
            # Проверяем, нужна ли синхронизация
            needs_sync = (cloud_file_info and 
                         current_hash != self.last_backup_hash)
            
            # Получаем список резервных копий на облаке
            backup_files = self._get_cloud_backups()
            
            return {
                'needs_sync': needs_sync,
                'current_hash': current_hash,
                'last_backup_hash': self.last_backup_hash,
                'cloud_file_exists': cloud_file_info is not None,
                'cloud_file_info': cloud_file_info,
                'backup_files_count': len(backup_files),
                'sync_path': self.remote_path
            }
        except Exception as e:
            return {
                'needs_sync': False,
                'error': str(e)
            }
    
    def _get_cloud_backups(self):
        """Получает список резервных копий на Яндекс.Диске"""
        try:
            files = self.yandex_disk.list_directory(self.remote_path)
            backup_files = [f for f in files if 'backup' in f['name'] and f['name'].endswith('.db')]
            return backup_files
        except Exception:
            return []
    
    def get_backup_history(self, limit=10):
        """
        Получает историю резервных копий
        
        Args:
            limit (int): Максимальное количество записей
        
        Returns:
            list: Список резервных копий
        """
        try:
            backup_files = self._get_cloud_backups()
            
            # Сортируем по дате модификации (новые сначала)
            backup_files.sort(key=lambda x: x['modified'] if x['modified'] else '', reverse=True)
            
            return backup_files[:limit]
        except Exception:
            return []
