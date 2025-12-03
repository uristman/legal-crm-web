/**
 * JavaScript для OAuth авторизации с Яндекс.Диском с поддержкой 2FA
 * Заменяет старый код синхронизации
 */

class YandexOAuthSync {
    constructor() {
        this.oauthConfigured = false;
        this.oauthAuthorized = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkOAuthStatus();
    }

    bindEvents() {
        // Обработка события postMessage для OAuth callback
        window.addEventListener('message', (event) => {
            if (event.origin !== window.location.origin) return;
            
            if (event.data.type === 'oauth_success') {
                this.handleOAuthCallback(event.data.code, event.data.state);
            }
        });
    }

    // ==================== OAuth АВТОРИЗАЦИЯ ====================

    async startOAuthAuthorization() {
        try {
            const username = $('#yandex-username').val().trim();
            
            if (!username) {
                this.showNotification('Пожалуйста, введите логин Яндекс.Паспорта', 'warning');
                return;
            }

            this.showNotification('Генерация URL авторизации...', 'info');

            const response = await fetch('/api/oauth/authorize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('Откройте ссылку в новой вкладке для авторизации', 'info');
                
                // Открываем новое окно для авторизации
                const authWindow = window.open(
                    data.auth_url,
                    'yandex_oauth',
                    'width=600,height=600,scrollbars=yes,resizable=yes'
                );

                if (!authWindow) {
                    this.showNotification('Не удалось открыть окно авторизации. Разрешите всплывающие окна.', 'error');
                    return;
                }

                // Проверяем закрытие окна авторизации
                const checkClosed = setInterval(() => {
                    if (authWindow.closed) {
                        clearInterval(checkClosed);
                        this.showNotification('Окно авторизации закрыто. Если авторизация прошла успешно, обновите страницу.', 'info');
                    }
                }, 1000);

                this.showNotification('После авторизации в открывшемся окне вернитесь сюда и обновите статус', 'success');
            } else {
                this.showNotification('Ошибка генерации URL авторизации: ' + data.error, 'error');
            }
        } catch (error) {
            this.showNotification('Ошибка при запуске авторизации: ' + error.message, 'error');
        }
    }

    async handleOAuthCallback(code, state) {
        try {
            this.showNotification('Обработка кода авторизации...', 'info');

            const response = await fetch('/api/oauth/exchange', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    code: code
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('Авторизация успешно завершена! Теперь можно настроить синхронизацию.', 'success');
                this.updateOAuthStatus();
            } else {
                this.showNotification('Ошибка авторизации: ' + data.error, 'error');
            }
        } catch (error) {
            this.showNotification('Ошибка при обработке кода авторизации: ' + error.message, 'error');
        }
    }

    async checkOAuthStatus() {
        try {
            const response = await fetch('/api/oauth/status');
            const data = await response.json();

            if (data.success) {
                this.oauthConfigured = data.oauth_configured;
                this.oauthAuthorized = data.oauth_authorized;
                this.updateOAuthUI(data);
            } else {
                this.showNotification('Ошибка проверки статуса OAuth: ' + data.error, 'error');
            }
        } catch (error) {
            console.error('OAuth status check failed:', error);
        }
    }

    updateOAuthUI(status) {
        const container = $('#yandex-oauth-container');
        const statusIndicator = $('#yandex-oauth-status');
        const statusText = $('#yandex-oauth-status-text');

        if (status.oauth_configured && status.oauth_authorized) {
            container.show();
            statusIndicator.html('<i class="fas fa-check-circle text-white"></i>');
            statusText.text('Авторизован');
            statusIndicator.parent().removeClass('bg-secondary bg-warning bg-danger').addClass('bg-success');
            
            // Показываем конфигурацию синхронизации
            $('#sync-config-section').show();
        } else if (status.oauth_configured && !status.oauth_authorized) {
            container.show();
            statusIndicator.html('<i class="fas fa-exclamation-triangle text-white"></i>');
            statusText.text('Требуется авторизация');
            statusIndicator.parent().removeClass('bg-secondary bg-success bg-danger').addClass('bg-warning');
            
            // Показываем форму авторизации
            $('#yandex-auth-form').show();
        } else {
            container.show();
            statusIndicator.html('<i class="fas fa-times-circle text-white"></i>');
            statusText.text('Не настроено');
            statusIndicator.parent().removeClass('bg-secondary bg-warning bg-success').addClass('bg-danger');
            
            // Показываем форму авторизации
            $('#yandex-auth-form').show();
        }

        // Обновляем статус синхронизации
        if (status.sync_configured && status.last_sync) {
            $('#last-sync-info').text('Последняя синхронизация: ' + new Date(status.last_sync).toLocaleString());
        }
    }

    updateOAuthStatus() {
        this.checkOAuthStatus();
    }

    // ==================== СИНХРОНИЗАЦИЯ ====================

    async testConnection() {
        try {
            const btn = event.target;
            const originalText = btn.innerHTML;
            
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Проверка...';
            btn.disabled = true;

            const response = await fetch('/api/oauth/test', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification(data.message, 'success');
            } else {
                this.showNotification(data.error, 'error');
                if (data.action_required) {
                    this.showNotification('Требуется повторная авторизация', 'warning');
                }
            }
        } catch (error) {
            this.showNotification('Ошибка соединения с сервером', 'error');
        } finally {
            const btn = event.target;
            btn.innerHTML = '<i class="fas fa-sync-alt me-2"></i>Тест соединения';
            btn.disabled = false;
        }
    }

    async uploadToCloud() {
        try {
            if (!this.oauthAuthorized) {
                this.showNotification('Сначала необходимо авторизоваться через OAuth', 'warning');
                return;
            }

            this.showNotification('Загрузка данных в облако...', 'info');

            const response = await fetch('/api/oauth/upload', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('Данные успешно синхронизированы с Яндекс.Диском!', 'success');
                this.updateOAuthStatus();
                this.loadBackupHistory();
            } else {
                if (data.action_required === 'Re-authorize') {
                    this.showNotification('Требуется повторная авторизация. Нажмите "Обновить токен"', 'warning');
                    $('#refresh-token-btn').show();
                } else {
                    this.showNotification('Ошибка: ' + (data.error || 'Неизвестная ошибка'), 'error');
                }
            }
        } catch (error) {
            this.showNotification('Ошибка загрузки: ' + error.message, 'error');
        }
    }

    async downloadFromCloud() {
        try {
            if (!this.oauthAuthorized) {
                this.showNotification('Сначала необходимо авторизоваться через OAuth', 'warning');
                return;
            }

            if (!confirm('Внимание! Загрузка данных из облака заменит текущую базу данных. Продолжить?')) {
                return;
            }

            this.showNotification('Загрузка данных из облака...', 'info');

            const response = await fetch('/api/oauth/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    remote_path: $('#download-remote-path').val()
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('Данные успешно загружены из облака!', 'success');
                this.updateOAuthStatus();
                this.loadAllData(); // Перезагружаем все данные
            } else {
                this.showNotification('Ошибка: ' + (data.error || 'Неизвестная ошибка'), 'error');
            }
        } catch (error) {
            this.showNotification('Ошибка загрузки: ' + error.message, 'error');
        }
    }

    async toggleAutoSync(toggle) {
        try {
            if (toggle.checked) {
                // Включаем автосинхронизацию
                const interval = prompt('Введите интервал синхронизации в минутах (по умолчанию 30):', '30');
                const intervalMinutes = interval ? parseInt(interval) : 30;

                if (intervalMinutes < 1) {
                    toggle.checked = false;
                    this.showNotification('Интервал должен быть больше 0 минут', 'warning');
                    return;
                }

                const response = await fetch('/api/oauth/auto/enable', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        interval_minutes: intervalMinutes
                    })
                });

                const data = await response.json();

                if (data.success) {
                    this.showNotification('Автоматическая синхронизация включена', 'success');
                } else {
                    toggle.checked = false;
                    this.showNotification('Ошибка: ' + (data.error || 'Неизвестная ошибка'), 'error');
                }
            } else {
                // Отключаем автосинхронизацию
                const response = await fetch('/api/oauth/auto/disable', {
                    method: 'POST'
                });

                const data = await response.json();

                if (data.success) {
                    this.showNotification('Автоматическая синхронизация отключена', 'info');
                } else {
                    this.showNotification('Ошибка отключения: ' + (data.error || 'Неизвестная ошибка'), 'error');
                }
            }
        } catch (error) {
            this.showNotification('Ошибка соединения с сервером', 'error');
        }
    }

    async loadBackupHistory() {
        try {
            const response = await fetch('/api/oauth/backups');
            const data = await response.json();

            if (data.success) {
                const tbody = $('#backup-history-body');
                tbody.empty();

                if (data.backups.length === 0) {
                    tbody.append(`
                        <tr>
                            <td colspan="3" class="text-center text-muted">
                                Резервные копии не найдены
                            </td>
                        </tr>
                    `);
                } else {
                    data.backups.forEach(backup => {
                        tbody.append(`
                            <tr>
                                <td>${backup.name}</td>
                                <td>${backup.size}</td>
                                <td>
                                    <button class="btn btn-sm btn-success" onclick="yandexSync.restoreBackup('${backup.path}')">
                                        <i class="fas fa-download me-1"></i>Восстановить
                                    </button>
                                </td>
                            </tr>
                        `);
                    });
                }
            } else {
                this.showNotification('Ошибка загрузки истории: ' + (data.error || 'Неизвестная ошибка'), 'error');
            }
        } catch (error) {
            this.showNotification('Ошибка загрузки истории резервных копий', 'error');
        }
    }

    async restoreBackup(remotePath) {
        try {
            if (!confirm(`Восстановить резервную копию "${remotePath.split('/').pop()}"?\nЭто заменит текущую базу данных!`)) {
                return;
            }

            this.showNotification('Восстановление данных...', 'info');

            const response = await fetch('/api/oauth/restore', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    remote_path: remotePath
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification(data.message, 'success');
                this.updateOAuthStatus();
                this.loadAllData(); // Перезагружаем все данные
            } else {
                this.showNotification('Ошибка: ' + (data.error || 'Неизвестная ошибка'), 'error');
            }
        } catch (error) {
            this.showNotification('Ошибка восстановления: ' + error.message, 'error');
        }
    }

    async cleanupBackups() {
        try {
            if (!confirm('Удалить старые резервные копии (старше 30 дней)?')) {
                return;
            }

            const response = await fetch('/api/oauth/cleanup', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification(data.message, 'success');
                this.updateOAuthStatus();
                this.loadBackupHistory();
            } else {
                this.showNotification('Ошибка: ' + (data.error || 'Неизвестная ошибка'), 'error');
            }
        } catch (error) {
            this.showNotification('Ошибка очистки: ' + error.message, 'error');
        }
    }

    async refreshToken() {
        try {
            const btn = $('#refresh-token-btn');
            btn.prop('disabled', true).text('Обновление токена...');

            const response = await fetch('/api/oauth/refresh', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('Токен успешно обновлен!', 'success');
                btn.hide();
                this.updateOAuthStatus();
            } else {
                this.showNotification('Ошибка обновления токена: ' + data.error, 'error');
            }
        } catch (error) {
            this.showNotification('Ошибка обновления токена: ' + error.message, 'error');
        } finally {
            const btn = $('#refresh-token-btn');
            btn.prop('disabled', false).text('Обновить токен');
        }
    }

    // ==================== УТИЛИТЫ ====================

    showNotification(message, type = 'info') {
        // Создаем уведомление
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';

        const iconClass = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'warning': 'fa-exclamation-triangle',
            'info': 'fa-info-circle'
        }[type] || 'fa-info-circle';

        const notification = $(`
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                <i class="fas ${iconClass} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `);

        // Добавляем в контейнер уведомлений
        $('#notifications-container').append(notification);

        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            notification.alert('close');
        }, 5000);
    }

    loadAllData() {
        // Перезагружаем все данные приложения
        if (typeof loadAllClients === 'function') loadAllClients();
        if (typeof loadAllContracts === 'function') loadAllContracts();
        if (typeof loadAllPayments === 'function') loadAllPayments();
        if (typeof loadAllTasks === 'function') loadAllTasks();
        if (typeof loadAllDocuments === 'function') loadAllDocuments();
        if (typeof loadAllReports === 'function') loadAllReports();
    }
}

// Инициализация при загрузке страницы
let yandexSync;

$(document).ready(function() {
    yandexSync = new YandexOAuthSync();
    
    // Показать контейнер OAuth синхронизации
    $('#yandex-oauth-container').show();
    
    // Загружаем историю резервных копий
    setTimeout(() => {
        if (yandexSync.oauthAuthorized) {
            yandexSync.loadBackupHistory();
        }
    }, 1000);
});

// Функции для использования в HTML (обратная совместимость)
function testConnection() {
    yandexSync.testConnection();
}

function uploadToCloud() {
    yandexSync.uploadToCloud();
}

function downloadFromCloud() {
    yandexSync.downloadFromCloud();
}

function toggleAutoSync(toggle) {
    yandexSync.toggleAutoSync(toggle);
}

function cleanupBackups() {
    yandexSync.cleanupBackups();
}

function restoreBackup(remotePath) {
    yandexSync.restoreBackup(remotePath);
}

function startOAuthAuthorization() {
    yandexSync.startOAuthAuthorization();
}

function refreshOAuthToken() {
    yandexSync.refreshToken();
}
