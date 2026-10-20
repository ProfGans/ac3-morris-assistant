@echo off
cd /d "%~dp0"
python morris.py
if errorlevel 1 pause
