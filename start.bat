@echo off
chcp 65001 >nul
cls

echo.
echo ========================================
echo Legal CRM Web - Starting Web Application
echo ========================================
echo.
echo Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ========================================
    echo INSTALLATION ERROR!
    echo ========================================
    echo Make sure Python is installed and added to PATH
    echo Try using: python -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo.
echo Starting web server...
echo Legal CRM Web will be available at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py