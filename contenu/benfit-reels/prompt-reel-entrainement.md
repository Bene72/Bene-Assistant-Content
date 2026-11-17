# Prompt — Reel d'entraînement (bloc test Apocalypse Training)

À coller dans une nouvelle discussion Claude, avec les deux logos en pièces jointes. Remplacer ce qui est entre [crochets].

```
Nouveau Reel Instagram BEN&FIT à monter : un REEL D'ENTRAÎNEMENT (pas une vidéo explicative face caméra).

Contexte : j'ai suivi le « bloc test » de programmation de mon ami [Prénom / compte Insta de l'ami]. Le Reel montre mes séances de ce bloc. C'est une collaboration : je t'envoie mon logo BEN&FIT et le sien (en pièces jointes).

1. Récupère dans mon dépôt GitHub Bene72/Bene-Assistant-Content :
   - contenu/benfit-reels/design-system-v2.md → DA naturelle à respecter (étalonnage léger, pas de look saturé, pas de halo, rendu pas « IA »)
   - contenu/benfit-reels/fabrique-montage/ → scripts réutilisables (build_base_naturel.py pour l'étalonnage, reel-cardio-muscle/compose_cardio.py comme modèle de compositing)
   - contenu/polices/ → Anton (titres, chiffres), Coda (textes), Permanent Marker (annotations)
   - contenu/benfit-reels/suivi-performances.md → ajoute ce Reel (fiche + hypothèse testée), via branche + PR que tu fusionnes toi-même
2. Mes rushs sont dans la Release « rushs » du même dépôt (télécharge-les via l'API GitHub si « gh release download » ne marche pas).

Montage attendu : dynamique et sportif
- Pas de transcription ni de sous-titres de parole (sauf si je parle face caméra dans un rush : dans ce cas, sous-titres Coda blancs bords bleus).
- Choisis les meilleurs moments de chaque rush : répétitions propres, moments d'effort, fins de série, réactions. Coupe les temps morts (installation, repos, marche).
- Plans courts (0,5 à 2 s), rythme soutenu, quelques variations de vitesse : ralenti sur un mouvement clé ou la fin d'une rep difficile, léger accéléré sur les transitions. Punch-in / zooms rapides pour l'énergie, sans effets gadgets.
- Garde le son ambiant des rushs (barre, impacts, souffle) en fond, nettoyé et équilibré, à -14 LUFS. PAS de musique : j'ajoute un son tendance dans Edits. Ajoute seulement quelques whooshs / impacts discrets sur les transitions.
- Accroche forte dans les 2 premières secondes : le plan le plus impressionnant + un titre court en Anton, par ex. « J'AI TESTÉ LE BLOC DE [AMI] ».
- Textes à l'écran, courts : nom de l'exercice + charge / reps en chips bleus (#2E6BFF), par ex. « BACK SQUAT · 5×3 · [xx] kg ». Infos du bloc : [liste des séances / exercices / charges].
- Logos : co-branding sobre « BEN&FIT × [AMI] » avec les deux logos en intro (moins de 1 s) et sur la carte de fin. Discret le reste du temps (petit, coin haut, opacité réduite), jamais sur un mouvement.
- Carte de fin : « Tu veux tester ce bloc ? » + CTA commentaire / abonnement + mention de [@compte de l'ami].
- Durée cible : 20 à 35 s. Format 1080×1920, 30 fps, H.264 + AAC, zones de sécurité Instagram respectées.

Vérifie avant de livrer : extrais des images à intervalles réguliers et regarde-les (textes lisibles, rien sur le visage ni sur le mouvement, logos propres). Tu ne peux pas écouter le son : dis-le-moi.

Livre :
- la vidéo. Si elle dépasse 400 Mo, envoie-la en 2 morceaux avec « split » (part1 / part2), sans réencoder, et rappelle-moi la commande cmd « copy /b fichier.part1 + fichier.part2 fichier.mp4 » avec les noms exacts ;
- la miniature 1080×1920 (plan d'effort fort, titre Anton + chip bleu, textes dans la zone visible de la grille 3:4) ;
- la caption (accroche, contenu du bloc, mention de [@ami], question / CTA) et 15 à 20 hashtags (#benandfit, #athletehybride, #preparationphysique…).
```

Astuce : ajouter au message la liste de ce qui a été filmé (« squat, tractions, rameur, metcon final… »).
