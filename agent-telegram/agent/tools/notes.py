"""Mémoire durable : ce que Bene demande de retenir."""
from .. import storage
from . import tool


@tool("remember", "Enregistre durablement une information que l'utilisateur te demande de retenir "
      "(préférence, fait sur un athlète, décision…). Elle sera rappelée dans toutes les futures conversations.",
      {"topic": {"type": "string", "description": "Thème court, ex. 'athlètes', 'préférences', 'business'"},
       "content": {"type": "string", "description": "L'information, formulée clairement"}},
      ["topic", "content"])
async def remember(ctx, topic: str, content: str):
    nid = storage.add_note(topic, content)
    return f"Noté (#{nid})."


@tool("list_notes", "Liste les notes mémorisées, éventuellement filtrées par thème.",
      {"topic": {"type": "string", "description": "Filtre optionnel"}})
async def list_notes(ctx, topic: str | None = None):
    notes = storage.get_notes(topic)
    return [{"id": n["id"], "topic": n["topic"], "content": n["content"]} for n in notes] or "Aucune note."


@tool("forget", "Supprime une note mémorisée par son numéro.",
      {"note_id": {"type": "integer"}}, ["note_id"])
async def forget(ctx, note_id: int):
    return "Note supprimée." if storage.delete_note(note_id) else "Note introuvable."
