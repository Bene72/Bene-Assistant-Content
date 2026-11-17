"""Mode abonnement : Claude tourne via Claude Code (Agent SDK), connecté à ton compte Claude.

Le SDK inclut Claude Code : rien d'autre à installer. Les compétences de agent/tools
sont branchées comme un serveur MCP interne.
"""
import logging

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ResultMessage, SystemMessage,
                              TextBlock, create_sdk_mcp_server, query)
from claude_agent_sdk import tool as sdk_tool

from . import config, storage, tools
from .brain import _system

log = logging.getLogger("brain_sdk")
SERVER = "benfit"
# WebFetch volontairement absent : la lecture de pages passe par fetch_page, qui est contrôlé
BUILTIN = ["WebSearch"] if config.WEB_SEARCH else []


def _server(ctx: dict):
    sdk_tools = []
    for t in tools.available(ctx.get("allowed")):

        def make(name):
            async def handler(args):
                log.info("outil %s %s", name, str(args)[:200])
                out, is_error = await tools.run(name, dict(args or {}), ctx)
                return {"content": [{"type": "text", "text": out}], "is_error": is_error}
            return handler

        sdk_tools.append(sdk_tool(t.name, t.description, t.schema)(make(t.name)))
    names = [f"mcp__{SERVER}__{t.name}" for t in sdk_tools]
    return create_sdk_mcp_server(SERVER, tools=sdk_tools), names


def _prompt(chat_id: int, user_text: str, use_history: bool) -> str:
    if not use_history:
        return user_text
    past = storage.history(chat_id, config.HISTORY_LENGTH)
    if not past:
        return user_text
    lines = [f"{'Bene' if m['role'] == 'user' else 'Toi'} : {m['content']}" for m in past]
    return ("<historique_recent>\n" + "\n\n".join(lines) + "\n</historique_recent>\n\n"
            f"Nouveau message : {user_text}")


async def think_sdk(chat_id: int, user_text: str, use_history: bool = True,
                    model: str | None = None, ctx: dict | None = None) -> str:
    ctx = ctx if ctx is not None else {"chat_id": chat_id}
    server, tool_names = _server(ctx)
    options = ClaudeAgentOptions(
        system_prompt=_system()[0]["text"],
        model=model or config.MODEL,
        mcp_servers={SERVER: server},
        tools=BUILTIN,                         # aucun accès aux fichiers ni au terminal
        allowed_tools=BUILTIN + tool_names,
        permission_mode="bypassPermissions",   # sans risque : seuls les outils ci-dessus existent
        setting_sources=[],                    # n'utilise pas tes réglages Claude Code perso
        cwd=str(config.DATA_DIR),
        max_turns=25,
        env={"CLAUDE_CODE_OAUTH_TOKEN": config.CLAUDE_CODE_OAUTH_TOKEN},
    )
    texts, result = [], None
    try:
        async for msg in query(prompt=_prompt(chat_id, user_text, use_history), options=options):
            if isinstance(msg, AssistantMessage):
                texts += [b.text for b in msg.content if isinstance(b, TextBlock)]
            elif isinstance(msg, ResultMessage):
                result = msg
            elif isinstance(msg, SystemMessage) and msg.subtype == "init":
                log.debug("init : %s", msg.data.get("tools"))
    except Exception as e:
        log.exception("échec Claude Code")
        low = str(e).lower()
        if "authentication" in low or "401" in low or "oauth" in low:
            return ("Je n'arrive pas à me connecter à ton compte Claude. Vérifie la connexion internet, "
                    "sinon relance connexion_claude.bat pour renouveler le jeton.")
        if "rate limit" in low or "429" in low or "usage limit" in low:
            return "Limite de ton abonnement atteinte pour le moment. Réessaie plus tard."
        return f"Erreur côté Claude : {e}"
    if result and result.is_error:
        status = result.api_error_status
        if status == 429:
            return "Limite de ton abonnement atteinte pour le moment. Réessaie plus tard."
        if status == 401:
            return "Connexion à ton compte Claude expirée : relance connexion_claude.bat."
        detail = "; ".join(result.errors or []) or result.subtype
        return f"Erreur côté Claude : {detail}"
    answer = (result.result if result and result.result else "\n".join(texts)).strip()
    return answer or "(pas de réponse)"
