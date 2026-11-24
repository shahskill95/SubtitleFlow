@echo off
chcp 65001 >nul
setlocal
set "PY=%LOCALAPPDATA%\Python\pythoncore-3.11-64\python.exe"
if not exist "%PY%" (
  where python >nul 2>nul
  if not errorlevel 1 (set "PY=python") else (
    echo Python ne naiden. Nuzhen Python 3.11.
    pause
    exit /b 1
  )
)
echo Proveryayu i ustanavlivayu zavisimosti...
"%PY%" -m pip install -U openai-whisper deep-translator
if errorlevel 1 (
  echo Ne udalos ustanovit zavisimosti.
  pause
  exit /b 1
)
echo.
echo Gotovo. Teper zapusti start_subtitleflow.bat
pause
