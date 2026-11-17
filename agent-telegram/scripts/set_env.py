"""Modifie une clé du fichier .env sans toucher au reste (lancé par modifier_cle.bat)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"

CLES = [
    ("TELEGRAM_BOT_TOKEN", "Token du bot Telegram (@BotFather)", "123456789:AA..."),
    ("CLAUDE_CODE_OAUTH_TOKEN", "Jeton de ton abonnement Claude", "sk-ant-oat01-..."),
    ("SUPABASE_SERVICE_KEY", "Clé secrète Supabase (service_role ou sb_secret_)", "sb_secret_... ou eyJ..."),
    ("SUPABASE_URL", "URL du projet Supabase", "https://xxxx.supabase.co"),
    ("CALENDARS", "Agendas iCal (Nom=lien, Nom2=lien2)", "Perso=https://...basic.ics"),
    ("GITHUB_TOKEN", "Token GitHub (optionnel)", "github_pat_..."),
    ("GMAIL_ADDRESS", "Ton adresse Gmail", "prenom.nom@gmail.com"),
    ("GMAIL_APP_PASSWORD", "Mot de passe d'application Google (16 lettres)", "abcd efgh ijkl mnop"),
    ("HA_URL", "Adresse de Home Assistant", "http://homeassistant.local:8123"),
    ("HA_TOKEN", "Jeton longue durée Home Assistant", "eyJ..."),
    ("HA_SATELLITE", "Enceinte par défaut (Home Assistant Voice)", "assist_satellite.home_assistant_voice_xxxx"),
    ("ASSISTANT_NAME", "Nom de ton assistant", "Jarvis"),
    ("VOICE_REPLY", "Quand tu envoies un vocal, réponse en : voix, texte ou les deux", "les deux"),
    ("MODEL", "Modèle (claude-haiku-5-5, claude-sonnet-5-5...)", "claude-haiku-5-5"),
    ("BRIEF_TIME", "Heure du brief du matin (HH:MM)", "07:30"),
    ("BRIEF_FORMAT", "Format du brief : texte, vocal ou les deux", "texte"),
]


def lire() -> list[str]:
    if not ENV.exists():
        print("\nFichier .env introuvable. Lance d'abord install.bat.\n")
        sys.exit(1)
    return ENV.read_text(encoding="utf-8").splitlines()


def valeur_actuelle(lignes: list[str], cle: str) -> str:
    for ligne in lignes:
        if ligne.strip().startswith(cle + "="):
            return ligne.split("=", 1)[1].strip()
    return ""


def masquer(v: str) -> str:
    if not v:
        return "(vide)"
    return v if len(v) <= 12 else f"{v[:6]}…{v[-4:]} ({len(v)} caractères)"


def ecrire(lignes: list[str], cle: str, valeur: str):
    nouvelles, trouve = [], False
    for ligne in lignes:
        if ligne.strip().startswith(cle + "="):
            nouvelles.append(f"{cle}={valeur}")
            trouve = True
        else:
            nouvelles.append(ligne)
    if not trouve:
        nouvelles.append(f"{cle}={valeur}")
    sauvegarde = ENV.parent / ".env.avant"
    sauvegarde.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    ENV.write_text("\n".join(nouvelles) + "\n", encoding="utf-8")
    print(f"\n✅ {cle} enregistré. (copie de l'ancien fichier : {sauvegarde.name})")


def main():
    lignes = lire()
    print("\n=== Modifier une clé de l'agent Ben&Fit ===\n")
    for i, (cle, libelle, _) in enumerate(CLES, 1):
        print(f" {i}. {libelle}\n    actuel : {masquer(valeur_actuelle(lignes, cle))}")
    print("\n 0. Quitter")

    choix = input("\nNuméro de la ligne à modifier : ").strip()
    if not choix.isdigit() or not 1 <= int(choix) <= len(CLES):
        print("Annulé.")
        return
    cle, libelle, exemple = CLES[int(choix) - 1]

    print(f"\n{libelle}\nExemple : {exemple}")
    valeur = input("Colle la nouvelle valeur (clic droit = coller), puis Entrée :\n").strip().strip('"\'')
    if not valeur:
        print("Rien saisi, annulé.")
        return
    if cle == "TELEGRAM_BOT_TOKEN" and ":" not in valeur:
        print("\n⚠️ Ça ne ressemble pas à un token Telegram (il contient « : »). Annulé.")
        return
    if cle == "CLAUDE_CODE_OAUTH_TOKEN" and not valeur.startswith("sk-ant-"):
        print("\n⚠️ Un jeton Claude commence par sk-ant-. Annulé.")
        return
    if cle == "GMAIL_APP_PASSWORD":
        valeur = valeur.replace(" ", "")
        if len(valeur) != 16 or not valeur.isalpha():
            print("\n⚠️ Un mot de passe d'application Google fait 16 lettres. Annulé.")
            return
    if cle == "GMAIL_ADDRESS" and "@" not in valeur:
        print("\n⚠️ Adresse mail invalide. Annulé.")
        return
    if cle == "HA_URL":
        valeur = valeur.rstrip("/")
        if not valeur.startswith(("http://", "https://")):
            print("\n⚠️ L'adresse doit commencer par http:// (ex. http://homeassistant.local:8123). Annulé.")
            return
    if cle == "SUPABASE_URL" and not valeur.startswith("http"):
        print("\n⚠️ L'URL doit commencer par https://. Annulé.")
        return
    ecrire(lignes, cle, valeur)
    print("Ferme la fenêtre de start.bat et relance-la pour appliquer.\n")


if __name__ == "__main__":
    main()
