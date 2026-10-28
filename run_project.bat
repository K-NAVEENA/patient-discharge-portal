
@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found. Please set up the project first.
    pause
    exit /b 1
)

echo Starting Patient Discharge Planning Portal...
call venv\Scripts\activate.bat
python app.py

pause
