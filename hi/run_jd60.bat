@echo off
cd /d "%~dp0"
python -m jd60 %*
if errorlevel 1 pause
