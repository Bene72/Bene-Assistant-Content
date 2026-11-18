"""Routines déclenchées par Home Assistant (événement « jarvis_routine »).

Dans une automatisation Home Assistant, action « Déclencher un événement » :
  event: jarvis_routine
  event_data:
    routine: brief        → le brief du matin sur Telegram (une seule fois par jour)
    routine: question     → question posée à l'enceinte ; réponse lue sur l'enceinte (canal restreint)
      text: "{{ trigger.slots.question }}"
      satellite: "{{ trigger.device_id }}"
    routine: message      → Jarvis traite le texte avec toutes ses compétences et te répond sur Telegram
      text: "Je viens de rentrer, qu'est-ce qu'il me reste à faire aujourd'hui ?"
"""
import logging

from . import brief, config, home

log = logging.getLogger("routines")
HOME_CHAT = 0  # conversation « maison », séparée de Telegram
_send = None

SPEAKER = ("[Question posée à voix haute à l'enceinte de la maison. Quelqu'un d'autre que {owner} "
           "peut avoir parlé.] {text}\n\nRéponds en 1 à 3 phrases courtes, faites pour être lues par une "
           "enceinte : pas de liste, pas d'émoji, pas de lien, pas de titre. Tu ne peux ni lire les mails ni "
           "les données des clients depuis l'enceinte : si on te le demande, dis que c'est sur Telegram.")


def set_sender(func):
    global _send
    _send = func


def owner() -> int | None:
    return next(iter(sorted(config.ALLOWED_USER_IDS)), None)


async def handle(data: dict):
    from .brain import think

    routine = str(data.get("routine") or "").strip().lower()
    text = str(data.get("text") or "").strip()[:1000]
    uid = owner()
    log.info("routine %s", routine)

    if routine == "brief":
        if brief.sent_today() or uid is None or _send is None:
            return
        brief.mark_sent()
        await brief.run_daily(uid, brief.parse_format(str(data.get("format") or config.BRIEF_FORMAT)), _send)

    elif routine == "question":
        if not text:
            return
        target = await home.resolve_satellite(str(data.get("satellite") or data.get("device_id") or ""))
        ctx = {"allowed": set(config.HOME_VOICE_TOOLS)}
        reply = await think(HOME_CHAT, SPEAKER.format(owner=config.OWNER_NAME, text=text), ctx=ctx,
                            use_history=False, model=config.MODEL)
        spoken = await home.announce(target, reply) if target else False
        if config.HOME_TRACE and _send and uid is not None:
            await _send(uid, f"🔊 Maison : « {text} »\n{reply}" + ("" if spoken else "\n(aucune enceinte configurée)"))

    elif routine == "message":
        if not text or uid is None or _send is None:
            return
        reply = await think(uid, f"[Routine maison déclenchée automatiquement] {text}", use_history=False)
        await _send(uid, reply)

    else:
        log.warning("routine inconnue : %s", routine)
        if _send and uid is not None:
            await _send(uid, f"Routine maison inconnue : « {routine} ». Connues : brief, question, message.")
