"""Coaching : lecture des données du dashboard Ben&Fit (Supabase), en LECTURE SEULE.

Aucune fonction ici n'écrit ni ne supprime de données : les données clients
restent intactes quoi que l'agent fasse.
"""
import re

import httpx

from .. import config
from . import tool

_enabled = lambda: bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY)  # noqa: E731
_schema_cache: dict | None = None


def _headers():
    k = config.SUPABASE_SERVICE_KEY
    return {"apikey": k, "Authorization": f"Bearer {k}"}


_TABLE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


async def _get(path: str, params=None, extra_headers=None):  # params : dict ou liste de tuples
    if path and not _TABLE.match(path):  # empêche de sortir de /rest/v1/ (ex. ../auth/v1/admin)
        raise ValueError(f"nom de table invalide : {path!r}")
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
    ctx["tainted"] = ctx["client_data"] = True  # données clients lues : plus de sortie web ni de voix externe
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
    ctx["tainted"] = ctx["client_data"] = True  # données clients lues : plus de sortie web ni de voix externe
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
    ctx["tainted"] = ctx["client_data"] = True  # données clients lues : plus de sortie web ni de voix externe
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
    ctx["tainted"] = ctx["client_data"] = True  # données clients lues : plus de sortie web ni de voix externe
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


# --- Programmation : écriture de cycles en BROUILLON (is_future) -----------------------
# Seule écriture autorisée de tout l'agent sur la base : créer des séances « futures »
# (invisibles pour l'athlète tant que Bene n'a pas cliqué sur « Activer » dans l'app),
# et supprimer celles que l'agent vient lui-même de créer. Jamais de modification.
import json  # noqa: E402
from pathlib import Path  # noqa: E402

from .. import confirm, storage  # noqa: E402

_WRITE_TABLES = {"workouts", "exercises"}
GROUP_TYPES = {"Normal", "Superset", "Giant Set", "Drop Set"}
JOURS = ["", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
GUIDE = Path(__file__).resolve().parent.parent / "prompts" / "programmation.md"


async def _write(method: str, table: str, params=None, payload=None):
    if table not in _WRITE_TABLES or method not in ("POST", "DELETE"):
        raise PermissionError(f"écriture interdite : {method} {table}")
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.request(method, f"{config.SUPABASE_URL}/rest/v1/{table}", params=params, json=payload,
                            headers={**_headers(), "Prefer": "return=representation"})
    if r.status_code >= 400:
        raise RuntimeError(f"Supabase {r.status_code} : {r.text[:400]}")
    return r.json() if r.content else []


def _txt(v, n):
    return None if v in (None, "") else str(v).strip()[:n]


BLOCK_FORMATS = ["For Time", "AMRAP", "EMOM", "Tabata", "RFT", "Death By"]
WORKOUT_TYPES = ["Push", "Pull", "Legs", "Full Body", "Upper", "Lower", "Core", "Cardio", "WOD", "Autre"]


def _clean_cycle(workouts: list) -> list[dict]:
    """Valide le cycle et le convertit au format exact de l'app (lignes de la table exercises)."""
    if not isinstance(workouts, list) or not 1 <= len(workouts) <= 14:
        raise ValueError("un cycle contient entre 1 et 14 séances")
    out = []
    for w in workouts:
        day = w.get("day_of_week")
        day = int(day) if day not in (None, "", 0) else None
        if day is not None and not 1 <= day <= 7:
            raise ValueError(f"day_of_week : 1 (lundi) à 7 (dimanche), ou vide : séance « {w.get('name')} »")
        if not _txt(w.get("name"), 120):
            raise ValueError("chaque séance doit avoir un nom")
        items = w.get("exercises") or []
        if not items:
            raise ValueError(f"séance « {w['name']} » : aucun exercice")
        rows, display, nblock = [], [], 0
        for e in items:
            blk = e.get("block")
            if blk:  # WOD / EMOM / AMRAP… : un « Workout Block » de l'app
                fmt = blk.get("format") or "For Time"
                if fmt not in BLOCK_FORMATS:
                    raise ValueError(f"format de bloc inconnu : {fmt} (autorisés : {', '.join(BLOCK_FORMATS)})")
                moves = [_txt(m, 120) for m in (blk.get("movements") or []) if _txt(m, 120)]
                if not 1 <= len(moves) <= 12:
                    raise ValueError(f"bloc {fmt} de « {w['name']} » : entre 1 et 12 mouvements")
                rounds = blk.get("rounds")
                rounds = int(rounds) if rounds not in (None, "") else None
                if rounds is not None and not 1 <= rounds <= 60:
                    raise ValueError(f"bloc {fmt} : nombre de rounds invalide")
                rest = _txt(blk.get("rest"), 40) or ""
                meta = {"type": fmt, "rounds": "" if rounds is None else str(rounds),
                        "cap": _txt(blk.get("cap"), 20) or "", "rest": rest,
                        "objective": _txt(blk.get("objective"), 300) or "",
                        "coachNote": _txt(blk.get("coach_note"), 800) or "", "uiVersion": 2}
                nblock += 1
                for i, m in enumerate(moves):
                    rows.append({"name": m, "sets": rounds or 1, "reps": "", "target_weight": "",
                                 "rest": rest if i == len(moves) - 1 else "0s",
                                 "note": json.dumps(meta, ensure_ascii=False) if i == 0 else "",
                                 "group_type": "Workout Block", "group_id": f"b{nblock}"})
                display.append({"block": meta, "movements": moves})
                continue
            if not _txt(e.get("name"), 120):
                raise ValueError(f"séance « {w['name']} » : exercice sans nom")
            sets = e.get("sets")
            sets = int(sets) if sets not in (None, "") else None
            if sets is not None and not 1 <= sets <= 20:
                raise ValueError(f"« {e['name']} » : nombre de séries invalide")
            gt = e.get("group_type") or "Normal"
            if gt not in GROUP_TYPES:
                raise ValueError(f"group_type inconnu : {gt} (autorisés : {', '.join(sorted(GROUP_TYPES))} ; "
                                 "pour un WOD/EMOM/AMRAP utilise un 'block')")
            row = {"name": _txt(e["name"], 120), "sets": sets, "reps": _txt(e.get("reps"), 60),
                   "target_weight": _txt(e.get("target_weight"), 60), "rest": _txt(e.get("rest"), 40),
                   "note": _txt(e.get("note"), 600), "group_type": gt,
                   "group_id": _txt(e.get("group_id"), 20) if gt != "Normal" else None}
            rows.append(row)
            display.append(row)
        if len(rows) > 45:
            raise ValueError(f"séance « {w['name']} » : trop de lignes ({len(rows)}), simplifie")
        for i, r in enumerate(rows):
            r["order_index"] = i
        dur = w.get("duration_min")
        out.append({"name": _txt(w["name"], 120), "type": _txt(w.get("type"), 40), "day_of_week": day,
                    "duration_min": int(dur) if dur else None, "notes": _txt(w.get("notes"), 4000),
                    "exercises": rows, "display": display})
    return out


def _cycle_summary(athlete: str, cycle_name: str, cycle: list[dict], existing_future: int) -> str:
    lines = [f"Créer le cycle « {cycle_name} » pour {athlete}",
             "En BROUILLON (cycle futur) : invisible pour l'athlète tant que tu n'as pas cliqué sur "
             "« Activer » dans l'onglet Programme de l'app."]
    if existing_future:
        lines.append(f"⚠️ {athlete} a déjà {existing_future} séance(s) dans son cycle futur : celles-ci s'y ajouteront.")
    for n, w in enumerate(cycle, 1):
        label = JOURS[w["day_of_week"]] if w["day_of_week"] else f"Séance {n}"
        head = f"\n{w['name']}" if w["name"].lower().startswith("séance") and not w["day_of_week"] else f"\n{label} · {w['name']}"
        if w["type"]:
            head += f" [{w['type']}]"
        if w["duration_min"]:
            head += f" ({w['duration_min']} min)"
        lines.append(head)
        if w["notes"]:
            lines.append("  " + w["notes"].replace("\n", "\n  "))
        for i, e in enumerate(w["display"], 1):
            if "block" in e:
                m = e["block"]
                bits = [f"BLOC {m['type']}"]
                if m["rounds"]:
                    bits.append(f"{m['rounds']} rounds")
                if m["cap"]:
                    bits.append(f"{m['cap']} min")
                if m["rest"]:
                    bits.append(f"repos {m['rest']}")
                lines.append(f"  {i}. " + " · ".join(bits))
                lines += [f"       - {mv}" for mv in e["movements"]]
                if m["objective"]:
                    lines.append(f"     Objectif : {m['objective']}")
                if m["coachNote"]:
                    lines.append(f"     {m['coachNote']}")
                continue
            bits = [e["name"]]
            if e["sets"] or e["reps"]:
                bits.append(f"{e['sets'] or '?'} x {e['reps'] or '?'}")
            if e["target_weight"]:
                bits.append(f"@ {e['target_weight']}")
            if e["rest"]:
                bits.append(f"repos {e['rest']}")
            tag = ""
            if e["group_type"] != "Normal":
                tag = f" [{e['group_type']}{' ' + e['group_id'] if e['group_id'] else ''}]"
            lines.append(f"  {i}. " + " · ".join(bits) + tag)
            if e["note"]:
                lines.append(f"     {e['note']}")
    return "\n".join(lines)


async def _create_cycle(client_id: str, athlete: str, cycle_name: str, cycle: list[dict]) -> str:
    created: list[str] = []
    try:
        for order, w in enumerate(cycle):
            row = {"client_id": client_id, "name": w["name"], "type": w["type"], "day_of_week": w["day_of_week"],
                   "duration_min": w["duration_min"], "notes": w["notes"], "cycle_name": cycle_name,
                   "is_future": True, "order_index": order}
            new = (await _write("POST", "workouts", payload=row))[0]
            created.append(new["id"])
            tag = new["id"][:8]
            exs = [{**e, "workout_id": new["id"],
                    "group_id": (f"{'wb' if e['group_type'] == 'Workout Block' else 'ag'}_{tag}_{e['group_id']}"
                                 if e["group_id"] else None)} for e in w["exercises"]]
            await _write("POST", "exercises", payload=exs)
    except Exception as e:
        if created:  # on ne laisse pas un cycle à moitié créé
            await _delete_draft(created)
        raise RuntimeError(f"création annulée, rien n'a été laissé dans l'app ({e})")
    storage.set_meta("last_cycle", json.dumps({"athlete": athlete, "cycle": cycle_name, "ids": created}))
    return (f"✅ Cycle « {cycle_name} » créé pour {athlete} : {len(created)} séances en brouillon.\n"
            "Retrouve-le dans l'app : fiche de l'athlète, onglet Programme, « Cycle futur ». "
            "Relis, ajuste, puis clique sur « Activer » quand tu veux.\n"
            "Pour le retirer : dis-moi « annule le dernier cycle ».")


async def _delete_draft(ids: list[str]) -> int:
    """Supprime uniquement des séances encore en brouillon (is_future = true)."""
    still = _ok(await _rows("workouts", [("select", "id"), ("id", f"in.({','.join(ids)})"), ("is_future", "eq.true")]))
    keep = [w["id"] for w in still]
    if not keep:
        return 0
    lst = f"in.({','.join(keep)})"
    await _write("DELETE", "exercises", params=[("workout_id", lst)])
    await _write("DELETE", "workouts", params=[("id", lst), ("is_future", "eq.true")])
    return len(keep)


@tool("coaching_programming_guide",
      "Renvoie la doctrine complète de programmation de Bene (Great Performance Trainer). "
      "À relire OBLIGATOIREMENT avant de construire ou de critiquer un cycle ou une séance.",
      enabled=_enabled)
async def coaching_programming_guide(ctx):
    try:
        return GUIDE.read_text(encoding="utf-8")
    except OSError:
        return "Doctrine absente (agent/prompts/programmation.md). Applique les principes de la posture coach."


_EX = {"type": "object", "description": "Soit un exercice classique (name, sets, reps…), soit un bloc {block: …}",
       "properties": {
    "name": {"type": "string"}, "sets": {"type": "integer"},
    "reps": {"type": "string", "description": "ex. '5', '8-10', '3/côté', '20 s', '10 m'"},
    "target_weight": {"type": "string", "description": "ex. '80 kg', '82-85 %', 'RPE 8', 'RIR 2'"},
    "rest": {"type": "string", "description": "ex. '120s', '60-90s', '2 min 30'"},
    "note": {"type": "string", "description": "tempo, intention technique, critère d'arrêt"},
    "group_type": {"type": "string", "enum": sorted(GROUP_TYPES)},
    "group_id": {"type": "string", "description": "même lettre (A, B…) pour les exercices enchaînés d'un même superset / giant set"},
    "block": {"type": "object", "required": ["format", "movements"],
              "description": "Bloc conditioning affiché comme « Workout Block » dans l'app (score et chrono côté athlète)",
              "properties": {
                  "format": {"type": "string", "enum": BLOCK_FORMATS,
                             "description": "For Time / RFT (rounds for time) : au chrono. AMRAP : max de tours dans le temps 'cap'. "
                                            "EMOM : une tâche par minute pendant 'cap' minutes. Tabata : 20 s / 10 s. Death By : +1 rep par minute."},
                  "rounds": {"type": "integer", "description": "nombre de tours (For Time, RFT) ; vide pour AMRAP"},
                  "cap": {"type": "string", "description": "durée ou time cap en minutes, ex. '12'"},
                  "rest": {"type": "string", "description": "repos entre les tours ou après le bloc, ex. '90s'"},
                  "objective": {"type": "string", "description": "stimulus visé, ex. 'vitesse constante sur les 3 rounds'"},
                  "coach_note": {"type": "string"},
                  "movements": {"type": "array", "items": {"type": "string"},
                                "description": "une ligne par mouvement, quantité incluse : '8 DB thrusters', '15 cal row', '20 s battle rope'"}}}}}


@tool("coaching_propose_cycle",
      "Propose la création d'un cycle de programmation pour un athlète, en BROUILLON (cycle futur, invisible "
      "pour l'athlète). Rien n'est écrit tant que Bene n'a pas validé par /ok le récapitulatif qui lui est "
      "envoyé automatiquement. Une entrée par séance, dans l'ordre du cycle. Choisis la bonne structure : "
      "exercice classique pour la force, la puissance, la technique ; Superset / Giant Set (même group_id) "
      "pour des exercices enchaînés avec repos après le groupe ; 'block' pour tout conditioning : "
      "For Time, RFT, AMRAP, EMOM, Tabata, Death By, et aussi les circuits d'activation ou finishers enchaînés. "
      "Ne mets jamais un WOD dans une simple note. 'notes' de la séance : durée, priorité, intention, "
      "échauffement. Mets la progression semaine par semaine et les indicateurs de suivi dans les notes "
      "de la dernière séance, comme le fait Bene.",
      {"name": {"type": "string", "description": "Nom ou partie du nom de l'athlète"},
       "cycle_name": {"type": "string", "description": "ex. 'Judo — Force, Puissance & Endurance spécifique'"},
       "workouts": {"type": "array", "items": {"type": "object", "required": ["name", "exercises"],
                    "properties": {"name": {"type": "string", "description": "ex. 'Séance 1 — Force maximale + puissance latérale'"},
                                   "type": {"type": "string", "enum": WORKOUT_TYPES},
                                   "day_of_week": {"type": "integer", "description": "1 = lundi … 7 = dimanche. Laisse vide si les séances sont numérotées sans jour fixe."},
                                   "duration_min": {"type": "integer"},
                                   "notes": {"type": "string"},
                                   "exercises": {"type": "array", "items": _EX}}}}},
      ["name", "cycle_name", "workouts"], enabled=_enabled)
async def coaching_propose_cycle(ctx, name: str, cycle_name: str, workouts: list):
    ctx["tainted"] = ctx["client_data"] = True
    found = _ok(await _rows("profiles", [("select", "id,full_name,archived"), ("role", "eq.client"),
                                         ("full_name", f"ilike.*{name.strip()}*")]))
    if not found:
        return f"Aucun athlète trouvé pour « {name} »."
    if len(found) > 1:
        return {"plusieurs_resultats": [f.get("full_name") for f in found]}
    p = found[0]
    cycle = _clean_cycle(workouts)
    cname = _txt(cycle_name, 80) or "Nouveau cycle"
    existing = _ok(await _rows("workouts", [("select", "id"), ("client_id", f"eq.{p['id']}"), ("is_future", "eq.true")]))
    summary = _cycle_summary(p["full_name"], cname, cycle, len(existing))
    return confirm.request(ctx["chat_id"], summary, lambda: _create_cycle(p["id"], p["full_name"], cname, cycle))


@tool("coaching_cancel_last_cycle",
      "Retire le dernier cycle brouillon créé par l'agent (uniquement s'il n'a pas encore été activé). "
      "Demande la confirmation /ok de Bene.", enabled=_enabled)
async def coaching_cancel_last_cycle(ctx):
    raw = storage.get_meta("last_cycle")
    if not raw or raw == "":
        return "Je n'ai créé aucun cycle récemment."
    last = json.loads(raw)

    async def do():
        n = await _delete_draft(last["ids"])
        storage.set_meta("last_cycle", "")
        if n == 0:
            return "Rien retiré : ce cycle a déjà été activé ou supprimé dans l'app. Je n'y touche pas."
        return f"Cycle « {last['cycle']} » de {last['athlete']} retiré ({n} séances en brouillon supprimées)."

    return confirm.request(ctx["chat_id"], f"Supprimer le brouillon « {last['cycle']} » de {last['athlete']} "
                           f"({len(last['ids'])} séances créées par l'agent, si elles sont encore en brouillon)", do)
