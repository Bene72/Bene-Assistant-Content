# Reel « Discipline » (20 nov. 2026)

Format **très court, très sport** (8 s) : une phrase face caméra + plans d'entraînement.
Demande de Bene : **montage seulement**. Couleurs d'origine (aucun étalonnage, aucun grain), pas d'effets à part les sous-titres.

- `build_discipline.py` : tout le Reel (`edl` → `stills` pour contrôler → `video`).
  - Morceaux de voix choisis à la main (`VOIX`), coupes recalées sur le point le plus calme (±60 ms), accélération ×1,05.
  - Plans de coupe posés **sur la voix** (`PLANS`) : squat sur « le taf », sled sur « il est là », vélo sur la fin de phrase ; fin sans voix (fentes, snatch) pour le son tendance ajouté à la publication.
  - Punch-ins : accroche serrée qui se relâche, punch-in sec sur « discipline », zooms de recadrage sur les plans de coupe.
  - **Couleurs** : lecture et export en matrice BT.709 plage TV (sinon ffmpeg passe par BT.601 et décale les teintes).
  - Son : voix seule, une seule chaîne (coupe-bas, débruitage léger nr 8, compresseur doux), -14 LUFS mesuré sur la partie parlée. Le son des plans de coupe n'est pas utilisé (musique de la salle).
  - Sous-titres : texte tapé à la main dans `SOUS_TITRES` (son trop essoufflé pour la reconnaissance vocale seule : Parakeet + Whisper medium recoupés).
- `thumb_discipline.py` : miniature (« Pas de motivation ? » au feutre, DISCIPLINE en Anton, bloc bleu « le taf, il est là. »).

Rushs : Release « rushs », VID_20261120_103837 (face caméra), 104034 (squat), 105756 (fentes), 110507 (sled), 112023 (vélo), 112349 (snatch).
