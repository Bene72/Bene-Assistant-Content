# Fabrique de montage des Reels BEN&FIT

Les scripts qui ont produit le Reel « Les 4 qualités / Si je devais tout recommencer » (nov. 2026).
À réutiliser pour les prochains Reels : même DA, mêmes animations.

## Où sont les fichiers vidéo
- **Rushs** : Release GitHub « rushs » du dépôt Bene72/Bene-site (pour l’instant).
- **Bibliothèque** (GIFs, b-roll, images) : Release GitHub « Bibliothèque » du dépôt Bene72/Bene-site (pour l’instant).
- Les vidéos ne vont jamais dans le code (limite GitHub 100 Mo et site plus lourd).

## Les étapes (dans l'ordre)
1. `transcribe.py` : transcription mot à mot avec horodatage (modèle Parakeet via sherpa-onnx, téléchargé depuis les releases GitHub de k2-fsa/sherpa-onnx).
2. `edl.py` : liste de montage (quelles phrases on garde), coupe des silences, coupes calées sur les mots.
3. `build_base.py` : assemble les coupes, accélère légèrement (×1,08) et applique l'étalonnage solaire.
4. `data.py` : sous-titres (découpage, mots-clés surlignés, corrections d'orthographe).
5. `compose.py` : tout le motion design (accroche en typographie animée, volets de chapitres 01–04, barre de progression, écran partagé, cartes, stickers GIF, carte de fin).
6. `audio.py` : musique et bruitages générés (aucun souci de droits), puis mixage avec ffmpeg (voix prioritaire, -14 LUFS).

## Charte
- Police **Coda ExtraBold** (sous-titres blancs, bords bleus, mots-clés dans un bloc bleu), **Anton** pour les grands chiffres.
- Bleu `#2E6BFF`, marine `#08122F`, blanc.
- Formats à alterner : écran partagé, encart flottant en bas, texte empilé, stickers GIF, cartes.

Les chemins dans les scripts (`/home/claude/...`) sont ceux de l'espace de travail de Claude : à adapter si besoin.
