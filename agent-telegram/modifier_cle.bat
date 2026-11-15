@echo off
chcp 65001 >nul
title Modifier une cle - Agent Ben&Fit
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo L'agent n'est pas installe. Lance d'abord install.bat
    pause
    exit /b 1
)
".venv\Scripts\python.exe" "scripts\set_env.py"
pause
