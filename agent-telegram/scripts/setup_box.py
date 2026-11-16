"""Crée le fichier .env.box du bot de la salle (lancé par installer_bot_boxlog.bat)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV, BOX = ROOT / ".env", ROOT / ".env.box"


def lire(path: Path) -> dict:
    out = {}
    if path.exists():
        for ligne in path.read_text(encoding="utf-8").splitlines():
            if "=" in ligne and not ligne.strip().startswith("#"):
                k, v = ligne.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def demander(texte: str, exemple: str, test, actuel: str = "") -> str:
    while True:
        print(f"\n{texte}\nExemple : {exemple}")
        if actuel:
            print("(Entrée seule = garder la valeur actuelle)")
        v = input("Colle la valeur (clic droit = coller), puis Entrée :\n").strip().strip("\"'")
        if not v and actuel:
            return actuel
        if test(v):
            return v
        print("⚠️ Ça ne ressemble pas à ce qui est attendu, recommence.")


def main():
    coach = lire(ENV)
    if not coach.get("CLAUDE_CODE_OAUTH_TOKEN") and not coach.get("ANTHROPIC_API_KEY"):
        print("\nInstalle et configure d'abord l'agent principal (install.bat).\n")
        sys.exit(1)
    old = lire(BOX)
    print("\n=== Bot de la salle (BoxLog), lecture seule ===")
    print("Il te faut 3 choses :")
    print(" 1. un NOUVEAU bot Telegram : @BotFather > /newbot (ex. BoxLog Prog, boxlog_prog_bot)")
    print(" 2. l'adresse du projet Supabase de BoxLog")
    print(" 3. sa clé secrète (service_role ou sb_secret_)")
    print("    Les deux se trouvent dans Vercel > projet BoxLog > Settings > Environment Variables,")
    print("    ou dans Supabase > projet BoxLog > Project Settings > API Keys.")

    token = demander("1/3  Token du NOUVEAU bot Telegram", "123456789:AA...",
                     lambda v: bool(re.match(r"^\d{6,}:[\w-]{30,}$", v)), old.get("TELEGRAM_BOT_TOKEN", ""))
    if token == coach.get("TELEGRAM_BOT_TOKEN"):
        print("\n⚠️ C'est le token de ton agent principal. Il faut un bot différent : crée-en un avec /newbot.")
        sys.exit(1)
    url = demander("2/3  Adresse Supabase de BoxLog", "https://abcdefgh.supabase.co",
                   lambda v: bool(re.match(r"^https://[a-z0-9]+\.supabase\.co/?$", v)), old.get("BOX_SUPABASE_URL", ""))
    if url.rstrip("/") == coach.get("SUPABASE_URL", "").rstrip("/"):
        print("\n⚠️ C'est l'adresse de ton app de coaching, pas celle de BoxLog. Vérifie le projet.")
        sys.exit(1)
    key = demander("3/3  Clé secrète Supabase de BoxLog", "sb_secret_... ou eyJ...",
                   lambda v: v.startswith(("sb_secret_", "eyJ")) and len(v) > 30, old.get("BOX_SUPABASE_KEY", ""))

    lignes = [
        "# Bot de la salle (BoxLog), lecture seule. Ne partage jamais ce fichier.",
        f"CLAUDE_CODE_OAUTH_TOKEN={coach.get('CLAUDE_CODE_OAUTH_TOKEN', '')}",
        f"AUTH_MODE={coach.get('AUTH_MODE', 'abonnement')}",
        f"ANTHROPIC_API_KEY={coach.get('ANTHROPIC_API_KEY', '')}",
        f"TELEGRAM_BOT_TOKEN={token}",
        f"ALLOWED_USER_IDS={coach.get('ALLOWED_USER_IDS', '')}",
        f"OWNER_NAME={coach.get('OWNER_NAME', 'Bene')}",
        f"TIMEZONE={coach.get('TIMEZONE', 'Europe/Paris')}",
        "# Modèle du quotidien, et modèle pour /prog (analyse de la programmation)",
        f"MODEL={old.get('MODEL') or coach.get('MODEL', 'claude-haiku-5-5')}",
        f"MODEL_COACH={old.get('MODEL_COACH') or coach.get('MODEL_COACH', '') or 'claude-sonnet-5-5'}",
        "WEB_SEARCH=true",
        f"BOX_SUPABASE_URL={url.rstrip('/')}",
        f"BOX_SUPABASE_KEY={key}",
        "# Si ta base contient plusieurs salles, mets ici l'identifiant de la tienne (sinon laisse vide)",
        f"BOX_ID={old.get('BOX_ID', '')}",
    ]
    BOX.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n✅ Bot de la salle configuré (.env.box).")
    print("Ferme la fenêtre de start.bat et relance-la : les deux bots démarrent ensemble.")
    print("Puis écris /start à ton nouveau bot, et /diag pour vérifier.\n")


if __name__ == "__main__":
    main()
