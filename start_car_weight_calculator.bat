@echo off
echo Stopping existing node.js services...
taskkill /F /IM node.exe >nul 2>&1

echo Starting Car Weight Calculator Server in background...
powershell -WindowStyle Hidden -Command "Start-Process -FilePath 'node.exe' -ArgumentList 'server.js' -WindowStyle Hidden"
echo Server started!
timeout /t 3
