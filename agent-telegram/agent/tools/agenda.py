"""Agenda (lecture) via les liens iCal secrets : Google Agenda, iCloud, Outlook…

Dans .env : CALENDARS=Perso=https://...ics, Pro=https://...ics
"""
import datetime as dt
from zoneinfo import ZoneInfo

import httpx
import icalendar
import recurring_ical_events

from .. import config
from . import tool

_enabled = lambda: bool(config.CALENDARS)  # noqa: E731


async def _fetch(url: str) -> icalendar.Calendar:
    url = url.replace("webcal://", "https://")
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        r = await c.get(url)
    r.raise_for_status()
    return icalendar.Calendar.from_ical(r.content)


def _fmt(value, tz) -> tuple[str, bool]:
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=tz)
        return value.astimezone(tz).strftime("%Y-%m-%d %H:%M"), False
    return value.isoformat(), True


async def events_between(start: dt.date, end: dt.date) -> list[dict]:
    tz = ZoneInfo(config.TIMEZONE)
    out = []
    for name, url in config.CALENDARS.items():
        try:
            cal = await _fetch(url)
        except Exception as e:
            out.append({"agenda": name, "erreur": f"lecture impossible : {e}"})
            continue
        for ev in recurring_ical_events.of(cal).between(start, end):
            debut, journee = _fmt(ev.get("DTSTART").dt, tz)
            fin = _fmt(ev.get("DTEND").dt, tz)[0] if ev.get("DTEND") else None
            item = {"agenda": name, "titre": str(ev.get("SUMMARY", "")), "debut": debut,
                    "fin": fin, "journee_entiere": journee}
            if ev.get("LOCATION"):
                item["lieu"] = str(ev.get("LOCATION"))
            out.append(item)
    return sorted(out, key=lambda e: e.get("debut", ""))


@tool("agenda_events",
      "Lit les rendez-vous des agendas de l'utilisateur sur une période (lecture seule).",
      {"start": {"type": "string", "description": "Date de début AAAA-MM-JJ (défaut : aujourd'hui)"},
       "days": {"type": "integer", "description": "Nombre de jours à couvrir (défaut 1)"}},
      enabled=_enabled)
async def agenda_events(ctx, start: str | None = None, days: int = 1):
    s = dt.date.fromisoformat(start) if start else dt.datetime.now(ZoneInfo(config.TIMEZONE)).date()
    evs = await events_between(s, s + dt.timedelta(days=max(1, min(days, 62))))
    return evs or "Aucun rendez-vous sur cette période."
