@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LNK=%STARTUP%\Agent BenFit.lnk"
if exist "%LNK%" (
    del "%LNK%"
    echo Demarrage automatique DESACTIVE.
) else (
    powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%LNK%'); $s.TargetPath='%~dp0start.bat'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Save()"
    echo Demarrage automatique ACTIVE : l'agent se lancera a chaque ouverture de session Windows.
    echo Relance ce fichier pour le desactiver.
)
pause
