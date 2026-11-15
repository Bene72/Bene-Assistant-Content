"""Lecture de la configuration depuis le fichier .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "agent.db"


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _ids(raw: str) -> set[int]:
    out = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            out.add(int(part))
    return out


# --- Connexion à Claude --------------------------------------------------------
# Mode "abonnement" : utilise ton abonnement Claude (0 € en plus) via un jeton
#   obtenu avec la commande `claude setup-token`.
# Mode "api" : clé API Anthropic facturée à l'usage.
CLAUDE_CODE_OAUTH_TOKEN = _get("CLAUDE_CODE_OAUTH_TOKEN")
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
AUTH_MODE = _get("AUTH_MODE", "abonnement" if CLAUDE_CODE_OAUTH_TOKEN or not ANTHROPIC_API_KEY else "api").lower()
if AUTH_MODE == "abonnement":
    # Sinon Claude Code utiliserait la clé API (payante) à la place de l'abonnement.
    os.environ.pop("ANTHROPIC_API_KEY", None)

# --- Obligatoire -------------------------------------------------------------
TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_IDS = _ids(_get("ALLOWED_USER_IDS"))

# --- Modèle ------------------------------------------------------------------
MODEL = _get("MODEL", "claude-sonnet-5-5")
MAX_TOKENS = int(_get("MAX_TOKENS", "4096"))
HISTORY_LENGTH = int(_get("HISTORY_LENGTH", "20"))
TIMEZONE = _get("TIMEZONE", "Europe/Paris")
OWNER_NAME = _get("OWNER_NAME", "Bene")

# --- Compétences optionnelles ------------------------------------------------
SUPABASE_URL = _get("SUPABASE_URL").rstrip("/")
SUPABASE_SERVICE_KEY = _get("SUPABASE_SERVICE_KEY")
GITHUB_TOKEN = _get("GITHUB_TOKEN")
GITHUB_OWNER = _get("GITHUB_OWNER", "Bene72")
WEB_SEARCH = _get("WEB_SEARCH", "true").lower() in ("1", "true", "yes", "oui")


def _calendars(raw: str) -> dict[str, str]:
    """'Perso=https://a.ics, Pro=https://b.ics' -> {'Perso': ..., 'Pro': ...}"""
    out = {}
    for i, part in enumerate(p.strip() for p in raw.split(",") if p.strip()):
        name, sep, url = part.partition("=")
        if sep and not name.lower().startswith(("http", "webcal")):
            out[name.strip()] = url.strip()
        else:
            out[f"Agenda {i + 1}"] = part
    return out


CALENDARS = _calendars(_get("CALENDARS"))
# Heure du brief du matin (HH:MM). Vide = pas de brief automatique.
BRIEF_TIME = _get("BRIEF_TIME", "07:30")
# Format du brief automatique : texte, vocal ou les deux
BRIEF_FORMAT = _get("BRIEF_FORMAT", "texte").lower()
# Voix des notes vocales (voix Microsoft Edge). Autres voix FR : fr-FR-VivienneMultilingualNeural,
# fr-FR-EloiseNeural (féminines), fr-FR-HenriNeural (masculine)
TTS_VOICE = _get("TTS_VOICE", "fr-FR-DeniseNeural")
TTS_RATE = _get("TTS_RATE", "+5%")
# Récap des bilans du week-end (cron, heure de Paris). Défaut : lundi 20h. Vide = désactivé.
BILANS_CRON = _get("BILANS_CRON", "0 20 * * mon")


def check() -> list[str]:
    """Retourne la liste des problèmes de configuration bloquants."""
    problems = []
    if AUTH_MODE == "abonnement" and not CLAUDE_CODE_OAUTH_TOKEN:
        problems.append("CLAUDE_CODE_OAUTH_TOKEN manquant dans .env (lance connexion_claude.bat)")
    if AUTH_MODE == "api" and not ANTHROPIC_API_KEY:
        problems.append("ANTHROPIC_API_KEY manquant dans .env")
    if not TELEGRAM_BOT_TOKEN:
        problems.append("TELEGRAM_BOT_TOKEN manquant dans .env")
    return problems
