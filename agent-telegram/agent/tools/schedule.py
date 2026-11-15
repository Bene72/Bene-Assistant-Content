"""Automatisations : création et gestion de tâches récurrentes."""
from .. import scheduler, storage
from . import tool


@tool("create_scheduled_task",
      "Crée une tâche récurrente. À chaque déclenchement, tu exécuteras la consigne 'prompt' "
      "(avec toutes tes compétences) et le résultat sera envoyé sur Telegram. "
      "Le planning est une expression cron à 5 champs, heure de Paris : "
      "'minute heure jour_du_mois mois jour_de_semaine'. Exemples : '0 8 * * mon' = chaque lundi 8h ; "
      "'30 7 * * *' = tous les jours 7h30 ; '0 18 1 * *' = le 1er de chaque mois à 18h ; "
      "'0 9 * * mon-fri' = jours de semaine 9h.",
      {"name": {"type": "string", "description": "Nom court de la tâche"},
       "cron": {"type": "string"},
       "prompt": {"type": "string", "description": "Consigne complète et autonome à exécuter"}},
      ["name", "cron", "prompt"])
async def create_scheduled_task(ctx, name: str, cron: str, prompt: str):
    scheduler.parse_cron(cron)  # lève une erreur si le cron est invalide
    tid = storage.add_task(name, cron, prompt, ctx["chat_id"])
    task = next(t for t in storage.list_tasks() if t["id"] == tid)
    scheduler.schedule(task)
    nxt = scheduler.next_run(tid)
    return f"Tâche #{tid} créée. Prochaine exécution : {nxt:%A %d/%m à %H:%M}." if nxt else f"Tâche #{tid} créée."


@tool("list_scheduled_tasks", "Liste les tâches récurrentes existantes avec leur prochaine exécution.")
async def list_scheduled_tasks(ctx):
    out = []
    for t in storage.list_tasks():
        nxt = scheduler.next_run(t["id"])
        out.append({"id": t["id"], "name": t["name"], "cron": t["cron"], "prompt": t["prompt"],
                    "prochaine": nxt.isoformat() if nxt else None})
    return out or "Aucune tâche planifiée."


@tool("delete_scheduled_task", "Supprime une tâche récurrente par son numéro.",
      {"task_id": {"type": "integer"}}, ["task_id"])
async def delete_scheduled_task(ctx, task_id: int):
    scheduler.unschedule(task_id)
    return "Tâche supprimée." if storage.delete_task(task_id) else "Tâche introuvable."


@tool("run_task_now", "Exécute immédiatement une tâche récurrente existante (pour la tester).",
      {"task_id": {"type": "integer"}}, ["task_id"])
async def run_task_now(ctx, task_id: int):
    import asyncio
    asyncio.create_task(scheduler._run_task(task_id))
    return "Lancée : le résultat arrivera dans un message séparé."
