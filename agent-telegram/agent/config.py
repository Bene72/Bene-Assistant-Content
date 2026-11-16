"""Lecture de la configuration depuis le fichier .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# Deux bots possibles sur le même code : "coach" (.env, dossier data) et "box" (.env.box, data-box)
PROFILE = (os.getenv("AGENT_PROFILE") or "coach").strip().lower()
ENV_FILE = ROOT / (".env" if PROFILE == "coach" else f".env.{PROFILE}")
load_dotenv(ENV_FILE)

DATA_DIR = ROOT / ("data" if PROFILE == "coach" else f"data-{PROFILE}")
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
# BoxLog (app de la salle), lecture seule — utilisé par le profil "box"
BOX_SUPABASE_URL = _get("BOX_SUPABASE_URL").rstrip("/")
BOX_SUPABASE_KEY = _get("BOX_SUPABASE_KEY")
BOX_ID = _get("BOX_ID")
# Heure du brief du matin (HH:MM). Vide = pas de brief automatique.
BRIEF_TIME = _get("BRIEF_TIME", "07:30") if PROFILE == "coach" else ""
# Format du brief automatique : texte, vocal ou les deux
BRIEF_FORMAT = _get("BRIEF_FORMAT", "texte").lower()
# Voix des notes vocales (voix Microsoft Edge). Autres voix FR : fr-FR-VivienneMultilingualNeural,
# fr-FR-EloiseNeural (féminines), fr-FR-HenriNeural (masculine)
TTS_VOICE = _get("TTS_VOICE", "fr-FR-DeniseNeural")
TTS_RATE = _get("TTS_RATE", "+5%")
# Autoriser l'envoi de textes contenant des données clients au service vocal Microsoft
TTS_CLIENT_DATA = _get("TTS_CLIENT_DATA", "false").lower() in ("1", "true", "yes", "oui")
# Modèles par usage (vide = MODEL). Ex. Haiku au quotidien, Sonnet pour les réponses aux bilans.
MODEL_BRIEF = _get("MODEL_BRIEF") or MODEL
MODEL_COACH = _get("MODEL_COACH") or MODEL
# Si le PC était éteint à l'heure du brief, l'envoyer au démarrage jusqu'à cette heure (HH:MM)
BRIEF_CATCHUP_UNTIL = _get("BRIEF_CATCHUP_UNTIL", "12:00")
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
        problems.append(f"TELEGRAM_BOT_TOKEN manquant dans {ENV_FILE.name}")
    return problems
