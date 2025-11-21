"""
Модуль управления синхронизацией для Legal CRM
Интегрирует Яндекс.Диск WebDAV с веб-приложением
"""

import os
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from sync.yandex_webdav import YandexDiskWebDAV, DatabaseSyncManager

class SyncConfiguration:
    """Класс для управления конфигурацией синхронизации"""
    
    DEFAULT_CONFIG = {
        'yandex_username': '',
        'yandex_password': '',
        'auto_sync_enabled': False,
        'sync_interval_minutes': 30,
        'last_sync': None,
        'remote_path': '/legal_crm/',
        'backup_retention_days': 30
    }
    
    def __init__(self, config_file='sync_config.json'):
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self):
        """Загружает конфигурацию из файла"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Обновляем конфигурацию новыми ключами
                for key, value in self.DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception:
                pass
        return self.DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Сохраняет конфигурацию в файл"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def update_config(self, **kwargs):
        """Обновляет конфигурацию"""
        for key, value in kwargs.items():
            if key in self.DEFAULT_CONFIG:
                self.config[key] = value
        return self.save_config()
    
    def get(self, key, default=None):
        """Получает значение конфигурации"""
        return self.config.get(key, default)
    
    def is_configured(self):
        """Проверяет, настроена ли синхронизация"""
        return bool(self.config['yandex_username'] and self.config['yandex_password'])


class SyncManager:
    """Основной менеджер синхронизации"""
    
    def __init__(self, db_path='legal_crm.db', config_file='sync_config.json'):
        self.db_path = db_path
        self.config = SyncConfiguration(config_file)
        self.sync_manager = None
        self.sync_thread = None
        self.running = False
        
        # Создаем директорию для синхронизации
        self.sync_dir = Path("sync")
        self.sync_dir.mkdir(exist_ok=True)
    
    def _get_sync_manager(self):
        """Создает или возвращает экземпляр менеджера синхронизации"""
        if self.sync_manager is None and self.config.is_configured():
            try:
                yandex_disk = YandexDiskWebDAV(
                    self.config.get('yandex_username'),
                    self.config.get('yandex_password')
                )
                self.sync_manager = DatabaseSyncManager(
                    self.db_path,
                    yandex_disk,
                    self.config.get('remote_path')
                )
            except Exception:
                pass
        return self.sync_manager
    
    def setup_yandex_connection(self, username, password):
        """
        Настраивает подключение к Яндекс.Диску
        
        Args:
            username (str): Логин Яндекс.Паспорта
            password (str): Пароль
        
        Returns:
            dict: Результат настройки
        """
        try:
            # Тестируем подключение
            yandex_disk = YandexDiskWebDAV(username, password)
            
            # Сохраняем конфигурацию
            self.config.update_config(
                yandex_username=username,
                yandex_password=password
            )
            
            # Создаем менеджер синхронизации
            self.sync_manager = DatabaseSyncManager(
                self.db_path,
                yandex_disk,
                self.config.get('remote_path')
            )
            
            return {
                'success': True,
                'message': 'Подключение к Яндекс.Диску настроено успешно!'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка подключения: {str(e)}'
            }
    
    def test_connection(self):
        """Тестирует подключение к Яндекс.Диску"""
        if not self.config.is_configured():
            return {
                'success': False,
                'error': 'Не настроены учетные данные для Яндекс.Диска'
            }
        
        try:
            yandex_disk = YandexDiskWebDAV(
                self.config.get('yandex_username'),
                self.config.get('yandex_password')
            )
            
            return {
                'success': True,
                'message': 'Подключение к Яндекс.Диску работает!'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка подключения: {str(e)}'
            }
    
    def sync_to_cloud(self):
        """
        Синхронизирует данные с облаком
        
        Returns:
            dict: Результат синхронизации
        """
        sync_manager = self._get_sync_manager()
        if not sync_manager:
            return {
                'success': False,
                'error': 'Менеджер синхронизации не инициализирован'
            }
        
        try:
            result = sync_manager.upload_to_cloud()
            
            if result['success']:
                self.config.update_config(
                    last_sync=datetime.now().isoformat()
                )
            
            return result
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка синхронизации: {str(e)}'
            }
    
    def sync_from_cloud(self):
        """
        Синхронизирует данные из облака
        
        Returns:
            dict: Результат синхронизации
        """
        sync_manager = self._get_sync_manager()
        if not sync_manager:
            return {
                'success': False,
                'error': 'Менеджер синхронизации не инициализирован'
            }
        
        try:
            result = sync_manager.download_from_cloud()
            return result
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка синхронизации: {str(e)}'
            }
    
    def get_sync_status(self):
        """
        Получает статус синхронизации
        
        Returns:
            dict: Информация о состоянии синхронизации
        """
        sync_manager = self._get_sync_manager()
        if not sync_manager:
            return {
                'configured': self.config.is_configured(),
                'needs_sync': False,
                'error': 'Менеджер синхронизации не инициализирован'
            }
        
        try:
            status = sync_manager.sync_status()
            status['configured'] = self.config.is_configured()
            status['auto_sync_enabled'] = self.config.get('auto_sync_enabled')
            status['last_sync'] = self.config.get('last_sync')
            
            return status
        except Exception as e:
            return {
                'configured': self.config.is_configured(),
                'needs_sync': False,
                'error': str(e)
            }
    
    def start_auto_sync(self):
        """Запускает автоматическую синхронизацию"""
        if self.running or not self.config.get('auto_sync_enabled'):
            return
        
        self.running = True
        self.sync_thread = threading.Thread(target=self._auto_sync_worker, daemon=True)
        self.sync_thread.start()
    
    def stop_auto_sync(self):
        """Останавливает автоматическую синхронизацию"""
        self.running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
    
    def _auto_sync_worker(self):
        """Рабочий поток для автоматической синхронизации"""
        interval = self.config.get('sync_interval_minutes', 30) * 60
        
        while self.running:
            try:
                sync_manager = self._get_sync_manager()
                if sync_manager:
                    status = sync_manager.sync_status()
                    if status.get('needs_sync', False):
                        self.sync_to_cloud()
            except Exception as e:
                print(f"Ошибка автоматической синхронизации: {e}")
            
            time.sleep(interval)
    
    def enable_auto_sync(self, interval_minutes=30):
        """
        Включает автоматическую синхронизацию
        
        Args:
            interval_minutes (int): Интервал синхронизации в минутах
        """
        self.config.update_config(
            auto_sync_enabled=True,
            sync_interval_minutes=interval_minutes
        )
        self.start_auto_sync()
    
    def disable_auto_sync(self):
        """Отключает автоматическую синхронизацию"""
        self.config.update_config(auto_sync_enabled=False)
        self.stop_auto_sync()
    
    def get_backup_history(self, limit=10):
        """
        Получает историю резервных копий
        
        Args:
            limit (int): Максимальное количество записей
        
        Returns:
            list: История резервных копий
        """
        sync_manager = self._get_sync_manager()
        if not sync_manager:
            return []
        
        try:
            return sync_manager.get_backup_history(limit)
        except Exception:
            return []
    
    def restore_from_backup(self, backup_filename):
        """
        Восстанавливает данные из резервной копии
        
        Args:
            backup_filename (str): Имя файла резервной копии
        
        Returns:
            dict: Результат восстановления
        """
        try:
            # Скачиваем выбранную резервную копию
            remote_path = f"{self.config.get('remote_path')}{backup_filename}"
            local_temp_backup = f"temp_{backup_filename}"
            
            yandex_disk = YandexDiskWebDAV(
                self.config.get('yandex_username'),
                self.config.get('yandex_password')
            )
            
            success = yandex_disk.download_file(remote_path, local_temp_backup)
            if not success:
                return {
                    'success': False,
                    'error': 'Не удалось скачать резервную копию'
                }
            
            # Создаем резервную копию текущей базы данных
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_backup = f"pre_restore_backup_{timestamp}.db"
            os.rename(self.db_path, current_backup)
            
            # Восстанавливаем из выбранной резервной копии
            os.rename(local_temp_backup, self.db_path)
            
            return {
                'success': True,
                'message': 'Данные восстановлены из резервной копии',
                'pre_restore_backup': current_backup
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка восстановления: {str(e)}'
            }
    
    def cleanup_old_backups(self):
        """
        Очищает старые резервные копии
        
        Returns:
            dict: Результат очистки
        """
        try:
            retention_days = self.config.get('backup_retention_days', 30)
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Получаем список всех резервных копий
            backup_files = self.get_backup_history(limit=1000)
            
            deleted_count = 0
            for backup in backup_files:
                if backup.get('modified'):
                    try:
                        backup_date = datetime.fromisoformat(backup['modified'].replace('Z', '+00:00'))
                        if backup_date < cutoff_date:
                            remote_path = f"{self.config.get('remote_path')}{backup['name']}"
                            yandex_disk = YandexDiskWebDAV(
                                self.config.get('yandex_username'),
                                self.config.get('yandex_password')
                            )
                            if yandex_disk.delete_file(remote_path):
                                deleted_count += 1
                    except Exception:
                        continue
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'message': f'Удалено {deleted_count} старых резервных копий'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
