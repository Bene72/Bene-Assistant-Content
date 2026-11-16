"""/diag : vérifie chaque connexion sans consommer le quota Claude."""
import httpx

from . import config, scheduler, storage


async def run() -> str:
    lines = [f"Mode {config.AUTH_MODE} · modèle {config.MODEL}"]

    def add(ok, label, detail=""):
        lines.append(("✅ " if ok else "❌ ") + label + (f" : {detail}" if detail else ""))

    add(bool(config.CLAUDE_CODE_OAUTH_TOKEN or config.ANTHROPIC_API_KEY), "Jeton Claude présent")

    if config.PROFILE == "box":
        if config.BOX_SUPABASE_URL and config.BOX_SUPABASE_KEY:
            try:
                from .tools.box import _get as bget
                wods = await bget("wods", [("select", "wod_date"), ("order", "wod_date.desc"), ("limit", "1")])
                progs = await bget("programs", [("select", "id"), ("status", "eq.active")])
                add(True, "BoxLog", f"dernier WOD le {wods[0]['wod_date'] if wods else '—'}, "
                                    f"{len(progs)} programme(s) actif(s)")
            except Exception as e:
                add(False, "BoxLog", str(e)[:150])
        else:
            add(False, "BoxLog non configuré (BOX_SUPABASE_URL / BOX_SUPABASE_KEY)")
        return "\n".join(lines)

    if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
        try:
            from .tools.coaching import _get
            r = await _get("profiles", [("select", "id"), ("role", "eq.client"), ("limit", "1")],
                           {"Prefer": "count=exact"})
            add(True, "Dashboard coaching", f"{r.headers.get('content-range', '?').split('/')[-1]} athlètes")
        except Exception as e:
            add(False, "Dashboard coaching", str(e)[:150])
    else:
        lines.append("➖ Dashboard coaching non configuré")

    if config.CALENDARS:
        from .tools.agenda import _fetch
        for name, url in config.CALENDARS.items():
            try:
                cal = await _fetch(url)
                add(True, f"Agenda {name}", f"{len(cal.walk('VEVENT'))} événements")
            except Exception as e:
                add(False, f"Agenda {name}", str(e)[:120])
    else:
        lines.append("➖ Agenda non configuré")

    if config.GITHUB_TOKEN:
        try:
            from .tools.github import _call
            add(True, "GitHub", (await _call("GET", "/user")).get("login", ""))
        except Exception as e:
            add(False, "GitHub", str(e)[:120])
    else:
        lines.append("➖ GitHub non configuré")

    try:
        from . import voice
        p = await voice.synthesize("Test de la voix.")
        p.unlink(missing_ok=True)
        add(True, "Voix", config.TTS_VOICE)
    except Exception as e:
        add(False, "Voix", f"{type(e).__name__} {str(e)[:100]}")

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.get("https://api.anthropic.com")
        add(True, "Accès réseau à Claude")
    except Exception as e:
        add(False, "Accès réseau à Claude (antivirus ?)", type(e).__name__)

    tasks = storage.list_tasks(enabled_only=True)
    lines.append(f"⏰ {len(tasks)} tâche(s) planifiée(s)")
    for t in tasks:
        nxt = scheduler.next_run(t["id"])
        lines.append(f"   {t['name']} → {nxt:%d/%m %H:%M}" if nxt else f"   {t['name']}")
    return "\n".join(lines)
