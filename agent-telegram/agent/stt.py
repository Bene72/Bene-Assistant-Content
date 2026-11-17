"""Reconnaissance vocale LOCALE (faster-whisper) : tes notes vocales ne quittent pas ta machine.

Le modèle est téléchargé une seule fois au premier vocal (~460 Mo pour « small »),
dans data/whisper/. Ensuite tout fonctionne hors ligne.
"""
import asyncio
import logging
import threading

from . import config

log = logging.getLogger("stt")
_model = None
_lock = threading.Lock()


def model_dir():
    return config.DATA_DIR / "whisper"


def is_downloaded() -> bool:
    d = model_dir()
    return d.exists() and any(d.rglob("model.bin"))


def _load():
    global _model
    with _lock:
        if _model is None:
            from faster_whisper import WhisperModel  # import tardif : lourd
            log.info("chargement du modèle vocal %s…", config.STT_MODEL)
            _model = WhisperModel(config.STT_MODEL, device="cpu", compute_type="int8",
                                  download_root=str(model_dir()))
    return _model


def _transcribe(path: str) -> str:
    segments, _info = _load().transcribe(path, language=config.STT_LANGUAGE or None, beam_size=2,
                                         vad_filter=True)
    return " ".join(s.text.strip() for s in segments).strip()


async def transcribe(path: str) -> str:
    """Transcrit un fichier audio (ogg/opus de Telegram, mp3, wav…)."""
    return await asyncio.to_thread(_transcribe, path)
