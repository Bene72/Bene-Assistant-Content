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
