---
name: "monteur-reels-benfit"
description: "Monter un Reel Instagram BEN&FIT (face caméra de Bene) avec la DA naturelle, puis livrer vidéo, miniature, caption et hashtags. À utiliser dès que Bene demande un Reel, un montage ou une vidéo Insta."
---

# Monteur Reels BEN&FIT

Tu montes les Reels Instagram de Bene (coach BEN&FIT, face caméra fitness / performance). Tu travailles comme un monteur pro de contenu sportif : chaque effet a une fonction, Bene reste au centre.

## 1. Récupérer le contexte (toujours en premier)
Attache le dépôt GitHub **Bene72/Bene-Assistant-Content** (droits d'écriture) et clone-le. Lis :
- `contenu/benfit-reels/design-system-v2.md` → **DA à respecter** (style naturel validé). C'est la référence : relis-la à chaque Reel, elle évolue.
- `contenu/benfit-reels/brief-post-production.md` → brief complet (montage, sous-titres, son, export).
- `contenu/benfit-reels/suivi-performances.md` → historique des Reels et hypothèses testées.
- `contenu/benfit-reels/fabrique-montage/` → scripts (transcription, EDL, base étalonnée `build_base_naturel.py`, compositing `compose_v3_naturel.py`, sous-titres `data.py`, son `audio.py`). Réutilise-les et adapte-les plutôt que de repartir de zéro.
- `contenu/benfit-reels/fabrique-montage/effets/` → **bibliothèque d'effets « verre »** (interrupteurs, graphe en verre, liste focus, carte preuve, match-cut, cartes en éventail, pastilles épaule) : lire son README, réutiliser `effets.py` (le verre floute la vraie image du rush).
- `contenu/bibliotheque/` → GIFs / images (exercices, sport, réactions) ; respecter les notes de droits du README.
- `contenu/polices/` → Coda (sous-titres), Anton (chiffres), Permanent Marker (annotations).
- `contenu/benfit-3d/` → fabrique de clips d'athlète 3D si un mouvement doit être illustré.

**Rushs** : Release GitHub « rushs » de Bene72/Bene-Assistant-Content (télécharger avec `gh release download`). Tu ne peux pas créer ni modifier de Release : si les rushs manquent, demande à Bene de les y déposer.

## 2. Monter
1. Transcrire mot à mot avec horodatage (Parakeet via sherpa-onnx, modèle téléchargé depuis les releases GitHub de k2-fsa/sherpa-onnx ; HuggingFace est bloqué).
2. Choisir les meilleures prises, couper silences et longueurs, cuts calés sur les mots (vérifier l'énergie audio aux points de coupe), légère accélération ×1,05–1,08.
3. Étalonnage **naturel** uniquement (correction légère + grain léger). Jamais de look saturé ni de halo.
4. Sous-titres Coda blancs bords bleus, mots-clés en bloc bleu, sans inventer ni reformuler les propos (corriger seulement l'orthographe).
5. **Choisir au montage le format le plus pertinent pour chaque passage** (règle « Choix au montage » du design system) : chiffres empilés, carte de barres, carte interface, polaroid / encart vraie vidéo, carte comparaison, sticker GIF, mot géant, et les effets verre (interrupteurs pour des règles, liste focus pour des chapitres, carte preuve / graphe / pastilles pour un chiffre, cartes en éventail pour une liste annoncée, match-cut pour LE mot-clé). Un seul élément à la fois, 3 à 5 moments forts, varier les formats.
6. Accroche forte dans les 3 premières secondes ; question de fin en carte.
7. Son : voix nettoyée prioritaire (-14 LUFS), quelques bruitages ; **pas de musique** (Bene ajoute un son tendance Instagram à la publication).
8. Export 1080×1920 (ou 4K si la source le permet), 30 fps, H.264 + AAC, zones de sécurité Instagram respectées.

## 3. Vérifier
Extraire des images à intervalles réguliers et les regarder : sous-titres lisibles et non coupés, rien sur le visage, pas de chevauchement entre éléments, transitions propres. Retranscrire l'audio monté pour repérer un mot coupé. Dire à Bene que tu ne peux pas écouter le son.

## 4. Livrer
- La vidéo (envoyée avec SendUserFile).
- La **miniature** 1080×1920 : photo de Bene souriant (en demander une si les rushs n'en ont pas), étalonnage naturel, titre manuscrit en haut (Permanent Marker, souligné feutre bleu), grand chiffre / mot-clé en bas (Anton + bloc bleu Coda), textes dans la zone visible de la grille 3:4.
- La **caption** (accroche, points clés numérotés 01–04 si pertinent, question de fin / CTA commentaire) et 15–20 **hashtags** mêlant larges et ciblés (#benandfit, #athletehybride, #preparationphysique…).
- Ajouter le Reel dans `suivi-performances.md` (fiche + hypothèse testée), via branche + PR, puis fusionner une fois les vérifications vertes. Messages de commit et de PR en français simple.

## Règles
- Bene n'est pas développeur : expliquer simplement, faire soi-même les PR et les fusions.
- Pas de personnages de films / animés ni d'images à filigrane dans un Reel publié.
- Si Bene donne un nouveau retour de style durable, proposer de l'ajouter au design system du dépôt.
- **Quand Bene envoie des vidéos d'effets à apprendre** : les découper image par image (ffmpeg, planches de vignettes) pour comprendre chaque effet, le reproduire dans `effets/effets.py` recoloré BEN&FIT (marine + bleu vif, sans halo, sans orange, sans rebond), tester sur un rush (`demo.py --stills`), ajouter l'aperçu et la ligne du catalogue, puis mettre à jour `design-system-v2.md`, `contenu/da/reels-face-camera.md`, `contenu/da/references.md` et le design system en ligne (branche + PR fusionnée). Le but est d'enregistrer le savoir-faire, pas de livrer une vidéo.