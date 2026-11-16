@echo off
chcp 65001 >nul
title Bot BoxLog
cd /d "%~dp0"
set AGENT_PROFILE=box
:loop
".venv\Scripts\python.exe" -m agent.main
if errorlevel 2 (
    pause
    exit /b 2
)
if errorlevel 1 (
    echo.
    echo Le bot BoxLog s'est arrete avec une erreur. Nouvelle tentative dans 15 secondes...
    timeout /t 15 >nul
    goto loop
)
pause
