"""« Chroniques de la pensée » : la chronique philosophique du point quotidien.

Une chronique par jour au maximum, envoyée juste après le brief (texte + note vocale selon
CHRONIQUE_FORMAT). Les épisodes passés sont gardés pour varier auteurs et thèmes.
Le cahier des charges est dans agent/prompts/chronique.md (fichier privé, pas sur GitHub).
"""
import datetime as dt
import logging
import re
import time
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config, storage

log = logging.getLogger("chronique")
SPEC = Path(__file__).parent / "prompts" / "chronique.md"

ASK = """Écris l'épisode {num} de mes « Chroniques de la pensée », en suivant à la lettre le cahier \
des charges ci-dessous.

Épisodes déjà diffusés (les plus récents d'abord) — ne reprends ni le même auteur principal ni le \
même thème que les 15 derniers, et fais progresser l'ensemble :
{history}

Vérifie sur le web toute date, titre d'œuvre ou citation dont tu n'es pas certain. Aucune citation \
inventée. Réponds UNIQUEMENT avec la chronique, au format final demandé, en texte simple sans \
Markdown (pas de **, pas de #). Commence exactement par « CHRONIQUES DE LA PENSÉE » puis \
« Épisode {num} — [Titre] ».

=== CAHIER DES CHARGES ===
{spec}"""


def enabled() -> bool:
    return config.CHRONIQUE_FORMAT != "off" and SPEC.exists()


def _init_table():
    with storage.db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS chroniques (
            num INTEGER PRIMARY KEY, day TEXT NOT NULL, title TEXT, theme TEXT, authors TEXT,
            text TEXT NOT NULL, ts REAL NOT NULL)""")


def episodes(limit: int = 60) -> list[dict]:
    _init_table()
    with storage.db() as c:
        return [dict(r) for r in c.execute(
            "SELECT num, day, title, theme, authors FROM chroniques ORDER BY num DESC LIMIT ?", (limit,))]


def _today() -> str:
    return dt.datetime.now(ZoneInfo(config.TIMEZONE)).date().isoformat()


def done_today() -> bool:
    return any(e["day"] == _today() for e in episodes(1))


def _field(text: str, label: str) -> str:
    m = re.search(rf"^\s*{label}\s*:\s*(.+)$", text, flags=re.M | re.I)
    return m[1].strip()[:200] if m else ""


def parse(text: str) -> dict:
    m = re.search(r"[ÉE]pisode\s+\d+\s*[—–-]\s*(.+)", text)
    return {"title": m[1].strip()[:200] if m else "",
            "theme": _field(text, "Th[èe]me"),
            "authors": _field(text, r"Auteur\(?s?\)?")}


def for_voice(text: str) -> str:
    """Version à écouter : sans la fiche (thème/auteur/période) ni la référence bibliographique."""
    out, skip = [], False
    for line in text.splitlines():
        s = line.strip()
        if re.match(r"(?i)^(th[èe]me|auteur\(?s?\)?|p[ée]riode)\s*:", s):
            continue
        if re.match(r"(?i)^pour aller plus loin", s):
            skip = True
            continue
        if re.match(r"(?i)^(la question du jour|à retenir)", s):
            skip = False
            s = s.capitalize()
        if s.upper() == "CHRONIQUES DE LA PENSÉE":
            s = "Chroniques de la pensée"
        if not skip:
            out.append(s)
    return "\n".join(out)


async def write(chat_id: int) -> str:
    """Rédige et enregistre l'épisode suivant. Retourne le texte."""
    from .brain import think

    past = episodes()
    num = (past[0]["num"] + 1) if past else 1
    history = "\n".join(f"- Ép. {e['num']} ({e['day']}) : {e['title']} | {e['theme']} | {e['authors']}"
                        for e in past) or "- aucun (c'est le premier épisode)"
    ctx: dict = {"allowed": set()}  # pas d'outil perso : seulement la recherche web
    text = (await think(chat_id, ASK.format(num=num, history=history, spec=SPEC.read_text(encoding="utf-8")),
                        ctx=ctx, use_history=False, model=config.MODEL_CHRONIQUE)).strip()
    if len(text) < 300:
        raise RuntimeError("chronique trop courte ou vide")
    meta = parse(text)
    with storage.db() as c:
        c.execute("INSERT INTO chroniques(num, day, title, theme, authors, text, ts) VALUES (?,?,?,?,?,?,?)",
                  (num, _today(), meta["title"], meta["theme"], meta["authors"], text, time.time()))
    return text


def today_text() -> str | None:
    _init_table()
    with storage.db() as c:
        r = c.execute("SELECT text FROM chroniques WHERE day=? ORDER BY num DESC LIMIT 1", (_today(),)).fetchone()
    return r["text"] if r else None


async def deliver(chat_id: int, send_text, force: bool = False) -> None:
    """Envoie la chronique du jour (une seule par jour, sauf force=True)."""
    from . import voice

    if not enabled() or (done_today() and not force):
        return
    try:
        text = (None if force else today_text()) or await write(chat_id)
    except Exception as e:
        log.exception("chronique")
        await send_text(chat_id, f"La chronique du jour n'a pas pu être écrite ({type(e).__name__}).")
        return
    if config.CHRONIQUE_FORMAT in ("texte", "les deux"):
        await send_text(chat_id, "🎙️ " + text)
    if config.CHRONIQUE_FORMAT in ("vocal", "les deux"):
        if not await voice.send(chat_id, for_voice(text), caption="🎙️ Chroniques de la pensée"):
            if config.CHRONIQUE_FORMAT == "vocal":
                await send_text(chat_id, "(La note vocale a échoué, voici la chronique.)\n\n" + text)
