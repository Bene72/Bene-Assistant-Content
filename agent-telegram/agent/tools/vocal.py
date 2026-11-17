"""Compétence : envoyer une note vocale."""
from .. import voice
from . import tool


@tool("send_voice_note",
      "Envoie un texte à l'utilisateur sous forme de note vocale Telegram (voix féminine). "
      "À utiliser quand il demande une réponse « en vocal », « en audio » ou « à l'oral ». "
      "Rédige le texte pour l'oral : phrases simples et enchaînées, pas d'émojis, pas de listes, "
      "pas de liens. Après l'envoi, réponds en une ligne très courte.",
      {"text": {"type": "string", "description": "Le texte à lire, rédigé pour l'oral"}}, ["text"])
async def send_voice_note(ctx, text: str):
    from .. import config
    if ctx.get("client_data") and not config.TTS_CLIENT_DATA:
        return ("Refusé : ce message contient des données clients et la voix passe par un service "
                "Microsoft externe. Réponds en texte. (Bene peut l'autoriser avec TTS_CLIENT_DATA=true dans .env.)")
    ok = await voice.send(ctx["chat_id"], text)
    return "Note vocale envoyée." if ok else "La note vocale a échoué : envoie la réponse en texte."
