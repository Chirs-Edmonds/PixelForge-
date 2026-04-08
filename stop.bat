@echo off
title PixelForge Stop

echo Stopping PixelForge servers...

taskkill /F /FI "WINDOWTITLE eq PixelForge Backend*" /T
taskkill /F /FI "WINDOWTITLE eq PixelForge Frontend*" /T

echo PixelForge stopped.
pause
