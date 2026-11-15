# Agent Ben&Fit

Ton assistant personnel, propulsé par Claude, à qui tu parles sur Telegram.
Un seul agent, plusieurs compétences :

| Compétence | Ce qu'il fait | À configurer |
|---|---|---|
| Discussion + recherche web | Répond, cherche sur le web, lit des pages | rien |
| Mémoire | Retient ce que tu lui demandes (« retiens que… ») | rien |
| Automatisations | Tâches récurrentes envoyées sur Telegram | rien |
| Coaching | Lit ton dashboard Supabase (athlètes, cycles, workouts). **Lecture seule** | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` |
| Dev | Lit tes repos, crée des issues, propose du code via Pull Request (jamais de push direct sur main) | `GITHUB_TOKEN` |

Les compétences non configurées sont simplement désactivées.

---

## Coût : 0 € en plus

L'agent utilise **ton abonnement Claude** (via Claude Code, inclus dans l'installation). Ce qu'il consomme est pris sur le même quota que tes discussions avec Claude. Si tu atteins la limite, il te le dit et refonctionne quand le quota se recharge.

Usage strictement perso : toi seul lui parles. Si un jour d'autres personnes (athlètes) doivent lui parler, passe en mode clé API (`AUTH_MODE=api` dans `.env`).

## Installation sur Windows (10 minutes)

### 1. Crée ton bot Telegram
1. Dans Telegram, ouvre **@BotFather**, envoie `/newbot`.
2. Choisis un nom (ex. *Ben&Fit Agent*) et un identifiant finissant par `bot`.
3. Garde le token qu'il te donne (`123456:ABC…`).

### 2. Installe
1. Dézippe le dossier où tu veux (ex. `Documents\benfit-agent`).
2. Double-clique sur **`install.bat`**. Il installe Python si besoin, puis les dépendances (quelques minutes, Claude Code pèse ~400 Mo).
   (Si Windows affiche « Windows a protégé votre ordinateur » : *Informations complémentaires* > *Exécuter quand même*.)
3. **Connexion à ton compte Claude** : ton navigateur s'ouvre, connecte-toi et autorise. Un jeton `sk-ant-oat…` s'affiche dans la fenêtre : copie-le et colle-le quand on te le demande (clic droit = coller). Il est enregistré automatiquement.
   (Si ça rate, relance juste `connexion_claude.bat`.)
4. Le Bloc-notes s'ouvre sur `.env` : colle le token Telegram à la ligne `TELEGRAM_BOT_TOKEN=`, enregistre.

### 3. Lance

1. Double-clique sur **`start.bat`**. Une fenêtre noire s'ouvre : l'agent tourne tant qu'elle est ouverte.
2. Dans Telegram, ouvre ton bot et écris `/start`. Il te répond ton **identifiant Telegram**.
3. Colle cet identifiant dans `.env` à la ligne `ALLOWED_USER_IDS=`, enregistre, ferme la fenêtre noire et relance `start.bat`.

C'est prêt. Seul toi peux lui parler.

**Lancement automatique au démarrage de Windows** : double-clique sur `demarrage_auto_windows.bat` (relance-le pour désactiver).

---

## Brief du matin et journal

Chaque jour à 7h30 (réglable avec `BRIEF_TIME` dans `.env`), l'agent t'envoie :
☀️ la date, la fête du jour et les jours fériés · 📅 tes rendez-vous · ✅ tes tâches (en retard, du jour) · 🎂 les anniversaires des 7 prochains jours · 🌍 5 actus · 💬 une phrase d'élan.

Tape `/brief` pour l'avoir tout de suite en texte, `/brief vocal` (ou `/briefvocal`) en note vocale, `/brief les deux` pour les deux. Pour le brief automatique, choisis avec `BRIEF_FORMAT=texte`, `vocal` ou `les deux` dans `.env`. Tu peux aussi demander n'importe quelle réponse « en vocal ».

Pour le remplir, parle-lui normalement :
- « Rappelle-moi d'appeler le comptable jeudi » : ajouté à la to-do
- « C'est fait pour le comptable » : coché
- « L'anniversaire de ma mère c'est le 14 mars 1968 » : enregistré, rappelé chaque année avec son âge
- Le soir : « Journée solide, PR au squat, mais crevé » : il te propose de l'ajouter à ton journal. « Fais-moi le bilan de ma semaine » : il relit ton journal.

### Brancher ton agenda (lecture seule)

**Google Agenda** (sur ordinateur) : calendar.google.com > roue dentée > *Paramètres* > clique sur ton agenda à gauche > section *Intégrer l'agenda* > copie l'**Adresse secrète au format iCal**.
**iPhone / iCloud** : app Calendrier > *Calendriers* > (i) à côté de l'agenda > active *Calendrier public* > partage le lien (remplace `webcal://` par `https://`, l'agent le fait aussi tout seul).
**Outlook** : *Paramètres* > *Calendrier* > *Calendriers partagés* > *Publier un calendrier* > lien ICS.

Colle le ou les liens dans `.env` :
```
CALENDARS=Perso=https://...ics, Pro=https://...ics
```
Garde ces liens secrets : quiconque les a peut lire l'agenda.

## Bilans des athlètes

- `/bilans` : qui a fait son bilan entre vendredi et lundi (scores et signaux à surveiller), et qui ne l'a pas encore fait. Le récap arrive aussi tout seul le lundi à 20h (`BILANS_CRON` dans `.env`).
- « Réponse pour Wissam » / « prépare-moi une réponse pour Léa » : l'agent lit son dernier bilan, le compare aux précédents, regarde ses séances, puis rédige le message prêt à copier-coller, comme si c'était toi.
- « Analyse le bilan de Wissam » : analyse détaillée (faits, hypothèses, priorités).

La posture de coach (ton, règles de rédaction, sécurité) est dans `agent/prompts/coach.md` : tu peux la modifier librement avec le Bloc-notes, puis relancer l'agent.

## Programmation des cycles

- `/cycle Wissam 5 semaines, focus force, ménager le genou` (ou en langage normal) : l'agent relit ta doctrine, lit les bilans, les logs et le programme en cours de l'athlète, construit le cycle, puis t'envoie le récapitulatif complet.
- Rien n'est écrit sans ton `/ok`. Après validation, les séances sont créées en **cycle futur** : l'athlète ne voit rien. Tu relis dans l'app (fiche athlète, onglet Programme, cycle futur) et tu cliques sur **Activer** quand tu veux.
- « Annule le dernier cycle » retire ce brouillon, tant qu'il n'a pas été activé.
- Structures gérées, au format exact de ton app : exercices classiques, Superset, Giant Set, Drop Set, et les Workout Blocks (For Time, RFT, AMRAP, EMOM, Tabata, Death By) avec rounds, durée, repos, objectif et note coach. Les séances peuvent avoir un jour fixe ou être simplement numérotées.
- L'agent ne peut que créer des brouillons : il ne modifie ni ne supprime jamais un programme existant.
- Ta doctrine complète est dans `agent/prompts/programmation.md` (elle reste sur ta machine, pas sur GitHub). Mets `MODEL_COACH=claude-sonnet-5-5` dans `.env` pour des cycles de qualité.

## Ajouter les compétences Coaching et Dev

**Coaching (ton dashboard Ben-Fit)** : l'agent lit directement la base Supabase de l'app ben-and-fit.vercel.app. Récupère les 2 valeurs que l'app utilise déjà :
- Dans **Vercel** > projet > *Settings* > *Environment Variables* : `NEXT_PUBLIC_SUPABASE_URL` va dans `SUPABASE_URL`, et `SUPABASE_SERVICE_ROLE_KEY` va dans `SUPABASE_SERVICE_KEY`.
- Ou dans **Supabase** > *Project Settings* > *API* : *Project URL* et la clé *service_role*.

Ce qu'il sait faire : vue cockpit de tous les athlètes actifs (séances 7/28 j, dernier bilan, fin d'engagement, fin de cycle, messages non lus, tâches coach) avec les points d'attention, et fiche complète d'un athlète (bilans, programme, logs, mesures, objectifs, nutrition, messages). Les points d'attention apparaissent aussi dans le brief du matin.

⚠️ Ton repo Ben-Fit est public : ne mets jamais la clé service_role dans le code, seulement dans ce `.env`.

L'agent ne peut que **lire** : aucune fonction d'écriture ou de suppression n'existe dans son code.

**Dev (GitHub)** : github.com > *Settings* > *Developer settings* > *Personal access tokens* > *Fine-grained tokens* > *Generate new token* :
- *Repository access* : les repos que tu veux lui confier
- *Permissions* : **Contents**, **Issues**, **Pull requests** en *Read and write*
- Colle le token dans `GITHUB_TOKEN`

Relance `start.bat` après chaque modification du `.env`.

---

## Exemples de demandes

- « Qu'est-ce que j'ai à faire côté clients cette semaine ? »
- « Analyse le dernier bilan de Wissam et dis-moi quoi ajuster dans sa prog »
- « Qui ne s'est pas entraîné depuis une semaine ? »
- « Regarde le README de Ben-Fit : quelles migrations restent à appliquer ? »
- « Chaque lundi à 8h, envoie-moi les cycles qui se terminent dans 14 jours et les engagements qui expirent ce mois-ci »
- « Tous les jours à 7h30, une veille de 5 actus sur la préparation physique et l'haltérophilie »
- « Dans Ben-Fit, regarde pourquoi le panneau Prochains suivis est vide et ouvre une issue »
- « Propose une PR qui corrige la faute de frappe dans le README de Track-your-progress »
- « Retiens que Wissam a une compétition le 12 décembre »

Commandes : `/brief` (brief du jour), `/bilans` (bilans du week-end), `/reponse Prénom`, `/cycle Prénom`, `/diag`, `/ok` et `/non`, `/taches` (tâches planifiées), `/reset` (effacer la conversation), `/id`.

---

## Passer sur Raspberry Pi

1. Pi 5 (8 Go) avec Raspberry Pi OS 64 bits, connecté à Internet.
2. Copie le dossier sur le Pi (clé USB ou `scp`), **avec ton fichier `.env` et le dossier `data/`** (mémoire et tâches). Le `.env` contient déjà ta connexion Claude : rien à refaire.
3. Dans un terminal sur le Pi :
   ```bash
   cd benfit-agent
   bash scripts/install_pi.sh
   ```
4. Arrête l'agent sur ton PC (sinon deux agents se disputeront le même bot).

Il tourne ensuite 24/7 et redémarre tout seul. Logs : `journalctl -u benfit-agent -f`.

---

## Structure

```
agent/
  main.py        bot Telegram
  brain.py       consignes de l'agent + mode clé API
  brain_sdk.py   mode abonnement (Claude Code)
  scheduler.py   tâches récurrentes
  storage.py     base SQLite (data/agent.db)
  tools/         une compétence = un fichier
    coaching.py  Supabase (lecture seule)
    github.py    GitHub
    web.py       lecture de pages
    notes.py     mémoire
    schedule.py  automatisations
```

Pour ajouter une compétence : crée un fichier dans `agent/tools/`, décore une fonction avec `@tool(...)`, et ajoute l'import en bas de `agent/tools/__init__.py`.

## Changer une clé plus tard

Double-clique sur **`modifier_cle.bat`** : il affiche la liste des clés (Telegram, Claude, Supabase, agenda, modèle, heure du brief…), tu choisis un numéro, tu colles la nouvelle valeur. Le reste du fichier `.env` n'est pas touché et une copie de l'ancien est gardée dans `.env.avant`. Relance `start.bat` ensuite.

## Sécurité

- Ne partage jamais le fichier `.env`. Seul ton identifiant Telegram est servi, et seulement en conversation privée.
- Données clients : lecture seule, à une exception près : créer un cycle en brouillon après ton `/ok`. L'agent ne peut interroger que des tables de ton dashboard, rien d'autre dans Supabase.
- Tout ce qui écrit à l'extérieur (issue ou Pull Request GitHub) attend ta confirmation : l'agent t'envoie un résumé exact, tu réponds `/ok` ou `/non`.
- Les textes venant d'ailleurs (bilans, pages web, agenda) sont traités comme des données, jamais comme des ordres. Dans un message où des données clients ont été lues, l'agent ne peut plus ouvrir de page web ni envoyer de vocal : rien ne peut sortir par ce biais.
- La lecture de pages web refuse les adresses locales (ta box, ton PC).
- La voix passe par un service Microsoft externe : par défaut, aucun texte contenant des données clients n'y est envoyé (`TTS_CLIENT_DATA`).
- Sauvegarde : une copie quotidienne de `data/agent.db` (journal, to-do, notes) dans `data/backups`, 7 jours gardés.
- `/diag` vérifie toutes les connexions sans consommer ton quota.
- Si le PC était éteint à 7h30, le brief part au démarrage (jusqu'à midi, réglable avec `BRIEF_CATCHUP_UNTIL`).
