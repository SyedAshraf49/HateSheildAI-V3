@echo off
echo ========================================
echo HateShield Setup and Run Script
echo ========================================
echo.

:: Check if Python is installed
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

echo [1/5] Python found!
py --version
echo.

:: Check if we're in the right directory
if not exist "backend\app.py" (
    echo ERROR: Please run this script from the HateShield root directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo [2/5] Installing backend dependencies...
cd backend
py -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo [3/5] Training ML model...
cd ml
if exist "hate_speech_model.pkl" (
    echo Model already exists, skipping training...
) else (
    py train_model.py
    if %errorlevel% neq 0 (
        echo ERROR: Failed to train model
        pause
        exit /b 1
    )
)
cd ..
cd ..
echo.

echo [4/5] Starting backend server...
start "HateShield Backend" cmd /k "cd /d %CD%\backend && py app.py"
timeout /t 3 /nobreak >nul
echo.

echo [5/5] Starting frontend server...
start "HateShield Frontend" cmd /k "cd /d %CD%\frontend && py -m http.server 8000"
timeout /t 2 /nobreak >nul
echo.

echo ========================================
echo HateShield is now running!
echo ========================================
echo.
echo Backend:  http://127.0.0.1:5000
echo Frontend: http://localhost:8000
echo.
echo Opening browser in 3 seconds...
timeout /t 3 /nobreak >nul

start http://localhost:8000

echo.
echo Press any key to stop all servers...
pause >nul

taskkill /FI "WindowTitle eq HateShield Backend*" /T /F >nul 2>&1
taskkill /FI "WindowTitle eq HateShield Frontend*" /T /F >nul 2>&1

echo All servers stopped.
pause