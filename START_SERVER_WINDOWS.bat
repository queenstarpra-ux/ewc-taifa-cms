@echo off
title EWC CMS — Ebenezer Worship Centre Taifa
color 1F
echo.
echo  ============================================================
echo   Ebenezer Worship Centre Taifa — Church Management System
echo   The Church of Pentecost . Taifa District . Greater Accra
echo  ============================================================
echo.
python --version >nul 2>&1
if %errorlevel%==0 (set PY=python) else (
  python3 --version >nul 2>&1
  if %errorlevel%==0 (set PY=python3) else (
    echo  ERROR: Python 3 is not installed.
    echo  Download FREE from: https://www.python.org/downloads/
    echo  IMPORTANT: Tick "Add Python to PATH" during install!
    echo.
    pause & exit /b 1
  )
)
echo  Python found!
echo.
echo  Open your browser at:    http://127.0.0.1:3000
echo  Username: admin    Password: admin123
echo  Change password after first login!
echo.
echo  Press Ctrl+C to stop the server
echo  ============================================================
echo.
%PY% server.py
pause
