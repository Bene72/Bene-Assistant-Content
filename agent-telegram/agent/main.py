"""Point d'entrée : lance le bot Telegram et le planificateur."""
import asyncio
import logging
import sys

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (Application, CommandHandler, ContextTypes, MessageHandler,
                          filters)

from . import brief, config, scheduler, storage
from .brain import think

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s : %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(config.DATA_DIR / "agent.log", encoding="utf-8")],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("main")

TELEGRAM_LIMIT = 4000


def split(text: str) -> list[str]:
    parts = []
    while len(text) > TELEGRAM_LIMIT:
        cut = text.rfind("\n", 0, TELEGRAM_LIMIT)
        cut = cut if cut > 1000 else TELEGRAM_LIMIT
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    parts.append(text)
    return parts


def authorized(update: Update) -> bool:
    return update.effective_user is not None and update.effective_user.id in config.ALLOWED_USER_IDS


async def refuse(update: Update):
    uid = update.effective_user.id if update.effective_user else "?"
    log.warning("accès refusé à l'utilisateur %s", uid)
    if not config.ALLOWED_USER_IDS:
        await update.message.reply_text(
            f"Ton identifiant Telegram est {uid}.\n"
            "Mets-le dans le fichier .env à la ligne ALLOWED_USER_IDS, puis relance l'agent."
        )
    else:
        await update.message.reply_text("Accès refusé.")


async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    await update.message.reply_text(
        f"Salut {config.OWNER_NAME}, je suis en ligne.\n\n"
        "Écris-moi normalement. Commandes utiles :\n"
        "/brief : ton brief du jour maintenant\n"
        "/bilans : qui a fait son bilan (vendredi → lundi)\n"
        "/taches : voir les tâches planifiées\n"
        "/reset : effacer l'historique de la conversation\n"
        "/id : afficher ton identifiant Telegram"
    )


async def cmd_id(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Ton identifiant Telegram : {update.effective_user.id}")


async def cmd_reset(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    storage.clear_history(update.effective_chat.id)
    await update.message.reply_text("Historique effacé. On repart de zéro (mes notes sont conservées).")


async def cmd_tasks(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    tasks = storage.list_tasks()
    if not tasks:
        return await update.message.reply_text(
            "Aucune tâche planifiée. Demande-moi par exemple :\n"
            "« Chaque lundi à 8h, fais-moi le point sur les cycles qui finissent dans 2 semaines »"
        )
    lines = []
    for t in tasks:
        nxt = scheduler.next_run(t["id"])
        nxt_txt = nxt.strftime("%d/%m %H:%M") if nxt else "-"
        lines.append(f"#{t['id']} {t['name']}\n   cron {t['cron']} | prochaine : {nxt_txt}")
    await update.message.reply_text("\n".join(lines))


async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    await answer(update, context, brief.PROMPT, use_history=False)


async def cmd_bilans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    await answer(update, context, brief.BILANS_PROMPT)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    text = update.message.text or update.message.caption or ""
    if not text.strip():
        return await update.message.reply_text("Pour l'instant je ne lis que le texte.")
    await answer(update, context, text)


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, use_history: bool = True):
    chat_id = update.effective_chat.id

    async def keep_typing():
        while True:
            await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
            await asyncio.sleep(4)

    typing = asyncio.create_task(keep_typing())
    try:
        reply = await think(chat_id, text, use_history=use_history)
    except Exception as e:
        log.exception("erreur")
        reply = f"Oups, une erreur : {type(e).__name__}: {e}"
    finally:
        typing.cancel()
    for part in split(reply):
        await update.message.reply_text(part, disable_web_page_preview=True)


async def post_init(app: Application):
    async def send(chat_id: int, text: str):
        for part in split(text):
            await app.bot.send_message(chat_id, part, disable_web_page_preview=True)

    scheduler.set_sender(send)
    brief.ensure_daily_task()
    scheduler.start()
    for uid in config.ALLOWED_USER_IDS:
        try:
            await app.bot.send_message(uid, "✅ Agent Ben&Fit démarré.")
        except Exception:
            pass  # l'utilisateur n'a pas encore écrit au bot


def main():
    problems = config.check()
    if problems:
        print("\nConfiguration incomplète :")
        for p in problems:
            print(" -", p)
        print("\nOuvre le fichier .env, complète-le, puis relance.\n")
        sys.exit(2)

    storage.init()
    from . import tools
    active = [t.name for t in tools.REGISTRY.values() if t.enabled()]
    log.info("mode %s | modèle %s | compétences : %s", config.AUTH_MODE, config.MODEL, ", ".join(active))
    if not config.ALLOWED_USER_IDS:
        log.warning("ALLOWED_USER_IDS vide : écris au bot, il te donnera ton identifiant.")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(CommandHandler("taches", cmd_tasks))
    app.add_handler(CommandHandler("brief", cmd_brief))
    app.add_handler(CommandHandler("bilans", cmd_bilans))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    log.info("Agent en ligne. Ctrl+C pour arrêter.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
