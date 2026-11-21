# Reel « Discipline » (20 nov. 2026)

Format **court, très sport** (15 s, v2 ; v1 de 8 s jugée « un poil courte » par Bene) : phrase face caméra → montage d'entraînement → chute « Discipline is everything. »
Demande de Bene : **montage seulement**. Couleurs d'origine (aucun étalonnage, aucun grain), pas d'effets à part les sous-titres.

- `build_discipline.py` : tout le Reel (`edl` → `stills` pour contrôler → `video`).
  - Déroulé dans `SEQUENCE` : morceaux de voix (plusieurs prises parlées possibles) et plans sans voix. Morceaux de voix choisis à la main, coupes recalées sur le point le plus calme (±60 ms), accélération ×1,05.
  - Plans de coupe posés **sur la voix** (`PLANS`) : squat sur « le taf », sled sur « il est là », vélo sur la fin de phrase ; puis montage sans voix (squat complet, sled, vélo, fentes, 2 snatchs) pour le son tendance ajouté à la publication, et chute face à l'objectif : « Discipline is everything. » (prise du squat, 104034 à 6,2 s).
  - Punch-ins : accroche serrée qui se relâche, punch-in sec sur « discipline », zooms de recadrage sur les plans de coupe.
  - **Couleurs** : lecture et export en matrice BT.709 plage TV (sinon ffmpeg passe par BT.601 et décale les teintes).
  - Son : voix seule, une seule chaîne (coupe-bas, débruitage léger nr 8, compresseur doux), -14 LUFS mesuré sur la partie parlée. Le son des plans de coupe n'est pas utilisé (musique de la salle).
  - Sous-titres : texte tapé à la main dans `SOUS_TITRES` (son trop essoufflé pour la reconnaissance vocale seule : Parakeet + Whisper medium recoupés).
- `thumb_discipline.py` : miniature (« Pas de motivation ? » au feutre, DISCIPLINE en Anton, bloc bleu « le taf, il est là. »).

Rushs : Release « rushs », VID_20261120_103837 (face caméra), 104034 (squat + « Discipline is everything »), 105756 (fentes), 110507 (sled), 112023 et 112113 (vélo), 112308 et 112349 (snatch).

Retour de Bene : 8 s, c'est trop court ; viser ~15 s en ajoutant des plans.


## Version courte (8 s) et son moins traité (21 nov.)
- `VERSION=court python build_discipline.py edl` puis `VERSION=court python build_discipline.py video` → version 8 s (phrase face caméra, fentes, snatch), que Bene préfère publier.
- Retour de Bene : voix « un peu moins isolée », traitement réduit de 20 % (`VOIX_FILTRE`) : coupe-bas 80 → 65 Hz, débruitage nr 8 → 6,4, présence +1,5 → +1,2 dB, compresseur 2,5:1 → 2:1. Toujours une seule chaîne.
