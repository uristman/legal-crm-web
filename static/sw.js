// 📱 Service Worker для Legal CRM PWA
// Обеспечивает работу приложения в offline режиме

const CACHE_NAME = 'legal-crm-v1.0.0';
const urlsToCache = [
  '/',
  '/static/mobile-responsive.css',
  '/login',
  '/dashboard',
  '/clients',
  '/static/favicon.ico',
  '/static/apple-touch-icon.png'
];

// Установка Service Worker
self.addEventListener('install', function(event) {
  console.log('🔧 Service Worker: Установка...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        console.log('💾 Service Worker: Кэш открыт');
        return cache.addAll(urlsToCache);
      })
      .then(function() {
        console.log('✅ Service Worker: Файлы кэшированы');
        return self.skipWaiting();
      })
      .catch(function(error) {
        console.error('❌ Service Worker: Ошибка кэширования:', error);
      })
  );
});

// Активация Service Worker
self.addEventListener('activate', function(event) {
  console.log('🚀 Service Worker: Активация...');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            console.log('🗑️ Service Worker: Удаление старого кэша:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(function() {
      console.log('✅ Service Worker: Активен');
      return self.clients.claim();
    })
  );
});

// Перехват сетевых запросов
self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Возвращаем кэшированную версию если есть
        if (response) {
          console.log('📦 Service Worker: Отдача из кэша:', event.request.url);
          return response;
        }

        // Иначе делаем сетевой запрос
        return fetch(event.request)
          .then(function(response) {
            // Проверяем, что ответ валидный
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Клонируем ответ для кэширования
            const responseToCache = response.clone();

            caches.open(CACHE_NAME)
              .then(function(cache) {
                cache.put(event.request, responseToCache);
              });

            console.log('🌐 Service Worker: Загрузка с сервера:', event.request.url);
            return response;
          })
          .catch(function(error) {
            console.error('❌ Service Worker: Ошибка сети:', error);
            
            // Показываем offline страницу для навигационных запросов
            if (event.request.destination === 'document') {
              return caches.match('/offline.html');
            }
          });
      })
  );
});

// Обработка push уведомлений (для будущего использования)
self.addEventListener('push', function(event) {
  console.log('🔔 Service Worker: Получено push уведомление');
  
  const options = {
    body: event.data ? event.data.text() : 'Новое уведомление Legal CRM',
    icon: '/static/icon-192.png',
    badge: '/static/badge-72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Открыть Legal CRM',
        icon: '/static/checkmark.png'
      },
      {
        action: 'close',
        title: 'Закрыть',
        icon: '/static/xmark.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('Legal CRM', options)
  );
});

// Обработка кликов по уведомлениям
self.addEventListener('notificationclick', function(event) {
  console.log('👆 Service Worker: Клик по уведомлению');
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// 📱 Дополнительные PWA функции

// Функция для определения подключения к интернету
function isOnline() {
  return navigator.onLine;
}

// Функция для синхронизации данных
function syncData() {
  if (isOnline()) {
    console.log('🌐 Синхронизация данных...');
    // Здесь можно добавить логику синхронизации с сервером
  } else {
    console.log('📵 Offline режим');
  }
}

// Функция для показа индикатора сети
function showNetworkStatus() {
  const status = document.createElement('div');
  status.id = 'network-status';
  status.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    padding: 0.5rem;
    text-align: center;
    font-size: 0.875rem;
    font-weight: 500;
    z-index: 1000;
    transition: all 0.3s ease;
    transform: translateY(-100%);
  `;

  if (isOnline()) {
    status.style.background = '#16a34a';
    status.style.color = 'white';
    status.textContent = '🟢 Подключено к интернету';
  } else {
    status.style.background = '#dc2626';
    status.style.color = 'white';
    status.textContent = '🔴 Нет подключения к интернету';
  }

  document.body.appendChild(status);
  
  // Показываем с анимацией
  setTimeout(() => {
    status.style.transform = 'translateY(0)';
  }, 100);

  // Скрываем через 3 секунды
  setTimeout(() => {
    status.style.transform = 'translateY(-100%)';
    setTimeout(() => status.remove(), 300);
  }, 3000);
}

// Слушаем события подключения к сети
window.addEventListener('online', showNetworkStatus);
window.addEventListener('offline', showNetworkStatus);

// 📊 Аналитика для PWA (опционально)
function trackPWAUsage() {
  // Проверяем, запущено ли приложение как PWA
  if (window.matchMedia('(display-mode: standalone)').matches) {
    console.log('📱 Запущено как PWA');
    // Здесь можно отправить аналитику
  }
}

// Функция для обновления PWA
function checkForUpdates() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready.then(function(registration) {
      registration.addEventListener('updatefound', function() {
        const newWorker = registration.installing;
        console.log('🔄 Обнаружена новая версия');
        
        newWorker.addEventListener('statechange', function() {
          if (newWorker.state === 'installed') {
            if (navigator.serviceWorker.controller) {
              // Новая версия доступна
              showUpdateNotification();
            } else {
              // Первая установка
              console.log('✅ PWA успешно установлена');
            }
          }
        });
      });
    });
  }
}

// Показ уведомления об обновлении
function showUpdateNotification() {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    bottom: 20px;
    left: 20px;
    right: 20px;
    background: var(--primary-color, #2563eb);
    color: white;
    padding: 1rem;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    z-index: 1000;
    text-align: center;
  `;
  
  notification.innerHTML = `
    <div style="margin-bottom: 0.5rem;">📱 Новая версия Legal CRM готова</div>
    <button onclick="location.reload()" style="
      background: white;
      color: var(--primary-color);
      border: none;
      padding: 0.5rem 1rem;
      border-radius: 4px;
      cursor: pointer;
      font-weight: 500;
    ">
      Обновить сейчас
    </button>
    <button onclick="this.parentElement.remove()" style="
      background: transparent;
      color: white;
      border: 1px solid rgba(255,255,255,0.5);
      padding: 0.5rem 1rem;
      border-radius: 4px;
      cursor: pointer;
      margin-left: 0.5rem;
    ">
      Позже
    </button>
  `;
  
  document.body.appendChild(notification);
}

// Инициализация PWA функций
document.addEventListener('DOMContentLoaded', function() {
  trackPWAUsage();
  checkForUpdates();
  
  // Показываем статус сети при загрузке
  if (!isOnline()) {
    setTimeout(showNetworkStatus, 1000);
  }
});

// 🔧 Регистрация Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/sw.js')
      .then(function(registration) {
        console.log('✅ Service Worker зарегистрирован успешно:', registration.scope);
        
        // Проверяем обновления
        registration.addEventListener('updatefound', function() {
          console.log('🔄 Проверка обновлений...');
        });
      })
      .catch(function(error) {
        console.error('❌ Ошибка регистрации Service Worker:', error);
      });
  });
}

// 📱 PWA манифест (создайте отдельный файл manifest.json)
const manifest = {
  "name": "Legal CRM",
  "short_name": "LegalCRM",
  "description": "Система управления юридической практикой",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#f8fafc",
  "theme_color": "#2563eb",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/static/icon-72.png",
      "sizes": "72x72",
      "type": "image/png"
    },
    {
      "src": "/static/icon-192.png", 
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/static/icon-512.png",
      "sizes": "512x512", 
      "type": "image/png"
    }
  ],
  "categories": ["business", "productivity"],
  "lang": "ru",
  "dir": "ltr"
};

// Экспорт функций для использования в других скриптах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    isOnline,
    syncData,
    showNetworkStatus,
    checkForUpdates,
    showUpdateNotification,
    trackPWAUsage
  };
}
