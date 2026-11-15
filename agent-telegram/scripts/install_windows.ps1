# Installation de l'agent Ben&Fit sous Windows
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host ""
Write-Host "=== Installation de l'agent Ben&Fit ===" -ForegroundColor Cyan

function Find-Python {
    foreach ($cmd in @("py -3", "python")) {
        try {
            $v = Invoke-Expression "$cmd -c `"import sys; print(sys.version_info[0]*100+sys.version_info[1])`"" 2>$null
            if ($v -and [int]$v -ge 310) { return $cmd }
        } catch {}
    }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Host "Python 3.10+ introuvable. Installation via winget..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    $py = Find-Python
    if (-not $py) {
        Write-Host "Python vient d'etre installe : ferme cette fenetre et relance install.bat." -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "Python trouve : $py" -ForegroundColor Green

if (-not (Test-Path ".venv")) {
    Write-Host "Creation de l'environnement..."
    Invoke-Expression "$py -m venv .venv"
}

Write-Host "Installation des dependances (inclut Claude Code, ~400 Mo : quelques minutes)..."
& ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) { throw "Echec de l'installation des dependances." }
Write-Host "Dependances installees." -ForegroundColor Green

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Fichier .env cree." -ForegroundColor Green
}

if (Select-String -Path ".env" -Pattern '^CLAUDE_CODE_OAUTH_TOKEN=\s*sk-ant-' -Quiet) {
    Write-Host "Deja connecte a ton compte Claude." -ForegroundColor Green
} else {
    & (Join-Path $PSScriptRoot "connexion_claude.ps1")
}

Write-Host ""
Write-Host "Derniere etape : colle le token de ton bot Telegram dans .env (il s'ouvre dans le Bloc-notes)," -ForegroundColor Cyan
Write-Host "a la ligne TELEGRAM_BOT_TOKEN=. Enregistre, puis double-clique sur start.bat."
Start-Process notepad.exe ".env"
