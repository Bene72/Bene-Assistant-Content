"""Compétence maison : voir et piloter les appareils via Home Assistant."""
from .. import config, home
from . import tool

_enabled = home.enabled

ACTIONS = {
    "on": "turn_on", "off": "turn_off", "toggle": "toggle",
    "open": "open_cover", "close": "close_cover", "stop": "stop_cover",
    "play": "media_play", "pause": "media_pause",
    "set_temperature": "set_temperature",
}


def _compact(s: dict, area: str) -> dict:
    a = s.get("attributes", {})
    out = {"id": s["entity_id"], "nom": a.get("friendly_name", s["entity_id"]), "etat": s["state"]}
    if area:
        out["piece"] = area
    dom = s["entity_id"].split(".")[0]
    if dom == "light" and a.get("brightness") is not None:
        out["luminosite_pct"] = round(a["brightness"] / 255 * 100)
    if dom == "climate":
        out.update({k: a[k] for k in ("current_temperature", "temperature", "hvac_action") if a.get(k) is not None})
    if dom in ("sensor", "binary_sensor") and a.get("device_class"):
        out["type"] = a["device_class"]
    if a.get("unit_of_measurement"):
        out["unite"] = a["unit_of_measurement"]
    return out


@tool("home_status",
      "Maison (Home Assistant) : liste les appareils et capteurs avec leur pièce et leur état "
      "(lumières, prises, volets, chauffage, détecteurs de mouvement, température, scènes…). "
      "Filtre optionnel par mot (pièce, nom) ou par type (light, switch, sensor, binary_sensor, climate, "
      "cover, scene, media_player). À appeler avant home_control pour trouver les bons id.",
      {"query": {"type": "string"}, "domain": {"type": "string"}}, enabled=_enabled)
async def home_status(ctx, query: str | None = None, domain: str | None = None):
    rows = []
    for s in await home.states():
        dom = s["entity_id"].split(".")[0]
        if dom not in home.STATUS_DOMAINS or (domain and dom != domain):
            continue
        a = s.get("attributes", {})
        if dom == "sensor" and a.get("device_class") not in home.SENSOR_CLASSES:
            continue
        if s["state"] in ("unavailable", "unknown") and dom not in ("light", "switch"):
            continue
        rows.append(s)
    areas = await home.areas_for([s["entity_id"] for s in rows][:300])
    out = [_compact(s, areas.get(s["entity_id"], "")) for s in rows]
    if query:
        q = query.lower()
        out = [o for o in out if q in (o["nom"] + " " + o.get("piece", "") + " " + o["id"]).lower()]
    return out[:120] or "Aucun appareil trouvé."


@tool("home_control",
      "Maison : commande un ou plusieurs appareils Home Assistant. action : on, off, toggle (lumières, prises, "
      "scènes, scripts), open/close/stop (volets), play/pause (lecteurs), set_temperature (chauffage). "
      "Pour une lumière, options : brightness_pct (1-100), color_temp_kelvin (2200 chaud à 6500 froid), "
      "color_name (ex. 'red', 'blue'). Pas de serrures ni d'alarme.",
      {"entity_ids": {"type": "array", "items": {"type": "string"}},
       "action": {"type": "string", "enum": sorted(ACTIONS)},
       "brightness_pct": {"type": "integer"}, "color_temp_kelvin": {"type": "integer"},
       "color_name": {"type": "string"}, "temperature": {"type": "number"}},
      ["entity_ids", "action"], enabled=_enabled)
async def home_control(ctx, entity_ids: list, action: str, brightness_pct: int | None = None,
                       color_temp_kelvin: int | None = None, color_name: str | None = None,
                       temperature: float | None = None):
    if not entity_ids or len(entity_ids) > 30:
        raise ValueError("entre 1 et 30 appareils")
    service = ACTIONS.get(action)
    if not service:
        raise ValueError(f"action inconnue : {action}")
    by_domain: dict[str, list[str]] = {}
    for e in entity_ids:
        dom = str(e).split(".")[0]
        if dom not in home.CONTROL_DOMAINS:
            raise PermissionError(f"type d'appareil non autorisé : {e}")
        by_domain.setdefault(dom, []).append(str(e))
    done = []
    for dom, ids in by_domain.items():
        svc = service
        if dom in ("scene", "script") and action in ("on", "toggle"):
            svc = "turn_on"
        data: dict = {"entity_id": ids}
        if dom == "light" and action == "on":
            if brightness_pct is not None:
                data["brightness_pct"] = max(1, min(int(brightness_pct), 100))
            if color_temp_kelvin is not None:
                data["color_temp_kelvin"] = max(1500, min(int(color_temp_kelvin), 7000))
            if color_name:
                data["color_name"] = str(color_name)[:30]
        if action == "set_temperature":
            if dom != "climate" or temperature is None:
                raise ValueError("set_temperature : un appareil climate et une température")
            data["temperature"] = max(5.0, min(float(temperature), 28.0))
        await home.call(dom, svc, data)
        done += ids
    return f"OK : {action} sur {', '.join(done)}."


@tool("home_announce",
      "Maison : fait dire une phrase à voix haute par l'enceinte (Home Assistant Voice ou autre), "
      "par exemple « le dîner est prêt ». satellite optionnel (sinon l'enceinte par défaut).",
      {"message": {"type": "string"}, "satellite": {"type": "string"}}, ["message"],
      enabled=lambda: home.enabled() and bool(config.HA_SATELLITE))
async def home_announce(ctx, message: str, satellite: str | None = None):
    if ctx.get("client_data"):
        raise PermissionError("pas d'annonce à voix haute de données clients")
    target = await home.resolve_satellite(satellite)
    await home.announce(target, message)
    return "Annoncé."
