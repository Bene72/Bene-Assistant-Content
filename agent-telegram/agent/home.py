"""Home Assistant : appels REST (états, commandes, annonces) et écoute des routines.

Jarvis ne fait que parler à Home Assistant, qui gère lui-même les appareils.
Les automatismes simples (lumière quand ça bouge) tournent dans Home Assistant, en local,
même si Jarvis est éteint. Jarvis intervient pour ce qui demande de « réfléchir ».
"""
import asyncio
import json
import logging
import time

import httpx

from . import config

log = logging.getLogger("home")
EVENT = "jarvis_routine"
connected = False  # état de l'écoute websocket (pour /diag)

CONTROL_DOMAINS = {"light", "switch", "fan", "cover", "climate", "media_player", "scene", "script",
                   "input_boolean", "vacuum", "humidifier"}
STATUS_DOMAINS = CONTROL_DOMAINS | {"binary_sensor", "sensor", "person", "weather"}
SENSOR_CLASSES = {"temperature", "humidity", "illuminance", "power", "energy", "battery", "co2", "pm25"}


def enabled() -> bool:
    return bool(config.HA_URL and config.HA_TOKEN)


def _headers():
    return {"Authorization": f"Bearer {config.HA_TOKEN}", "Content-Type": "application/json"}


async def api(method: str, path: str, payload=None):
    async with httpx.AsyncClient(timeout=20, trust_env=False) as c:
        r = await c.request(method, f"{config.HA_URL}/api/{path.lstrip('/')}", headers=_headers(), json=payload)
    if r.status_code == 401:
        raise PermissionError("jeton Home Assistant refusé (HA_TOKEN)")
    if r.status_code >= 400:
        raise RuntimeError(f"Home Assistant {r.status_code} : {r.text[:300]}")
    ctype = r.headers.get("content-type", "")
    return r.json() if "json" in ctype else r.text


async def template(tpl: str) -> str:
    return await api("POST", "template", {"template": tpl})


async def states() -> list[dict]:
    return await api("GET", "states")


async def areas_for(entity_ids: list[str]) -> dict[str, str]:
    if not entity_ids:
        return {}
    ids = json.dumps(entity_ids)
    tpl = ("{% set ns = namespace(l=[]) %}{% for e in " + ids + " %}"
           "{% set ns.l = ns.l + [[e, area_name(e) or '']] %}{% endfor %}{{ ns.l | tojson }}")
    try:
        raw = await template(tpl)
        return {k: v for k, v in json.loads(raw)}
    except Exception:
        log.warning("pièces indisponibles", exc_info=True)
        return {}


async def call(domain: str, service: str, data: dict):
    return await api("POST", f"services/{domain}/{service}", data)


async def resolve_satellite(ref: str | None) -> str | None:
    """Accepte un entity_id assist_satellite.*, un id d'appareil, ou rien (= HA_SATELLITE)."""
    ref = (ref or "").strip()
    if ref.startswith(("assist_satellite.", "media_player.")):
        return ref
    if ref:
        try:
            raw = await template("{{ device_entities('" + ref.replace("'", "") + "') "
                                 "| select('match', 'assist_satellite\\\\.') | list | first | default('') }}")
            if str(raw).strip():
                return str(raw).strip()
        except Exception:
            log.warning("satellite introuvable pour %s", ref, exc_info=True)
    return config.HA_SATELLITE or None


async def announce(target: str | None, message: str) -> bool:
    """Fait parler l'enceinte. assist_satellite → annonce ; media_player → synthèse vocale de HA."""
    if not target or not message.strip():
        return False
    message = message.strip()[:900]
    if target.startswith("assist_satellite."):
        await call("assist_satellite", "announce", {"entity_id": target, "message": message})
    else:
        await call("tts", "speak", {"entity_id": config.HA_TTS_ENTITY or "tts.home_assistant_cloud",
                                    "media_player_entity_id": target, "message": message})
    return True


# --- Écoute des routines (websocket) --------------------------------------------------
_recent: dict[str, float] = {}
_hour: list[float] = []


def _throttle(name: str) -> bool:
    """Garde-fou quota : une même routine au plus toutes les 20 s, 30 routines par heure au total."""
    now = time.time()
    if now - _recent.get(name, 0) < 20:
        return False
    _hour[:] = [t for t in _hour if now - t < 3600]
    if len(_hour) >= 30:
        return False
    _recent[name] = now
    _hour.append(now)
    return True


async def listen(handler):
    """Se connecte au websocket de Home Assistant et transmet les événements « jarvis_routine »."""
    global connected
    import websockets

    url = config.HA_URL.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/api/websocket"
    delay = 5
    while True:
        try:
            async with websockets.connect(url, max_size=2 ** 22, open_timeout=15, proxy=None) as ws:
                json.loads(await ws.recv())  # auth_required
                await ws.send(json.dumps({"type": "auth", "access_token": config.HA_TOKEN}))
                auth = json.loads(await ws.recv())
                if auth.get("type") != "auth_ok":
                    log.error("Home Assistant refuse le jeton (HA_TOKEN) : nouvel essai dans 10 min")
                    await asyncio.sleep(600)
                    continue
                await ws.send(json.dumps({"id": 1, "type": "subscribe_events", "event_type": EVENT}))
                connected, delay = True, 5
                log.info("écoute des routines Home Assistant active")
                async for raw in ws:
                    m = json.loads(raw)
                    if m.get("type") != "event":
                        continue
                    data = (m.get("event") or {}).get("data") or {}
                    name = str(data.get("routine") or "?").lower()
                    if not _throttle(name):
                        log.warning("routine %s ignorée (trop fréquente)", name)
                        continue
                    asyncio.create_task(_safe(handler, data))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning("Home Assistant injoignable (%s) : nouvel essai dans %ss", type(e).__name__, delay)
        connected = False
        await asyncio.sleep(delay)
        delay = min(delay * 2, 300)


async def _safe(handler, data):
    try:
        await handler(data)
    except Exception:
        log.exception("échec de la routine %s", data)
