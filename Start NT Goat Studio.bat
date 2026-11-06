@echo off
cd /d "%~dp0"
python nt_goat_studio.py
if errorlevel 1 py nt_goat_studio.py
pause
