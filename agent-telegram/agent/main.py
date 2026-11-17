"""Point d'entrée : lance le bot Telegram et le planificateur."""
import asyncio
import html
import logging
import sys
from logging.handlers import RotatingFileHandler

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (Application, CommandHandler, ContextTypes, MessageHandler,
                          filters)

from . import brief, config, confirm, diag, home, routines, scheduler, storage, stt, voice
from .brain import think

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s : %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout),
              RotatingFileHandler(config.DATA_DIR / "agent.log", maxBytes=2_000_000, backupCount=3,
                                  encoding="utf-8")],
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


def fmt(text: str) -> str:
    """Mise en forme légère pour Telegram : une ligne qui commence par « ## » devient un titre en gras."""
    out = []
    for line in text.split("\n"):
        safe = html.escape(line, quote=False)
        out.append(f"<b>{safe[3:].strip()}</b>" if line.startswith("## ") else safe)
    return "\n".join(out)


async def send_text(bot, chat_id: int, text: str):
    """Envoie un texte (découpé si besoin), avec titres en gras ; repli en texte brut si Telegram refuse."""
    for part in split(text):
        try:
            await bot.send_message(chat_id, fmt(part), parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            await bot.send_message(chat_id, part.replace("## ", ""), disable_web_page_preview=True)


def authorized(update: Update) -> bool:
    """Uniquement Bene, et uniquement en conversation privée (jamais dans un groupe)."""
    return (update.effective_user is not None
            and update.effective_user.id in config.ALLOWED_USER_IDS
            and update.effective_chat is not None and update.effective_chat.type == "private")


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
    if config.PROFILE == "box":
        return await update.message.reply_text(
            f"Salut {config.OWNER_NAME}, ici le bot de la salle (BoxLog), en lecture seule.\n\n"
            "Écris-moi normalement, par exemple :\n"
            "- qu'est-ce qu'on a fait ces 3 dernières semaines ?\n"
            "- c'est quand la dernière fois qu'on a fait des thrusters ?\n"
            "- propose-moi le WOD de jeudi sans doublon avec la semaine\n\n"
            "/prog : résumé des 3 dernières semaines\n"
            "/prog 6 : sur 6 semaines\n"
            "/mouvement snatch : historique d'un mouvement\n"
            "/diag : vérifier la connexion\n"
            "/reset : effacer l'historique de la conversation"
        )
    await update.message.reply_text(
        f"Salut {config.OWNER_NAME}, ici {config.ASSISTANT_NAME}.\n\n"
        "Écris-moi ou envoie-moi un vocal. Commandes utiles :\n"
        "/brief : ton brief du jour en texte\n"
        "/brief vocal (ou /briefvocal) : en note vocale · /brief les deux : texte + vocal\n"
        "/bilans : qui a fait son bilan (vendredi → lundi)\n"
        "/reponse Prénom : réponse prête à envoyer à son dernier bilan\n"
        "/cycle Prénom + consignes : prépare son prochain cycle (brouillon, après ton /ok)\n"
        "/diag : vérifier que tout est bien connecté\n"
        "/taches : voir les tâches planifiées\n"
        "/reset : effacer l'historique de la conversation\n"
        "/id : afficher ton identifiant Telegram"
    )


async def cmd_prog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    arg = (context.args or ["3"])[0]
    weeks = max(1, min(int(arg), 16)) if arg.isdigit() else 3
    await answer(update, context,
                 f"Fais-moi le point sur la programmation de la salle des {weeks} dernières semaines "
                 f"(box_programming sur {weeks * 7} jours) : ce qu'on a fait semaine par semaine en très "
                 "condensé, les mouvements et formats les plus utilisés, ce qui manque, et les doublons à "
                 "éviter pour la suite.", model=config.MODEL_COACH)


async def cmd_mouvement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    q = " ".join(context.args or []).strip()
    if not q:
        return await update.message.reply_text("Dis-moi lequel : /mouvement thruster")
    await answer(update, context, f"Historique du mouvement « {q} » à la salle (box_search_movement, 12 semaines) : "
                 "dernière fois, fréquence, dans quels formats.")


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


async def cmd_brief(update: Update, context: ContextTypes.DEFAULT_TYPE, fmt: str | None = None):
    if not authorized(update):
        return await refuse(update)
    fmt = fmt or brief.parse_format(" ".join(context.args or []), default="texte")
    chat_id = update.effective_chat.id

    async def send_brief(cid, text):
        await send_text(context.bot, cid, text)

    action = ChatAction.RECORD_VOICE if fmt == "vocal" else ChatAction.TYPING

    async def keep_busy():
        while True:
            await context.bot.send_chat_action(chat_id, action)
            await asyncio.sleep(4)

    busy = asyncio.create_task(keep_busy())
    try:
        await brief.run(chat_id, fmt, send_brief)
    except Exception as e:
        log.exception("erreur brief")
        await update.message.reply_text(f"Oups, le brief a échoué : {type(e).__name__}: {e}")
    finally:
        busy.cancel()


async def cmd_brief_vocal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_brief(update, context, fmt="vocal")


async def cmd_bilans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    await answer(update, context, brief.BILANS_PROMPT)


async def cmd_reponse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    name = " ".join(context.args or []).strip()
    if not name:
        return await update.message.reply_text("Dis-moi pour qui : /reponse Prénom")
    await answer(update, context, f"Prépare-moi la réponse au dernier bilan de {name}.", model=config.MODEL_COACH)


async def cmd_cycle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    args = " ".join(context.args or []).strip()
    if not args:
        return await update.message.reply_text(
            "Dis-moi pour qui et ce que tu veux :\n/cycle Wissam 5 semaines, focus force, ménager le genou")
    await answer(update, context, f"Prépare le prochain cycle de programmation pour : {args}", model=config.MODEL_COACH)


async def cmd_diag(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    await update.message.reply_text(await diag.run())


async def cmd_ok(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    await update.message.reply_text(await confirm.execute(update.effective_chat.id), disable_web_page_preview=True)


async def cmd_non(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    await update.message.reply_text(confirm.cancel(update.effective_chat.id))


SPOKEN = ("[Message vocal de {owner}, transcrit automatiquement : il peut y avoir des erreurs de "
          "transcription, devine le sens.] {text}\n\n"
          "Réponds comme à l'oral : naturel, phrases courtes, pas de liste, pas d'émoji, pas de lien, "
          "pas de titre « ## ». Va droit au but.")


async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    chat_id = update.effective_chat.id
    media = update.message.voice or update.message.audio
    if media is None:
        return
    if media.file_size and media.file_size > 19_000_000:
        return await update.message.reply_text("Vocal trop long pour moi (20 Mo max). Découpe-le en plusieurs.")
    if not stt.is_downloaded():
        await update.message.reply_text("🎙 Premier vocal : je télécharge la reconnaissance vocale "
                                        "(~460 Mo, une seule fois). Ça peut prendre quelques minutes…")
    await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
    tmp = config.DATA_DIR / f"vocal-{update.message.message_id}.oga"
    try:
        f = await media.get_file()
        await f.download_to_drive(str(tmp))
        text = await stt.transcribe(str(tmp))
    except Exception as e:
        log.exception("transcription")
        return await update.message.reply_text(f"Je n'ai pas réussi à écouter ton vocal : {type(e).__name__}: {e}")
    finally:
        tmp.unlink(missing_ok=True)
    if not text:
        return await update.message.reply_text("Je n'ai rien entendu dans ce vocal.")
    await update.message.reply_text(f"🎙 « {text} »")
    await answer(update, context, SPOKEN.format(owner=config.OWNER_NAME, text=text), spoken=True,
                 history_text=f"(vocal) {text}")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not authorized(update):
        return await refuse(update)
    text = update.message.text or update.message.caption or ""
    if not text.strip():
        return await update.message.reply_text("Pour l'instant je ne lis que le texte.")
    await answer(update, context, text)


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, use_history: bool = True,
                 model: str | None = None, spoken: bool = False, history_text: str | None = None):
    chat_id = update.effective_chat.id
    ctx: dict = {}

    async def keep_typing():
        while True:
            await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
            await asyncio.sleep(4)

    typing = asyncio.create_task(keep_typing())
    try:
        reply = await think(chat_id, text, ctx=ctx, use_history=use_history, model=model,
                            history_text=history_text)
    except Exception as e:
        log.exception("erreur")
        reply = f"Oups, une erreur : {type(e).__name__}: {e}"
        spoken = False
    finally:
        typing.cancel()
    if spoken and config.VOICE_REPLY in ("voix", "vocal", "les deux"):
        if ctx.get("client_data") and not config.TTS_CLIENT_DATA:
            reply += "\n\n(Réponse en texte : elle contient des données clients, je ne les envoie pas au service vocal.)"
        else:
            await context.bot.send_chat_action(chat_id, ChatAction.RECORD_VOICE)
            if await voice.send(chat_id, reply):
                if config.VOICE_REPLY in ("voix", "vocal"):
                    return
            else:
                reply += "\n\n(La réponse vocale a échoué.)"
    await send_text(context.bot, chat_id, reply)


async def post_init(app: Application):
    async def send(chat_id: int, text: str):
        await send_text(app.bot, chat_id, text)

    async def send_voice(chat_id: int, path, caption: str = ""):
        with open(path, "rb") as f:
            await app.bot.send_voice(chat_id, voice=f, caption=caption or None, filename="jarvis.mp3")

    scheduler.set_sender(send)
    voice.set_sender(send_voice)
    confirm.set_sender(send)
    routines.set_sender(send)
    if config.PROFILE == "coach" and home.enabled():
        app.bot_data["ha_listener"] = asyncio.create_task(home.listen(routines.handle))
    if config.PROFILE == "coach":
        brief.ensure_daily_task()
    scheduler.start()
    if brief.missed_today():  # PC éteint à l'heure du brief : on le rattrape
        log.info("brief du matin manqué : rattrapage")
        task = next((t for t in storage.list_tasks() if t["name"] == brief.NAME), None)
        if task:
            asyncio.create_task(scheduler._run_task(task["id"]))
    for uid in config.ALLOWED_USER_IDS:
        try:
            await app.bot.send_message(uid, "✅ Bot BoxLog démarré." if config.PROFILE == "box" else f"✅ {config.ASSISTANT_NAME} démarré.")
        except Exception:
            pass  # l'utilisateur n'a pas encore écrit au bot


def main():
    problems = config.check()
    if problems:
        print("\nConfiguration incomplète :")
        for p in problems:
            print(" -", p)
        print(f"\nOuvre le fichier {config.ENV_FILE.name}, complète-le, puis relance.\n")
        sys.exit(2)

    storage.init()
    try:
        storage.backup()
    except Exception:
        log.exception("sauvegarde impossible")
    from . import tools
    active = [t.name for t in tools.REGISTRY.values() if t.enabled()]
    log.info("mode %s | modèle %s | compétences : %s", config.AUTH_MODE, config.MODEL, ", ".join(active))
    if not config.ALLOWED_USER_IDS:
        log.warning("ALLOWED_USER_IDS vide : écris au bot, il te donnera ton identifiant.")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("reset", cmd_reset))
    if config.PROFILE == "box":
        app.add_handler(CommandHandler("prog", cmd_prog))
        app.add_handler(CommandHandler("mouvement", cmd_mouvement))
        app.add_handler(CommandHandler("diag", cmd_diag))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
        log.info("Bot BoxLog en ligne. Ctrl+C pour arrêter.")
        return app.run_polling(drop_pending_updates=True)
    app.add_handler(CommandHandler("taches", cmd_tasks))
    app.add_handler(CommandHandler("brief", cmd_brief))
    app.add_handler(CommandHandler("bilans", cmd_bilans))
    app.add_handler(CommandHandler("briefvocal", cmd_brief_vocal))
    app.add_handler(CommandHandler("reponse", cmd_reponse))
    app.add_handler(CommandHandler("diag", cmd_diag))
    app.add_handler(CommandHandler("cycle", cmd_cycle))
    app.add_handler(CommandHandler("ok", cmd_ok))
    app.add_handler(CommandHandler("non", cmd_non))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    log.info("Agent en ligne. Ctrl+C pour arrêter.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
