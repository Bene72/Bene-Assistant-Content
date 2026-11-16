@echo off
chcp 65001 >nul
title Installer le bot BoxLog
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo L'agent n'est pas installe. Lance d'abord install.bat
    pause
    exit /b 1
)
".venv\Scripts\python.exe" "scripts\setup_box.py"
pause
