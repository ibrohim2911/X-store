@echo off
title X-Store & Ngrok Startup
echo ==============================================
echo        Starting X-Store Application...
echo ==============================================
start "" "%~dp0dist\XStore.exe"

echo.
echo Waiting a few seconds for the app to start...
timeout /t 5 /nobreak >nul

echo.
echo ==============================================
echo    Starting Ngrok (Online Access)...
echo ==============================================
start "" ngrok http 8000

exit
