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


# --- Bilans hebdo -------------------------------------------------------------------
BILAN_FIELDS = ["sommeil", "moral", "assiduite_diete", "assiduite_training", "neat"]


def _filled(b: dict) -> bool:
    """Un bilan est « fait » si l'athlète a rempli au moins un score ou une note."""
    keys = [f"{f}_score" for f in BILAN_FIELDS] + [f"{f}_note" for f in BILAN_FIELDS] + \
        ["autre_note", "problemes_diete_note", "problemes_training_note"]
    return any(b.get(k) not in (None, "") for k in keys)


def _local(ts: str | None):
    if not ts:
        return None
    d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(ZoneInfo(config.TIMEZONE))


def _bilan_time(b: dict):
    """Moment où le bilan a été rempli : updated_at si dispo, sinon created_at."""
    return _local(b.get("updated_at")) or _local(b.get("created_at"))


def bilan_window(today: dt.date) -> tuple[dt.date, dt.date]:
    """Fenêtre vendredi -> lundi la plus récente (en cours si on est entre vendredi et lundi)."""
    friday = today - dt.timedelta(days=(today.weekday() - 4) % 7)
    return friday, friday + dt.timedelta(days=3)


def _scores(b: dict) -> dict:
    return {f: b.get(f"{f}_score") for f in BILAN_FIELDS if b.get(f"{f}_score") is not None}


@tool("coaching_bilans_weekend",
      "Qui a fait son bilan hebdo entre vendredi et lundi (fenêtre la plus récente, ou celle "
      "commençant au vendredi indiqué). Donne pour chaque athlète actif : fait / pas fait, quand, "
      "scores, et les notes importantes.",
      {"friday": {"type": "string", "description": "Vendredi de début AAAA-MM-JJ (optionnel)"}},
      enabled=_enabled)
async def coaching_bilans_weekend(ctx, friday: str | None = None):
    if friday:
        start = dt.date.fromisoformat(friday)
        end = start + dt.timedelta(days=3)
    else:
        start, end = bilan_window(_today())
    since = (start - dt.timedelta(days=7)).isoformat()
    clients, bilans = await asyncio.gather(
        _rows("profiles", [("select", "id,full_name,email"), ("role", "eq.client"), ("archived", "not.is.true")]),
        _rows("bilans", [("select", "*"), ("or", f"(created_at.gte.{since},updated_at.gte.{since})"),
                         ("order", "created_at.desc"), ("limit", "1000")]),
    )
    if not _ok(bilans) and _errs(bilans):  # pas de colonne updated_at : on se rabat sur created_at
        bilans = await _rows("bilans", [("select", "*"), ("created_at", f"gte.{since}"),
                                        ("order", "created_at.desc"), ("limit", "1000")])
    names = {c["id"]: c.get("full_name") or c.get("email") or c["id"][:8] for c in _ok(clients)}
    # sans updated_at, on accepte aussi un bilan rattaché à la semaine du vendredi ou au lundi suivant
    weeks = {(start - dt.timedelta(days=4)).isoformat(), end.isoformat()}
    faits, manquants = [], []
    for cid, name in sorted(names.items(), key=lambda x: x[1].lower()):
        found = None
        for b in _ok(bilans):
            t = _bilan_time(b)
            in_window = t and start <= t.date() <= end
            by_week = "updated_at" not in b and (b.get("week_start") or "")[:10] in weeks
            if b.get("client_id") == cid and _filled(b) and (in_window or by_week):
                found = (b, t if in_window else None)
                break
        if found:
            b, t = found
            notes = {k: b[k] for k in ("problemes_training_note", "problemes_diete_note", "autre_note")
                     if b.get(k)}
            if t:
                jour = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"][t.weekday()]
                quand = f"{jour} {t:%d/%m %H:%M}"
            else:
                quand = f"bilan de la semaine du {b.get('week_start')}"
            faits.append({"athlete": name, "rempli_le": quand,
                          "scores": _scores(b), **notes})
        else:
            manquants.append(name)
    return {"fenetre": f"du vendredi {start:%d/%m} au lundi {end:%d/%m}",
            "en_cours": start <= _today() <= end,
            "bilans_faits": faits, "pas_encore_fait": manquants,
            "donnees_indisponibles": _errs(clients, bilans)}


@tool("coaching_bilan",
      "Bilan hebdo complet d'un athlète (le dernier rempli, ou celui d'une semaine donnée) avec son "
      "contexte : 2 bilans précédents pour la tendance, programme en cours, séances des 14 derniers "
      "jours, mesures récentes, objectifs. À utiliser pour analyser un bilan ou préparer la réponse.",
      {"name": {"type": "string", "description": "Nom ou partie du nom de l'athlète"},
       "week_start": {"type": "string", "description": "Lundi de la semaine AAAA-MM-JJ (optionnel)"}},
      ["name"], enabled=_enabled)
async def coaching_bilan(ctx, name: str, week_start: str | None = None):
    found = _ok(await _rows("profiles", [("select", "*"), ("role", "eq.client"),
                                         ("full_name", f"ilike.*{name.strip()}*")]))
    if not found:
        return f"Aucun athlète trouvé pour « {name} »."
    if len(found) > 1:
        return {"plusieurs_resultats": [f.get("full_name") for f in found]}
    p, cid = found[0], found[0]["id"]
    d14 = (_today() - dt.timedelta(days=14)).isoformat()
    bilans, workouts, logs, measures, goals = await asyncio.gather(
        _rows("bilans", [("select", "*"), ("client_id", f"eq.{cid}"), ("order", "week_start.desc"), ("limit", "8")]),
        _rows("workouts", [("select", "name,day_of_week,notes"), ("client_id", f"eq.{cid}"),
                           ("is_archived", "not.is.true")]),
        _rows("workout_logs", [("select", "*"), ("client_id", f"eq.{cid}"), ("logged_at", f"gte.{d14}"),
                               ("order", "logged_at.desc"), ("limit", "60")]),
        _rows("measures", [("select", "*"), ("client_id", f"eq.{cid}"), ("order", "date.desc"), ("limit", "4")]),
        _rows("goals", [("select", "*"), ("client_id", f"eq.{cid}")]),
    )
    filled = [b for b in _ok(bilans) if _filled(b)]
    if week_start:
        filled = [b for b in filled if (b.get("week_start") or "")[:10] <= week_start] or filled
    if not filled:
        return f"Aucun bilan rempli trouvé pour {p.get('full_name')}."
    clean = lambda b: {k: v for k, v in b.items() if k not in ("id", "client_id", "coach_id") and v not in (None, "")}  # noqa: E731
    seance_days = sorted({(l.get("logged_at") or "")[:10] for l in _ok(logs)} - {""})
    return {
        "athlete": {"nom": p.get("full_name"), "programme": p.get("current_program"),
                    "note_coach": p.get("coach_note"), "debut_engagement": p.get("engagement_start"),
                    "fin_engagement": p.get("engagement_end")},
        "bilan": clean(filled[0]),
        "bilans_precedents_scores": [{"semaine": b.get("week_start"), **_scores(b)} for b in filled[1:3]],
        "programme_en_cours": workouts,
        "jours_entraines_14j": seance_days,
        "logs_14j": _ok(logs)[:30],
        "mesures": measures, "objectifs": goals,
    }
