"""Registre des compétences (outils) que Claude peut appeler.

Chaque compétence est déclarée avec le décorateur @tool. Pour en ajouter une,
crée un fichier dans ce dossier, décore une fonction async, puis importe le
module en bas de ce fichier.
"""
import json
import traceback
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    func: Callable[..., Awaitable[Any]]
    enabled: Callable[[], bool]


REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, properties: dict | None = None,
         required: list[str] | None = None, enabled: Callable[[], bool] = lambda: True):
    def deco(func):
        REGISTRY[name] = Tool(
            name=name,
            description=description,
            schema={"type": "object", "properties": properties or {}, "required": required or []},
            func=func,
            enabled=enabled,
        )
        return func
    return deco


def definitions() -> list[dict]:
    return [
        {"name": t.name, "description": t.description, "input_schema": t.schema}
        for t in REGISTRY.values() if t.enabled()
    ]


async def run(name: str, args: dict, ctx: dict) -> tuple[str, bool]:
    """Exécute un outil. Retourne (texte_résultat, est_une_erreur)."""
    t = REGISTRY.get(name)
    if not t or not t.enabled():
        return f"Outil inconnu ou désactivé : {name}", True
    try:
        result = await t.func(ctx=ctx, **args)
    except Exception as e:  # l'erreur est renvoyée à Claude qui peut corriger
        traceback.print_exc()
        return f"Erreur : {type(e).__name__}: {e}", True
    if not isinstance(result, str):
        result = json.dumps(result, ensure_ascii=False, default=str, indent=1)
    if len(result) > 30_000:
        result = result[:30_000] + "\n…[tronqué]"
    return result, False


# Chargement des compétences
from . import notes, schedule, web, coaching, github, agenda, personal  # noqa: E402,F401
