"""Notes vocales : synthèse vocale (voix Microsoft Edge, gratuite) envoyée sur Telegram."""
import logging
import re
import tempfile
from pathlib import Path

from . import config

log = logging.getLogger("voice")
_send_voice = None  # fonction async (chat_id, chemin_mp3, legende) branchée par main.py

EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⭐⭕⏰-⏺️‍]+")


def set_sender(func):
    global _send_voice
    _send_voice = func


def for_speech(text: str) -> str:
    """Nettoie un texte écrit pour qu'il passe bien à l'oral."""
    text = EMOJI.sub("", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[*_#`>]+", "", text)
    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.M)        # puces
    text = re.sub(r"(\d{1,2})h(\d{2})", r"\1 heures \2", text)  # 18h30 -> 18 heures 30
    text = re.sub(r"(\d{1,2})h\b", r"\1 heures", text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # chaque ligne devient une phrase pour que la voix marque une pause
    return " ".join(ln if ln[-1] in ".!?:;," else ln + "." for ln in lines)


async def synthesize(text: str) -> Path:
    import edge_tts  # import tardif : seul le mode vocal en a besoin

    path = Path(tempfile.gettempdir()) / f"benfit-vocal-{abs(hash(text)) % 10**8}.mp3"
    await edge_tts.Communicate(for_speech(text), config.TTS_VOICE, rate=config.TTS_RATE).save(str(path))
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError("fichier audio vide")
    return path


async def send(chat_id: int, text: str, caption: str = "") -> bool:
    """Envoie `text` en note vocale. Retourne False (sans planter) si la synthèse échoue."""
    if not _send_voice:
        return False
    try:
        path = await synthesize(text)
        await _send_voice(chat_id, path, caption)
        path.unlink(missing_ok=True)
        return True
    except Exception:
        log.exception("échec de la note vocale")
        return False
