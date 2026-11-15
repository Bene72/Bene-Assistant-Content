"""Planificateur : exécute les tâches récurrentes et envoie le résultat sur Telegram."""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from . import config, storage

log = logging.getLogger("scheduler")
scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)
_send = None  # fonction async (chat_id, texte) branchée par main.py


def set_sender(func):
    global _send
    _send = func


def parse_cron(cron: str) -> CronTrigger:
    """Valide une expression cron à 5 champs (minute heure jour mois jour_semaine)."""
    return CronTrigger.from_crontab(cron.strip(), timezone=config.TIMEZONE)


async def _run_task(task_id: int):
    from .brain import think  # import tardif pour éviter les boucles

    task = next((t for t in storage.list_tasks() if t["id"] == task_id), None)
    if not task or not task["enabled"]:
        return
    log.info("tâche %s : %s", task_id, task["name"])
    from . import brief
    if task["name"] == brief.NAME and _send:
        try:
            brief.mark_sent()
            await brief.run(task["chat_id"], brief.parse_format(config.BRIEF_FORMAT), _send)
        except Exception as e:
            log.exception("échec du brief")
            await _send(task["chat_id"], f"Le brief a échoué : {e}")
        return
    prompt = (
        f"[Tâche automatique « {task['name']} »] {task['prompt']}\n"
        "Exécute-la maintenant et rédige directement le message final à envoyer."
    )
    try:
        text = await think(task["chat_id"], prompt, use_history=False)
    except Exception as e:
        log.exception("échec tâche %s", task_id)
        text = f"La tâche a échoué : {e}"
    if _send:
        await _send(task["chat_id"], f"⏰ {task['name']}\n\n{text}")


def schedule(task: dict):
    scheduler.add_job(
        _run_task, parse_cron(task["cron"]), args=[task["id"]],
        id=f"task-{task['id']}", replace_existing=True, misfire_grace_time=3600,
    )


def unschedule(task_id: int):
    job = scheduler.get_job(f"task-{task_id}")
    if job:
        job.remove()


def next_run(task_id: int):
    job = scheduler.get_job(f"task-{task_id}")
    return job.next_run_time if job else None


def start():
    for task in storage.list_tasks(enabled_only=True):
        try:
            schedule(task)
        except Exception:
            log.exception("tâche %s invalide", task["id"])
    scheduler.start()
    log.info("planificateur démarré (%d tâches)", len(scheduler.get_jobs()))
