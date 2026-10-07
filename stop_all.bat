@echo off
title AepttasShield Shutdown Utility
cd /d "%~dp0"
node scripts/stop-backends.js
pause
