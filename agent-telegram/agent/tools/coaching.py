"""Coaching : lecture des données du dashboard Ben&Fit (Supabase), en LECTURE SEULE.

Aucune fonction ici n'écrit ni ne supprime de données : les données clients
restent intactes quoi que l'agent fasse.
"""
import httpx

from .. import config
from . import tool

_enabled = lambda: bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY)  # noqa: E731
_schema_cache: dict | None = None


def _headers():
    k = config.SUPABASE_SERVICE_KEY
    return {"apikey": k, "Authorization": f"Bearer {k}"}


async def _get(path: str, params=None, extra_headers=None):  # params : dict ou liste de tuples
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{config.SUPABASE_URL}/rest/v1/{path}", params=params,
                        headers={**_headers(), **(extra_headers or {})})
    if r.status_code >= 400:
        raise RuntimeError(f"Supabase {r.status_code} : {r.text[:500]}")
    return r


@tool("coaching_list_tables",
      "Liste les tables du dashboard coach Ben&Fit (Supabase) avec leurs colonnes. "
      "À appeler en premier pour découvrir la structure (athlètes, workouts, cycles…).",
      enabled=_enabled)
async def coaching_list_tables(ctx):
    global _schema_cache
    if _schema_cache is None:
        r = await _get("", extra_headers={"Accept": "application/openapi+json"})
        spec = r.json()
        defs = spec.get("definitions") or spec.get("components", {}).get("schemas", {})
        _schema_cache = {
            name: {col: (p.get("format") or p.get("type")) for col, p in d.get("properties", {}).items()}
            for name, d in defs.items()
        }
    return _schema_cache


@tool("coaching_query",
      "Lit des lignes d'une table du dashboard coach (lecture seule). Utilise la syntaxe de filtre "
      "PostgREST : filters = {'colonne': 'eq.valeur'}, opérateurs eq, neq, gt, gte, lt, lte, like, "
      "ilike (ex. 'ilike.*dupont*'), is (ex. 'is.null'), in (ex. 'in.(a,b)'). "
      "select permet les jointures (ex. '*,athletes(name)'). Dates au format AAAA-MM-JJ.",
      {"table": {"type": "string"},
       "select": {"type": "string", "description": "Colonnes, défaut '*'"},
       "filters": {"type": "object", "additionalProperties": {"type": "string"}},
       "order": {"type": "string", "description": "ex. 'created_at.desc'"},
       "limit": {"type": "integer", "description": "défaut 50, max 500"},
       "count_only": {"type": "boolean", "description": "Renvoie seulement le nombre de lignes"}},
      ["table"], enabled=_enabled)
async def coaching_query(ctx, table: str, select: str = "*", filters: dict | None = None,
                         order: str | None = None, limit: int = 50, count_only: bool = False):
    params = {"select": select}
    params.update(filters or {})
    if order:
        params["order"] = order
    if count_only:
        r = await _get(table, {**params, "limit": 1}, {"Prefer": "count=exact"})
        return {"count": r.headers.get("content-range", "").split("/")[-1]}
    params["limit"] = max(1, min(int(limit), 500))
    rows = (await _get(table, params)).json()
    return {"rows": rows, "n": len(rows)}


# --- Vues métier Ben&Fit ---------------------------------------------------------
# Structure connue (repo Bene72/Ben-Fit) : profiles (role client/coach, archived,
# engagement_start/end), workouts (is_archived, is_future), workout_logs (logged_at),
# workout_sessions (date, completed), bilans (week_start lundi, created_at, archived),
# cycles / vue cycle_alerts (days_remaining), coach_tasks (title, due_date, done),
# messages (sender_id, receiver_id, read), measures, goals, nutrition_plans.
import asyncio  # noqa: E402
import datetime as dt  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402


async def _rows(table: str, params: list[tuple]) -> list[dict]:
    try:
        return (await _get(table, params)).json()
    except Exception as e:  # table/colonne absente : on continue sans
        return [{"_erreur": f"{table} : {str(e)[:200]}"}]


def _ok(rows):
    return [r for r in rows if "_erreur" not in r]


def _errs(*groups):
    return [r["_erreur"] for g in groups for r in g if "_erreur" in r]


def _today():
    return dt.datetime.now(ZoneInfo(config.TIMEZONE)).date()


async def overview() -> dict:
    today = _today()
    d7, d28 = (today - dt.timedelta(days=7)).isoformat(), (today - dt.timedelta(days=28)).isoformat()
    # bilan attendu au moins pour la semaine dernière (celui de la semaine en cours peut arriver)
    last_monday = (today - dt.timedelta(days=today.weekday() + 7)).isoformat()
    clients, alerts, logs, sessions, bilans, msgs, tasks = await asyncio.gather(
        _rows("profiles", [("select", "*"), ("role", "eq.client"), ("archived", "not.is.true")]),
        _rows("cycle_alerts", [("select", "*")]),
        _rows("workout_logs", [("select", "client_id,logged_at"), ("logged_at", f"gte.{d28}"), ("limit", "5000")]),
        _rows("workout_sessions", [("select", "client_id,date,completed"), ("date", f"gte.{d28}"), ("limit", "5000")]),
        _rows("bilans", [("select", "client_id,week_start,created_at"), ("order", "created_at.desc"), ("limit", "2000")]),
        _rows("messages", [("select", "sender_id,created_at"), ("read", "eq.false"), ("limit", "2000")]),
        _rows("coach_tasks", [("select", "*"), ("done", "eq.false"), ("order", "due_date.asc"), ("limit", "300")]),
    )
    ids = {c["id"]: c.get("full_name") or c.get("email") or c["id"][:8] for c in _ok(clients)}

    days_trained: dict[str, set] = {}
    for r in _ok(logs):
        if r.get("logged_at"):
            days_trained.setdefault(r["client_id"], set()).add(r["logged_at"][:10])
    for r in _ok(sessions):
        if r.get("completed") is not False and r.get("date"):
            days_trained.setdefault(r["client_id"], set()).add(r["date"][:10])
    last_bilan = {}
    for b in _ok(bilans):
        last_bilan.setdefault(b["client_id"], b)
    unread = {}
    for m in _ok(msgs):
        if m.get("sender_id") in ids:
            unread[m["sender_id"]] = unread.get(m["sender_id"], 0) + 1
    cycle_by_client = {a.get("client_id"): a for a in _ok(alerts)}

    athletes, attention = [], []
    for cid, name in sorted(ids.items(), key=lambda x: x[1].lower()):
        c = next(x for x in _ok(clients) if x["id"] == cid)
        days = sorted(days_trained.get(cid, []))
        a = {"nom": name, "programme": c.get("current_program"),
             "seances_7j": len([d for d in days if d >= d7]), "seances_28j": len(days),
             "derniere_seance": days[-1] if days else None,
             "dernier_bilan": (last_bilan.get(cid) or {}).get("week_start"),
             "messages_non_lus": unread.get(cid, 0)}
        if c.get("engagement_end"):
            a["fin_engagement"] = c["engagement_end"]
            left = (dt.date.fromisoformat(c["engagement_end"][:10]) - today).days
            a["jours_avant_fin_engagement"] = left
            if left <= 14:
                attention.append(f"{name} : engagement {'terminé' if left < 0 else f'finit dans {left} j'} (renouvellement)")
        cyc = cycle_by_client.get(cid)
        if cyc and cyc.get("days_remaining") is not None:
            a["cycle_jours_restants"] = cyc["days_remaining"]
            if cyc["days_remaining"] <= 14:
                attention.append(f"{name} : cycle « {cyc.get('cycle_name') or ''} » finit dans {cyc['days_remaining']} j, prog à préparer")
        if not days or days[-1] < d7:
            attention.append(f"{name} : aucune séance enregistrée depuis 7 jours" + (f" (dernière {days[-1]})" if days else ""))
        if not a["dernier_bilan"] or a["dernier_bilan"][:10] < last_monday:
            attention.append(f"{name} : bilan manquant (dernier : {a['dernier_bilan'] or 'aucun'})")
        if a["messages_non_lus"]:
            attention.append(f"{name} : {a['messages_non_lus']} message(s) non lu(s)")
        athletes.append(a)

    t_out = []
    for t in _ok(tasks):
        due = t.get("due_date")
        t_out.append({"tache": t.get("title"), "athlete": ids.get(t.get("client_id")), "echeance": due,
                      "en_retard": bool(due and due[:10] < today.isoformat())})
    return {"date": today.isoformat(), "nb_athletes_actifs": len(ids), "points_attention": attention,
            "taches_coach_ouvertes": t_out, "athletes": athletes,
            "donnees_indisponibles": _errs(clients, alerts, logs, sessions, bilans, msgs, tasks)}


@tool("coaching_overview",
      "Cockpit coach Ben&Fit : pour chaque athlète actif, séances des 7/28 derniers jours, dernier bilan, "
      "fin d'engagement, jours restants du cycle, messages non lus ; plus la liste des points d'attention "
      "et des tâches coach ouvertes. À utiliser pour « qu'est-ce que j'ai à faire côté clients ».",
      enabled=_enabled)
async def coaching_overview(ctx):
    return await overview()


@tool("coaching_athlete",
      "Fiche complète d'un athlète : profil, derniers bilans (en entier), programme en cours avec exercices, "
      "derniers logs d'entraînement, mesures, objectifs, nutrition, tâches et derniers messages.",
      {"name": {"type": "string", "description": "Nom ou partie du nom de l'athlète"}},
      ["name"], enabled=_enabled)
async def coaching_athlete(ctx, name: str):
    found = _ok(await _rows("profiles", [("select", "*"), ("role", "eq.client"),
                                         ("full_name", f"ilike.*{name.strip()}*")]))
    if not found:
        return f"Aucun athlète trouvé pour « {name} »."
    if len(found) > 1:
        return {"plusieurs_resultats": [f.get("full_name") for f in found]}
    p = found[0]
    cid = p["id"]
    q = lambda *extra: [("select", "*"), ("client_id", f"eq.{cid}"), *extra]  # noqa: E731
    bilans, workouts, logs, measures, goals, nutri, tasks, msgs = await asyncio.gather(
        _rows("bilans", q(("order", "created_at.desc"), ("limit", "4"))),
        _rows("workouts", [("select", "*,exercises(*)"), ("client_id", f"eq.{cid}"),
                           ("is_archived", "not.is.true")]),
        _rows("workout_logs", q(("order", "logged_at.desc"), ("limit", "40"))),
        _rows("measures", q(("order", "date.desc"), ("limit", "6"))),
        _rows("goals", q()),
        _rows("nutrition_plans", q(("active", "eq.true"))),
        _rows("coach_tasks", q(("done", "eq.false"))),
        _rows("messages", [("select", "sender_id,content,created_at,read"),
                           ("or", f"(sender_id.eq.{cid},receiver_id.eq.{cid})"),
                           ("order", "created_at.desc"), ("limit", "10")]),
    )
    for m in _ok(msgs):
        m["de"] = "athlète" if m.pop("sender_id", None) == cid else "coach"
    return {"profil": {k: v for k, v in p.items() if k not in ("email",)},
            "bilans_recents": bilans, "programme_en_cours": workouts, "logs_recents": logs,
            "mesures": measures, "objectifs": goals, "nutrition": nutri,
            "taches_ouvertes": tasks, "messages_recents": msgs}
