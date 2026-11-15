"""Vie perso : to-do, anniversaires, journal, et le brief du matin."""
import datetime as dt
from zoneinfo import ZoneInfo

import holidays

from .. import config, storage
from . import tool


def _today() -> dt.date:
    return dt.datetime.now(ZoneInfo(config.TIMEZONE)).date()


def _date(s: str | None) -> str | None:
    return dt.date.fromisoformat(s).isoformat() if s else None


# --- To-do -----------------------------------------------------------------------
@tool("todo_add", "Ajoute une tâche à la to-do de l'utilisateur, avec une échéance optionnelle.",
      {"text": {"type": "string"},
       "due": {"type": "string", "description": "Échéance AAAA-MM-JJ (optionnel)"}}, ["text"])
async def todo_add(ctx, text: str, due: str | None = None):
    tid = storage.add_todo(text, _date(due))
    return f"Ajouté à la to-do (#{tid})."


@tool("todo_list", "Liste les tâches à faire (non terminées), en retard ou à venir.",
      {"until": {"type": "string", "description": "Ne garder que les échéances jusqu'à cette date "
                 "AAAA-MM-JJ (les tâches sans échéance sont toujours incluses)"}})
async def todo_list(ctx, until: str | None = None):
    items = storage.list_todos(_date(until))
    return items or "To-do vide."


@tool("todo_done", "Marque une tâche comme faite.", {"todo_id": {"type": "integer"}}, ["todo_id"])
async def todo_done(ctx, todo_id: int):
    return "Bien joué, c'est coché." if storage.done_todo(todo_id) else "Tâche introuvable."


@tool("todo_delete", "Supprime une tâche de la to-do.", {"todo_id": {"type": "integer"}}, ["todo_id"])
async def todo_delete(ctx, todo_id: int):
    return "Supprimée." if storage.delete_todo(todo_id) else "Tâche introuvable."


# --- Anniversaires -----------------------------------------------------------------
@tool("birthday_add", "Enregistre l'anniversaire d'une personne.",
      {"name": {"type": "string"},
       "day": {"type": "integer"}, "month": {"type": "integer"},
       "year": {"type": "integer", "description": "Année de naissance si connue (pour l'âge)"}},
      ["name", "day", "month"])
async def birthday_add(ctx, name: str, day: int, month: int, year: int | None = None):
    dt.date(2000, month, day)  # valide la date (2000 = bissextile, accepte le 29/02)
    storage.add_birthday(name, day, month, year)
    return f"Anniversaire de {name} enregistré ({day:02d}/{month:02d})."


@tool("birthday_list", "Liste les anniversaires à venir sur N jours (défaut 30), ou tous si days=0.",
      {"days": {"type": "integer"}})
async def birthday_list(ctx, days: int = 30):
    return upcoming_birthdays(_today(), days) or "Aucun anniversaire sur la période."


@tool("birthday_delete", "Supprime un anniversaire par son numéro.", {"birthday_id": {"type": "integer"}},
      ["birthday_id"])
async def birthday_delete(ctx, birthday_id: int):
    return "Supprimé." if storage.delete_birthday(birthday_id) else "Introuvable."


def upcoming_birthdays(today: dt.date, days: int) -> list[dict]:
    out = []
    for b in storage.list_birthdays():
        nxt = None
        for y in (today.year, today.year + 1):
            try:
                d = dt.date(y, b["month"], b["day"])
            except ValueError:  # 29 février une année non bissextile
                d = dt.date(y, 3, 1)
            if d >= today:
                nxt = d
                break
        delta = (nxt - today).days
        if days and delta > days:
            continue
        item = {"id": b["id"], "nom": b["name"], "date": nxt.isoformat(), "dans_jours": delta}
        if b["year"]:
            item["age"] = nxt.year - b["year"]
        out.append(item)
    return sorted(out, key=lambda x: x["dans_jours"])


# --- Journal -----------------------------------------------------------------------
@tool("journal_write", "Enregistre une entrée du journal personnel de l'utilisateur (son ressenti, "
      "ce qu'il a fait, ses victoires, ses apprentissages). Reformule fidèlement, sans inventer.",
      {"content": {"type": "string"},
       "date": {"type": "string", "description": "AAAA-MM-JJ, défaut aujourd'hui"}}, ["content"])
async def journal_write(ctx, content: str, date: str | None = None):
    storage.add_journal(_date(date) or _today().isoformat(), content)
    return "Ajouté au journal."


@tool("journal_read", "Relit le journal sur une période.",
      {"start": {"type": "string"}, "end": {"type": "string"}})
async def journal_read(ctx, start: str | None = None, end: str | None = None):
    s = _date(start) or (_today() - dt.timedelta(days=7)).isoformat()
    e = _date(end) or _today().isoformat()
    return storage.read_journal(s, e) or "Rien dans le journal sur cette période."


# --- Brief du matin ----------------------------------------------------------------
@tool("daily_brief_data",
      "Rassemble en un appel les données perso du jour pour le brief : rendez-vous du jour et du "
      "lendemain, to-do (en retard, du jour, sans échéance), anniversaires (aujourd'hui et 7 jours), "
      "jours fériés proches, l'entrée de journal d'hier et, si le dashboard est connecté, les "
      "points d'attention coaching.")
async def daily_brief_data(ctx):
    today = _today()
    data = {"date": today.isoformat(), "jour": ["lundi", "mardi", "mercredi", "jeudi", "vendredi",
                                                "samedi", "dimanche"][today.weekday()]}
    if config.CALENDARS:
        from .agenda import events_between
        data["rendez_vous"] = await events_between(today, today + dt.timedelta(days=2))
    else:
        data["rendez_vous"] = "agenda non connecté (CALENDARS vide dans .env)"
    todos = storage.list_todos(today.isoformat())
    data["todo"] = {
        "en_retard": [t for t in todos if t["due"] and t["due"] < today.isoformat()],
        "aujourdhui": [t for t in todos if t["due"] == today.isoformat()],
        "sans_echeance": [t for t in todos if not t["due"]],
    }
    data["anniversaires"] = upcoming_birthdays(today, 7)
    fr = holidays.France(years=[today.year, today.year + 1], language="fr")
    data["jours_feries_14j"] = [{"date": d.isoformat(), "nom": n} for d, n in sorted(fr.items())
                                if 0 <= (d - today).days <= 14]
    if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
        from .coaching import overview
        try:
            ov = await overview()
            data["coaching"] = {
                "points_attention": ov["points_attention"],
                "taches_coach_du_jour_ou_en_retard": [
                    t for t in ov["taches_coach_ouvertes"]
                    if t["en_retard"] or (t["echeance"] or "")[:10] == today.isoformat()],
            }
        except Exception as e:
            data["coaching"] = f"indisponible : {e}"
    yesterday = (today - dt.timedelta(days=1)).isoformat()
    data["journal_hier"] = storage.read_journal(yesterday, yesterday)
    return data
