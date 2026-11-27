# CLAUDE.md — le « deuxième cerveau » de Bene (BEN&FIT)

> Lu automatiquement quand ce dépôt est attaché. **Page d'accueil courte** : elle dit qui est Bene, les règles fixes,
> et **quel fichier lire pour chaque tâche**. Ne lis que la fiche utile (économie de tokens), pas tout le dépôt.
> Dernière mise à jour : 24 nov. 2026 (soir).

## 1. Qui est Bene
- Coach dans une salle CrossFit / HYROX et créateur de **BEN&FIT** (coaching individuel hybride, « Become an Athlete / The Hybrid Athlete System » : BUILD force · RUN endurance · PERFORM performance · MOVE mobilité).
- Cible : **athlètes confirmés** (HYROX, CrossFit, hybrides), pas les débutants.
- Il fait tout seul : coaching, contenu Instagram, apps (dashboard coach, BoxLog), agent Telegram.
- **Pas développeur** (néophyte GitHub) : expliquer simplement, en français, sans jargon. **Faire soi-même branches, PR et fusions** (il le demande sur tous ses dépôts). Messages de commit/PR en français simple.
- Lit souvent sur **mobile** : réponses courtes, l'essentiel d'abord.
- Objectif Instagram : **10 000 vues par vidéo**.

## 2. Règles qui valent partout
0. **Reels de séance : monter comme Bene** (réf. 27 nov., `contenu/da/reels-entrainement.md`) : plans longs à vitesse réelle, répétitions entières, coupes franches entre les reps, **pas de ralentis en rampe, zooms animés, flashs ni flous** ; les effets seulement sur 1–2 temps forts. Mieux vaut sobre et net que « monteur qui en fait trop ».
1. **Ne jamais inventer ses propos** : sous-titres = ses mots exacts (orthographe corrigée seulement). Si l'audio est douteux, le dire et demander.
2. **Rendu « créateur humain », pas « IA »** : son audience repère l'IA et décroche. Pas de look saturé, halos, éclairs, statues, dégradés, rebonds partout. Une seule couleur d'accent.
3. **Couleurs BEN&FIT uniquement** : marine `#0A206B`, bleu vif `#2E6BFF`, blanc (+ marine profond `#030A1A`, bleu clair `#8CB8FF` sur marine). Pas d'orange, pas d'autres bleus.
4. **Polices** (`contenu/polices/`) : Coda (sous-titres/textes), Anton (titres/chiffres), Permanent Marker (annotations, avec parcimonie).
5. **Photos de Bene** (« Optimise cette photo ») : plus lumineuse, nette, en relief, **sans rien inventer** (pas d'IA qui ajoute muscles/veines). Script : `contenu/photos/optimise_photo.py`. Exception seulement s'il demande explicitement de « tricher ».
6. **La demande du jour l'emporte** sur les fiches. Quand il valide/refuse un style durablement → mettre à jour la fiche concernée (`contenu/da/…`) + ce fichier, via PR fusionnée.
7. Outils : pas de musique dans les Reels (il ajoute un son tendance sur Insta). **5 hashtags max** (limite Instagram 2026).

## 3. Pour chaque tâche, lire ça (et seulement ça)
| Tâche | Lire d'abord | Base de scripts / outils |
|---|---|---|
| Reel face caméra | `contenu/da/reels-face-camera.md`, `contenu/benfit-reels/design-system-v2.md` | `contenu/benfit-reels/fabrique-montage/` (le plus récent : `reel-zone2-hyrox/build_zone2.py`) + skill `monteur-reels-benfit` |
| Reel d'entraînement / collab | `contenu/da/reels-entrainement.md`, `contenu/benfit-reels/prompt-reel-entrainement.md` | `reel-semaine-entrainement/build_semaine.py` (voix off + montage + ralentis 60 i/s + photo de fin), `reel-seance-apocalypse/build_seance.py` (séance longue ~1 min 20 : chapitres animés, rampes de vitesse, écran partagé ; **pas de barre de progression**, zooms ≤ 1,45×), `reel-apocalypse/` (collab) |
| Montage « montage seulement » (sans effets/étalonnage) | — | `reel-discipline/build_discipline.py` (`SEQUENCE`, `VERSION=court`) |
| Miniature | `contenu/da/miniatures.md` | `thumb_*.py` dans chaque dossier de Reel (naturelle, studio, **dark** = `reel-discipline/thumb_dark.py`) ; exemples `contenu/benfit-reels/miniatures/` |
| Carrousel | `contenu/da/carrousels-storytelling.md` ou `carrousels-briefing.md`, `publications-instagram.md` | export **carré 1080×1080, PNG légers, pas de 2x** |
| Reel « effets gestes » (carrousel au doigt, claquement, mur au clap, tornade multivers) — **format adoré** | `contenu/da/reels-effets-gestes.md` (style, tournage, idées), `fabrique-montage/reel-canape/README.md` | `reel-canape/build_canape.py` (flux optique + son, détourage rembg) |
| Effets à apprendre (il envoie des Reels d'autres créateurs) ; lot « modèles CapCut » (zoom flou, RVB, éclats, cadres, fond noir, écho, clones, texte écho, titre dans le décor, mosaïque) | `fabrique-montage/effets/README.md` | `effets/effets.py` ; but = enregistrer le savoir-faire, pas livrer une vidéo |
| Clip 3D d'athlète | `contenu/da/animations-3d.md` | `contenu/benfit-3d/` (référence : arraché v2) |
| Plan de contenu / audit profil / analyse concurrents | `contenu/methodes-claude/*.md` | skills du même nom |
| Suivi des Reels (stats, hypothèses) | `contenu/benfit-reels/suivi-performances.md` | ajouter une fiche à chaque Reel livré |
| Logos (BEN&FIT, Apocalypse) / intro logo animée | `contenu/logos/README.md` | `fabrique-montage/logo-anim/logo_anim.py` (5 s style clip de rap, sorties .mov transparent / .webm / fond vert) |
| Inspirations | `contenu/da/references.md` | |
| Hors BEN&FIT (Twin's League / Ultimate League) | `contenu/da/autres-marques.md` | |
| Agent Telegram | `agent-telegram/README.md` | prompts coach (« Kairo ») et programmation dans `agent-telegram/agent/prompts/` |

## 4. Reels : règles fixes (déjà validées, ne pas redemander)
- **Rushs** : Release GitHub « rushs » de ce dépôt (ou une Release par séance `rushs-AAAA-MM-JJ-sujet` si Bene les a rangées). **Index : `contenu/benfit-reels/rushs-index.md`** (quelle vidéo = quelle séance) → le tenir à jour à chaque nouveau lot. Claude ne peut pas créer / modifier / supprimer de Release. Prendre **les plus récents** (trier par date). Téléchargement fiable :
  `gh api -H "Accept: application/octet-stream" repos/Bene72/Bene-Assistant-Content/releases/assets/<id> > fichier` (`gh release download` peut être bloqué). Ids : `gh api repos/Bene72/Bene-Assistant-Content/releases/tags/rushs -q '.assets[]|[.id,.name,.created_at]|@tsv'`.
- **Transcription** : Parakeet (sherpa-onnx) — modèle `sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8` depuis les releases GitHub `k2-fsa/sherpa-onnx` (asr-models) ; si son difficile, recouper avec `sherpa-onnx-whisper-medium` (même endroit). HuggingFace est bloqué. `fabrique-montage/transcribe.py`.
- **Montage** : coupes sèches calées sur les mots (couper au point le plus calme ±60 ms), punch-ins rythmés, recadrage si mal centré, accélération ×1,05.
- **Couleurs** : style « naturel » (étalonnage léger) par défaut ; s'il dit « ne touche pas à la colorimétrie » → couleurs d'origine, aucun grain. Toujours lire/écrire en **BT.709** (`in_color_matrix=bt709` / `out_color_matrix=bt709` + tags), sinon ffmpeg décale les teintes.
- **Sous-titres** : Coda blanc, bords bleus, mots-clés dans un bloc bleu `#2E6BFF` ; ligne ≤ 920 px (réduire la police sinon) ; jamais sur le visage.
- **Son** : voix légèrement nettoyée, **une seule chaîne** (jamais voix nettoyée + voix d'origine mélangées = écho métallique). Il veut la voix **« moins isolée »** : réglage validé le 21 nov. = coupe-bas 65 Hz, `afftdn nr=6.4`, présence +1,2 dB, compresseur 2:1. **-14 LUFS** mesuré sur la voix ; mono → stéréo à **-3 dB** (sinon +3 LU). Pas de musique ; le son des plans de salle contient souvent la musique de la salle → le couper ou le baisser.
- **Export** : 1080×1920, 30 i/s, H.264 CRF 12 preset slow, AAC 320k, qualité max. Si trop lourd pour l'envoi : 2 fichiers séparés en haute qualité (pas de réencodage pour réduire).
- **Vérifier** : planches d'images (cadrage, sous-titres), retranscrire l'audio monté (mot coupé ?), mesurer les LUFS. Dire qu'on ne peut pas écouter.
- **Livrer** : vidéo + miniature + caption (accroche, points, question de fin) + **5 hashtags** ; fiche dans `suivi-performances.md` ; script dans `fabrique-montage/reel-<sujet>/` via PR fusionnée.
- **Durée** : court et très sport ; 8 s jugé « un poil court » → viser ~15 s ; Reel d'entraînement < 30 s.
- Ralentis : ses rushs récents sont en 60 i/s → lire à 0,5 (vraies images).
- Upscale 4K : pas de GPU ici (Real-ESRGAN ≈ 30 s/image). Rendu validé en test : 50 % IA / 50 % image réelle. Pour une vidéo entière, conseiller Topaz / CapCut.

## 5. Ce qui a déjà été fait (Reels)
#1 Fort ≠ en forme (trop « IA ») · #2 Zone 2 · #3 Tractions · #4 Les 4 qualités (adoré : motion design + GIFs) · #5 Cardio et muscle (`reel-cardio-muscle/`) · #6 Collab Apocalypse Training (`reel-apocalypse/`) · #7 Zone 2 / HYROX (`reel-zone2-hyrox/`) · #8 Discipline (`reel-discipline/`, versions 8 s et 15 s) · #9 Acteur principal, Reel d'entraînement (`reel-semaine-entrainement/`) · #10 Canapé, effets gestes (`reel-canape/`, **adoré** : format à développer et à décliner, voir `contenu/da/reels-effets-gestes.md`) · #11 Séance à deux × Apocalypse (`reel-seance-apocalypse/`, 78 s, pas de sous-titres).
Idées en attente : verre d'eau infini (effet), « Pourquoi tu finis tes WOD explosé ? » (pacing), « a day in the life » de coach, clip 3D épaulé-jeté.

## 6. Ses autres projets (dépôts séparés — ne pas mélanger)
| Projet | Où | À savoir |
|---|---|---|
| Dashboard coach BEN&FIT | `Bene72/Ben-Fit` (Next.js + Supabase, ben-and-fit.vercel.app/coach) | Ne **jamais** perdre de données client. Cycles de 5 semaines, alertes J-14/J-7, bilans hebdo vendredi→lundi, dates d'engagement saisies à la main, une seule fiche client concise. |
| BoxLog (prog de sa salle) | `Bene72/Track-your-progress` | App seulement ; Claude pousse et fusionne lui-même. Vente prévue plus tard (une box par acheteur). |
| Site BEN&FIT | `Bene72/Bene-site` (Vercel) | Le site seulement, aucun contenu de création. |
| Agent Telegram « Ben&Fit Agent » | `agent-telegram/` ici | Sur son PC Windows (Raspberry Pi plus tard), abonnement Claude (0 € en plus). Brief quotidien (texte ou vocal), bilans clients, programmation (WOD/EMOM/AMRAP bien distincts), chronique philo « Chroniques de la pensée », infos bourse (PEA ETF). Projet « Jarvis » : domotique, Gmail (envoi seulement après accord). |
| Offre de coaching | — | 120 €/mois avec diète, 88 € sans ; 12 semaines en 2 paiements ; problème n°1 : 80 % partent à 3–6 mois. |
| Séances de Pilates (PDF) | — | Même format que la séance 3 ; ≥ 3 nouveaux exercices à chaque séance ; environ toutes les 2 semaines (séance 6 le 23 nov.). |
| Autres | — | Livres nutrition BEN&FIT (30 jours, 50 recettes, 2000/2500 kcal) ; Twin's League / Ultimate League (FIFA 2v2 à Tours, DA rétro 90-2000) ; Ultimate Shop (fidélité FC27 au Délirium) ; manga « Afterimage » ; outil neurotype (Thibaudeau). |

## 7. Garder ce fichier à jour
- À la fin d'une création ou quand Bene donne une règle durable : mettre à jour **la fiche détaillée** + la ligne utile ici (court !), via PR fusionnée.
- Ce fichier doit rester **court** (une page d'accueil) : les détails vont dans `contenu/da/` et les README des dossiers.
