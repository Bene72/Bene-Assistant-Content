"""BoxLog (app de la salle) : lecture seule de la programmation.

But : savoir ce qui a été programmé (WODs du jour + programmes) pour éviter les doublons
et mieux programmer la suite. Aucune écriture : ce fichier ne fait que des requêtes GET.
"""
import asyncio
import datetime as dt
import re
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from .. import config
from . import tool

_enabled = lambda: bool(config.BOX_SUPABASE_URL and config.BOX_SUPABASE_KEY)  # noqa: E731
_TABLE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
GUIDE = Path(__file__).resolve().parent.parent / "prompts" / "programmation.md"
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


async def _get(table: str, params: list[tuple]) -> list[dict]:
    if not _TABLE.match(table):
        raise ValueError(f"nom de table invalide : {table!r}")
    k = config.BOX_SUPABASE_KEY
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{config.BOX_SUPABASE_URL}/rest/v1/{table}", params=params,
                        headers={"apikey": k, "Authorization": f"Bearer {k}"})
    if r.status_code >= 400:
        raise RuntimeError(f"BoxLog {r.status_code} : {r.text[:300]}")
    return r.json()


def _today() -> dt.date:
    return dt.datetime.now(ZoneInfo(config.TIMEZONE)).date()


def _box(params: list[tuple]) -> list[tuple]:
    return params + ([("box_id", f"eq.{config.BOX_ID}")] if config.BOX_ID else [])


def _chunks(ids: list[str], n: int = 60):
    for i in range(0, len(ids), n):
        yield ids[i:i + n]


def _day(d: str | None) -> str:
    if not d:
        return "?"
    x = dt.date.fromisoformat(d[:10])
    return f"{JOURS[x.weekday()]} {x:%d/%m}"


def _wod(w: dict) -> dict:
    out = {"date": w["wod_date"], "jour": _day(w["wod_date"]), "titre": w["title"], "format": w["format"],
           "contenu": w["description"]}
    if w.get("time_cap_sec"):
        out["time_cap_min"] = round(w["time_cap_sec"] / 60, 1)
    if w.get("emom_rounds"):
        out["emom"] = f"{w['emom_rounds']} x {w.get('emom_interval_sec') or 60}s"
    if w.get("is_benchmark"):
        out["benchmark"] = True
    return out


def _block(b: dict) -> dict:
    out = {"type": b.get("block_type"), "titre": b.get("title")}
    for src, dst in (("prescription", "prescription"), ("notes", "notes"), ("percent_1rm", "pourcent_1rm")):
        if b.get(src) not in (None, ""):
            out[dst] = b[src]
    if b.get("is_optional"):
        out["optionnel"] = True
    return out


async def _programs(scope: str, name: str | None) -> list[dict]:
    params = _box([("select", "id,name,start_date,status,is_shared,athlete_id"),
                   ("status", "in.(active,completed)"), ("order", "start_date.desc"), ("limit", "200")])
    if scope != "tout":
        params.append(("is_shared", "eq.true"))
    progs = await _get("programs", params)
    if name:
        progs = [p for p in progs if name.strip().lower() in (p.get("name") or "").lower()]
    return progs


async def _sessions_with_blocks(prog_ids: list[str], start: dt.date, end: dt.date) -> list[dict]:
    sessions = []
    for ch in _chunks(prog_ids):
        sessions += await _get("program_sessions_expanded", [
            ("select", "session_id,program_id,week_number,day_offset,period,session_date"),
            ("program_id", f"in.({','.join(ch)})"),
            ("session_date", f"gte.{start}"), ("session_date", f"lte.{end}"), ("order", "session_date.asc")])
    blocks: dict[str, list] = {}
    for ch in _chunks([s["session_id"] for s in sessions]):
        for b in await _get("program_blocks", [("select", "*"), ("program_session_id", f"in.({','.join(ch)})"),
                                               ("order", "position.asc")]):
            blocks.setdefault(b["program_session_id"], []).append(_block(b))
    for s in sessions:
        s["blocs"] = blocks.get(s["session_id"], [])
    return sessions


@tool("box_programs",
      "BoxLog : liste des programmes de la salle (nom, date de début, statut, partagé à la salle ou "
      "individuel). scope='salle' = programmes partagés (défaut), 'tout' = aussi les individuels.",
      {"scope": {"type": "string", "enum": ["salle", "tout"]}}, enabled=_enabled)
async def box_programs(ctx, scope: str = "salle"):
    ctx["tainted"] = True
    progs = await _programs(scope, None)
    return [{"programme": p["name"], "debut": p["start_date"], "statut": p["status"],
             "partage_salle": p["is_shared"]} for p in progs] or "Aucun programme trouvé."


@tool("box_programming",
      "BoxLog : tout ce qui a été programmé à la salle sur une période, dans l'ordre chronologique : "
      "les WODs du jour publiés et les séances des programmes (blocs : échauffement, exercice, superset, "
      "EMOM, AMRAP, for time, finisher…). Sert à savoir ce qui a été fait avant de programmer la suite. "
      "Par défaut : les 21 derniers jours, programmes partagés à la salle.",
      {"start": {"type": "string", "description": "Début AAAA-MM-JJ (défaut : il y a 21 jours)"},
       "days": {"type": "integer", "description": "Nombre de jours couverts (défaut 21, max 120). "
                                                  "Peut dépasser aujourd'hui pour voir ce qui est déjà prévu."},
       "program": {"type": "string", "description": "Filtre : partie du nom d'un programme (optionnel)"},
       "scope": {"type": "string", "enum": ["salle", "tout"]}}, enabled=_enabled)
async def box_programming(ctx, start: str | None = None, days: int = 21, program: str | None = None,
                          scope: str = "salle"):
    ctx["tainted"] = True
    days = max(1, min(int(days), 120))
    s = dt.date.fromisoformat(start) if start else _today() - dt.timedelta(days=days - 1)
    e = s + dt.timedelta(days=days - 1)
    wods, progs = await asyncio.gather(
        _get("wods", _box([("select", "*"), ("status", "eq.published"), ("wod_date", f"gte.{s}"),
                           ("wod_date", f"lte.{e}"), ("order", "wod_date.asc"), ("limit", "400")])),
        _programs(scope, program))
    names = {p["id"]: p["name"] for p in progs}
    sessions = await _sessions_with_blocks(list(names), s, e) if names else []
    seances = [{"date": x["session_date"], "jour": _day(x["session_date"]), "programme": names.get(x["program_id"]),
                "semaine": x["week_number"], "moment": x["period"], "blocs": x["blocs"]} for x in sessions]
    return {"periode": f"du {s:%d/%m/%Y} au {e:%d/%m/%Y}", "aujourdhui": _today().isoformat(),
            "wods_du_jour": [] if program else [_wod(w) for w in wods],
            "seances_programmes": seances,
            "programmes_inclus": sorted(set(names.values()))}


@tool("box_search_movement",
      "BoxLog : cherche un mouvement ou un mot (ex. 'thruster', 'snatch', 'row', 'Fran') dans tout ce qui a été "
      "programmé à la salle sur les dernières semaines : dates, contexte et nombre d'apparitions. "
      "Sert à éviter les doublons et à voir depuis quand un mouvement n'a pas été travaillé.",
      {"query": {"type": "string"},
       "weeks": {"type": "integer", "description": "Profondeur en semaines (défaut 8, max 52)"},
       "scope": {"type": "string", "enum": ["salle", "tout"]}}, ["query"], enabled=_enabled)
async def box_search_movement(ctx, query: str, weeks: int = 8, scope: str = "salle"):
    ctx["tainted"] = True
    q = re.sub(r"[^\w\s'+-]", " ", query, flags=re.UNICODE).strip()[:40]
    if len(q) < 2:
        raise ValueError("mot recherché trop court")
    weeks = max(1, min(int(weeks), 52))
    s, e = _today() - dt.timedelta(weeks=weeks), _today() + dt.timedelta(days=28)
    wods, progs = await asyncio.gather(
        _get("wods", _box([("select", "wod_date,title,format,description"), ("status", "eq.published"),
                           ("wod_date", f"gte.{s}"), ("or", f"(title.ilike.*{q}*,description.ilike.*{q}*)"),
                           ("order", "wod_date.desc"), ("limit", "200")])),
        _programs(scope, None))
    names = {p["id"]: p["name"] for p in progs}
    hits = [{"date": w["wod_date"], "jour": _day(w["wod_date"]), "source": "WOD du jour", "titre": w["title"],
             "contexte": w["description"][:400]} for w in wods]
    for x in (await _sessions_with_blocks(list(names), s, e) if names else []):
        for b in x["blocs"]:
            if q.lower() in " ".join(str(v) for v in b.values()).lower():
                hits.append({"date": x["session_date"], "jour": _day(x["session_date"]),
                             "source": names.get(x["program_id"]), "titre": b.get("titre"),
                             "contexte": " · ".join(str(b[k]) for k in ("type", "prescription", "notes") if b.get(k))[:400]})
    hits.sort(key=lambda h: h["date"] or "", reverse=True)
    past = [h for h in hits if (h["date"] or "") <= _today().isoformat()]
    return {"mot": q, "periode": f"{weeks} dernières semaines (+ 4 semaines déjà prévues)",
            "apparitions": len(hits),
            "derniere_fois": past[0]["date"] if past else None,
            "jours_depuis": (_today() - dt.date.fromisoformat(past[0]["date"])).days if past else None,
            "detail": hits[:60]}


@tool("box_programming_guide",
      "Doctrine de programmation de Bene (Great Performance Trainer). À relire avant de proposer "
      "ou de critiquer une programmation pour la salle.", enabled=_enabled)
async def box_programming_guide(ctx):
    try:
        return GUIDE.read_text(encoding="utf-8")
    except OSError:
        return "Doctrine absente (agent/prompts/programmation.md)."
