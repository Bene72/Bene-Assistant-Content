@echo off
chcp 65001 >nul
title Agent Ben^&Fit
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo L'agent n'est pas installe. Lance d'abord install.bat
    pause
    exit /b 1
)
echo Verification des dependances...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt --disable-pip-version-check
if exist ".env.box" start "Bot BoxLog" /min "%~dp0start_box.bat"
:loop
".venv\Scripts\python.exe" -m agent.main
if errorlevel 2 (
    pause
    exit /b 2
)
if errorlevel 1 (
    echo.
    echo L'agent s'est arrete avec une erreur. Nouvelle tentative dans 15 secondes...
    echo Ferme cette fenetre pour l'arreter.
    timeout /t 15 >nul
    goto loop
)
pause
