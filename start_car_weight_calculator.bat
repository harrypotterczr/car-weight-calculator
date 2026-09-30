@echo off
cd /d "%~dp0"

echo Stopping existing Car Weight Calculator server (server.js only)...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Where-Object { $_.CommandLine -like '*server.js*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo Starting Car Weight Calculator Server in background...
powershell -WindowStyle Hidden -Command "Start-Process -FilePath 'node.exe' -ArgumentList 'server.js' -WindowStyle Hidden"
echo Server started!
timeout /t 3
