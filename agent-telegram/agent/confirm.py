"""Confirmation obligatoire avant toute action qui écrit à l'extérieur (GitHub…).

Le résumé envoyé à Bene est produit par le code, pas par le modèle : même si l'agent
était manipulé par un texte piégé, il ne peut ni exécuter ni maquiller l'action.
"""
import asyncio
import logging
import time

log = logging.getLogger("confirm")
TTL = 900  # 15 minutes
_pending: dict[int, dict] = {}
_send = None


def set_sender(func):
    global _send
    _send = func


def request(chat_id: int, summary: str, action) -> str:
    """Met une action en attente. `action` : fonction async sans argument."""
    _pending[chat_id] = {"summary": summary, "action": action, "ts": time.time()}
    if _send:
        asyncio.create_task(_send(chat_id, f"⚠️ Action à confirmer :\n{summary}\n\n/ok pour valider · /non pour annuler"))
    return ("Action mise en attente : elle ne sera exécutée que si l'utilisateur envoie /ok. "
            "Dis-lui simplement qu'une confirmation lui a été envoyée.")


async def execute(chat_id: int) -> str:
    p = _pending.pop(chat_id, None)
    if not p:
        return "Rien à confirmer."
    if time.time() - p["ts"] > TTL:
        return "La demande a expiré (15 min). Redemande-la."
    try:
        return str(await p["action"]())
    except Exception as e:
        log.exception("action confirmée en échec")
        return f"L'action a échoué : {e}"


def cancel(chat_id: int) -> str:
    return "Annulé." if _pending.pop(chat_id, None) else "Rien à annuler."
