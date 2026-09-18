@echo off
cd /d "%~dp0jd60"
python -m jd60
if errorlevel 1 pause
