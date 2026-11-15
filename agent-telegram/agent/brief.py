"""Brief du matin : consigne et création automatique de la tâche quotidienne."""
import logging

from . import config, scheduler, storage

log = logging.getLogger("brief")
NAME = "Brief du matin"

PROMPT = """Fais mon brief du matin.
1. Appelle daily_brief_data pour mes données perso.
2. Cherche sur le web la fête du jour (saint du calendrier français) et les actus importantes \
des dernières 24 h : 4 actus monde/France et 1 actu sport.
3. Rédige le brief dans cet ordre, court et lisible sur téléphone, sans Markdown :

☀️ [Jour date] + fête du jour (+ jour férié s'il y en a un)
📅 Rendez-vous : heure, titre, lieu. Si rien : « Journée libre d'agenda ».
✅ À faire : d'abord les tâches en retard, puis celles du jour, puis 2-3 sans échéance max.
🏋️ Coaching (si dispo) : tâches coach du jour/en retard, puis les points d'attention \
athlètes les plus importants (fin de cycle/engagement, athlètes sans séance, bilans manquants, \
messages non lus). 6 lignes max, regroupe si besoin.
🎂 Anniversaires : aujourd'hui en premier, puis ceux des 7 prochains jours (avec l'âge si connu).
🌍 Le monde : 5 actus, une ligne chacune.
💬 Une phrase d'élan pour la journée (pas niaise).

N'invente rien : si une rubrique est vide, dis-le en quelques mots ou saute-la."""


ORAL_PROMPT = """Fais mon brief du matin, mais pour une NOTE VOCALE d'1 à 2 minutes.
1. Appelle daily_brief_data, puis cherche sur le web la fête du jour et 4-5 actus importantes \
des dernières 24 h (monde, France, sport).
2. Rédige un texte fait pour être écouté : comme une amie qui te briefe, tutoiement, phrases \
courtes qui s'enchaînent, aucun émoji, aucune liste, aucun lien, aucun symbole. Écris les \
heures en toutes lettres (« 18 heures 30 »). Ordre : bonjour + date + fête du jour, \
rendez-vous, tâches importantes, points coaching s'il y en a, anniversaires, actus en \
une phrase chacune, puis une phrase d'élan pour finir.
3. Réponds UNIQUEMENT avec ce texte, sans titre ni commentaire, et n'appelle pas send_voice_note."""

FORMATS = {"texte": "texte", "text": "texte", "écrit": "texte", "ecrit": "texte",
           "vocal": "vocal", "audio": "vocal", "voix": "vocal", "oral": "vocal",
           "deux": "les deux", "les deux": "les deux", "both": "les deux", "tout": "les deux"}


def parse_format(raw: str | None, default: str = "texte") -> str:
    raw = (raw or "").strip().lower()
    return FORMATS.get(raw, FORMATS.get(raw.split()[-1], default) if raw else default)


async def run(chat_id: int, fmt: str, send_text) -> None:
    """Produit le brief au format demandé et l'envoie (send_text : coroutine (chat_id, texte))."""
    from . import voice
    from .brain import think

    if fmt == "vocal":
        oral = await think(chat_id, ORAL_PROMPT, use_history=False)
        if not await voice.send(chat_id, oral, caption="☀️ Brief du matin"):
            await send_text(chat_id, "(La note vocale a échoué, voici le brief en texte.)\n\n" + oral)
        return
    text = await think(chat_id, PROMPT, use_history=False)
    await send_text(chat_id, text)
    if fmt == "les deux":
        await voice.send(chat_id, text, caption="☀️ Brief du matin (version audio)")


BILANS_NAME = "Bilans du week-end"
BILANS_PROMPT = """Fais le point sur les bilans hebdo : appelle coaching_bilans_weekend.
Rédige sans Markdown, court :
📋 Bilans du [vendredi] au [lundi]
✅ Faits (X/Y) : une ligne par athlète avec quand, ses scores en bref et, s'il y en a, le \
signal à surveiller (douleur, moral bas, sommeil en chute, diète ou training en difficulté).
⏳ Pas encore faits : les noms.
Termine par : « Dis-moi "réponse pour [prénom]" et je te prépare le message. »"""


def ensure_daily_task():
    """Crée (ou met à jour) les tâches automatiques pour chaque utilisateur autorisé."""
    if not config.ALLOWED_USER_IDS:
        return
    if config.BRIEF_TIME:
        try:
            hh, mm = (int(x) for x in config.BRIEF_TIME.split(":"))
            _ensure(NAME, f"{mm} {hh} * * *", PROMPT)
        except Exception:
            log.error("BRIEF_TIME invalide (%s), format attendu HH:MM", config.BRIEF_TIME)
    if config.BILANS_CRON and config.SUPABASE_URL:
        try:
            _ensure(BILANS_NAME, config.BILANS_CRON, BILANS_PROMPT)
        except Exception:
            log.error("BILANS_CRON invalide (%s)", config.BILANS_CRON)


def _ensure(name: str, cron: str, prompt: str):
    scheduler.parse_cron(cron)
    NAME_ = name
    existing = {t["chat_id"]: t for t in storage.list_tasks() if t["name"] == NAME_}
    for uid in config.ALLOWED_USER_IDS:
        t = existing.get(uid)
        if t and t["cron"] == cron and t["prompt"] == prompt:
            continue
        if t:
            scheduler.unschedule(t["id"])
            storage.delete_task(t["id"])
        storage.add_task(name, cron, prompt, uid)
        log.info("« %s » programmé (%s) pour %s", name, cron, uid)
