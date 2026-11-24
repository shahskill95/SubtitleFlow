@echo off
chcp 65001 >nul
setlocal
set "PY=%LOCALAPPDATA%\Python\pythoncore-3.11-64\python.exe"
if not exist "%PY%" (
  where python >nul 2>nul
  if not errorlevel 1 (set "PY=python") else (
    echo Python 3.11 nujen. Zapusti setup_windows.bat ili ustanovi Python 3.11.
    pause
    exit /b 1
  )
)
cd /d "%~dp0"
"%PY%" desktop_app.py
if errorlevel 1 pause
