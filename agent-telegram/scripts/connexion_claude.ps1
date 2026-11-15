# Connecte l'agent a ton abonnement Claude (0 EUR en plus)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$py = ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "Lance d'abord install.bat" -ForegroundColor Yellow; exit 1 }

$exe = & $py -c "import claude_agent_sdk, os; print(os.path.join(os.path.dirname(claude_agent_sdk.__file__), '_bundled', 'claude.exe'))"
if (-not (Test-Path $exe)) { Write-Host "Claude Code introuvable : relance install.bat" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "=== Connexion a ton compte Claude ===" -ForegroundColor Cyan
Write-Host "Ton navigateur va s'ouvrir : connecte-toi avec le compte de ton abonnement et autorise."
Write-Host "Un jeton commencant par sk-ant-oat va ensuite s'afficher ici."
Write-Host ""
& $exe setup-token

Write-Host ""
$token = (Read-Host "Copie-colle le jeton ici puis Entree (clic droit = coller)").Trim()
if (-not $token.StartsWith("sk-ant-")) {
    Write-Host "Ca ne ressemble pas a un jeton. Relance connexion_claude.bat." -ForegroundColor Red
    exit 1
}

$envPath = Join-Path $Root ".env"
$lines = [IO.File]::ReadAllLines($envPath)
$found = $false
for ($i = 0; $i -lt $lines.Length; $i++) {
    if ($lines[$i] -match '^\s*CLAUDE_CODE_OAUTH_TOKEN\s*=') { $lines[$i] = "CLAUDE_CODE_OAUTH_TOKEN=$token"; $found = $true }
}
if (-not $found) { $lines += "CLAUDE_CODE_OAUTH_TOKEN=$token" }
[IO.File]::WriteAllLines($envPath, $lines, (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Connecte ! Le jeton est enregistre dans .env." -ForegroundColor Green
