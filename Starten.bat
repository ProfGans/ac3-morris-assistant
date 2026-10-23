@echo off
cd /d "%~dp0"
python mainmenu.py
if errorlevel 1 pause
