#!/usr/bin/env bash
# Installation de l'agent Ben&Fit sur Raspberry Pi (Raspberry Pi OS 64 bits)
# Usage : bash scripts/install_pi.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
USER_NAME="$(whoami)"

echo "=== Installation de l'agent Ben&Fit sur Raspberry Pi ==="
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

if [ ! -f .env ]; then
  cp .env.example .env
  echo ">> Fichier .env créé : remplis-le avec  nano .env  puis relance ce script."
  exit 0
fi

sudo tee /etc/systemd/system/benfit-agent.service >/dev/null <<EOF
[Unit]
Description=Agent Ben&Fit (Telegram + Claude)
After=network-online.target
Wants=network-online.target

[Service]
User=${USER_NAME}
WorkingDirectory=${ROOT}
ExecStart=${ROOT}/.venv/bin/python -m agent.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now benfit-agent
echo
echo "Agent installé et démarré. Il redémarrera tout seul avec le Pi."
echo "  Voir les logs :     journalctl -u benfit-agent -f"
echo "  Redémarrer :        sudo systemctl restart benfit-agent"
echo "  Arrêter :           sudo systemctl stop benfit-agent"
