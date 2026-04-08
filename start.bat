@echo off
title PixelForge Launcher

echo Stopping any previous PixelForge servers...

:: Kill any uvicorn / Python backend process
wmic process where "commandline like '%%uvicorn%%'" call terminate >nul 2>&1

:: Kill any node / npm frontend process on port 3000
wmic process where "commandline like '%%vite%%'" call terminate >nul 2>&1

:: Also kill our titled CMD windows if they are still open
taskkill /F /FI "WINDOWTITLE eq PixelForge Backend*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq PixelForge Frontend*" /T >nul 2>&1

:: Give Windows time to fully release the sockets
echo Waiting for ports to clear...
timeout /t 4 /nobreak >nul

echo Starting PixelForge Backend...
start "PixelForge Backend" cmd /k "cd /d C:\Users\chris\Desktop\PixelForge && "C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn backend.main:app --port 8000 && pause"

timeout /t 4 /nobreak >nul

echo Starting PixelForge Frontend...
start "PixelForge Frontend" cmd /k "cd /d C:\Users\chris\Desktop\PixelForge\frontend && npm run dev"

echo Waiting for servers to boot...
timeout /t 5 /nobreak >nul

echo Opening browser...
start "" http://localhost:3000

exit
