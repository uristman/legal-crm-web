@echo off
echo.
echo =====================================================
echo  🔐 Установка системы аутентификации для Legal CRM
echo =====================================================
echo.

echo Шаг 1: Создание резервной копии...
if exist app.py (
    copy app.py app_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%.py >nul
    echo ✅ Резервная копия создана
) else (
    echo ❌ Файл app.py не найден!
    pause
    exit /b 1
)

echo.
echo Шаг 2: Замена основного файла приложения...
if exist app_with_auth.py (
    copy app_with_auth.py app.py >nul
    echo ✅ app.py заменен на версию с аутентификацией
) else (
    echo ❌ Файл app_with_auth.py не найден!
    pause
    exit /b 1
)

echo.
echo Шаг 3: Проверка наличия всех необходимых файлов...

set files_ok=1

if not exist "templates\login.html" (
    echo ❌ templates\login.html - НЕ НАЙДЕН!
    set files_ok=0
) else (
    echo ✅ templates\login.html - OK
)

if not exist "templates\index.html" (
    echo ❌ templates\index.html - НЕ НАЙДЕН!
    set files_ok=0
) else (
    echo ✅ templates\index.html - OK
)

if not exist "static\js\main.js" (
    echo ❌ static\js\main.js - НЕ НАЙДЕН!
    set files_ok=0
) else (
    echo ✅ static\js\main.js - OK
)

if not exist "requirements.txt" (
    echo ❌ requirements.txt - НЕ НАЙДЕН!
    set files_ok=0
) else (
    echo ✅ requirements.txt - OK
)

echo.
if %files_ok%==1 (
    echo =====================================================
    echo  ✅ УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!
    echo =====================================================
    echo.
    echo Учетные данные администратора:
    echo   Логин: admin
    echo   Пароль: admin123
    echo.
    echo ⚠️  ОБЯЗАТЕЛЬНО измените пароль после первого входа!
    echo.
    echo Для запуска приложения:
    echo   python app.py
    echo.
    echo Для развертывания на Render.com:
    echo   1. Загрузите файлы на GitHub
    echo   2. Подключите репозиторий к Render.com
    echo   3. Добавьте переменные окружения:
    echo      SECRET_KEY=ваш_секретный_ключ
    echo      ADMIN_PASSWORD=ваш_пароль
    echo.
) else (
    echo =====================================================
    echo  ❌ УСТАНОВКА НЕ ЗАВЕРШЕНА - ЕСТЬ ОШИБКИ!
    echo =====================================================
    echo.
    echo Убедитесь, что все необходимые файлы находятся в папке:
    echo   - app_with_auth.py
    echo   - templates\login.html
    echo   - templates\index.html
    echo   - static\js\main.js
    echo   - requirements.txt
    echo.
)

echo.
pause