@echo off
setlocal enabledelayedexpansion

title Intelligent Assignment Checker Dashboard

echo ========================================================
echo   INTELLIGENT ASSIGNMENT CHECKER - WEB DASHBOARD
echo   C++ Core Engine ^| DSA Analysis ^| Python Flask
echo ========================================================
echo.

:: Check for Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in PATH. Please install Python 3.
    pause
    exit /b 1
)

:: Check for Flask
python -c "import flask" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Flask not detected. Installing dependencies from requirements.txt...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

:: Check if checker.exe exists, if not build it
if not exist "checker.exe" (
    echo [INFO] checker.exe not found. Compiling main.cpp with g++...
    g++ -std=c++11 main.cpp -o checker.exe
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to compile main.cpp. Ensure MinGW g++ is in PATH.
        pause
        exit /b 1
    )
    echo [OK] checker.exe compiled successfully.
)

:: Open the browser after 2 seconds in parallel
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:5000"

echo.
echo [SERVER] Starting dashboard at http://127.0.0.1:5000
echo [SERVER] Press CTRL+C to stop the server.
echo.

python app.py

pause
