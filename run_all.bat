@echo off
title AepttasShield Full Stack Launcher
echo ========================================================
echo Starting All Backend Servers and React Native UI...
echo ========================================================

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

echo [1/4] Starting Malware APK Scanner Backend (Port 8001)...
start "Malware Backend" /d "%ROOT_DIR%backend\malware" cmd /k "node server_mal.js"

echo [2/4] Starting Vulnerability Backend (Port 8000)...
start "Vulnerability Backend" /d "%ROOT_DIR%backend\vulnerability" cmd /k "python run_server.py"

echo [3/4] Starting PostgreSQL Auth Backend (Port 8002)...
start "Auth Backend" /d "%ROOT_DIR%backend-reference" cmd /k "python run_postgres_auth_server.py"

echo [4/5] Starting Geolocation Backend (Port 8003)...
start "Geolocation Backend" /d "%ROOT_DIR%backend\geolocation-backend-fixed-main" cmd /k "python run_server.py"

echo [5/6] Starting Caller Intelligence Backend (Port 8004)...
start "Caller Intelligence Backend" /d "%ROOT_DIR%backend\caller-intelligence-backend-main\Backend file" cmd /k "python run_server.py"

echo [6/6] Starting Parental Control Backend (Port 8005)...
start "Parental Control Backend" /d "%ROOT_DIR%backend\parental-control-backend-main" cmd /k "python run_server.py"

echo.
echo ========================================================
echo Launching Android App / Emulator...
echo ========================================================
echo.

call npx react-native run-android

pause
