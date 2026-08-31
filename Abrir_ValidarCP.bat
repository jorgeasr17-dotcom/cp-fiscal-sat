@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Abriendo CP fiscal Matamoros en http://127.0.0.1:5099
start "" http://127.0.0.1:5099
python app.py
if errorlevel 1 pause
