# BEN&FIT — athlète 3D animé

Fabrique un clip 9:16 où un athlète 3D aux couleurs BEN&FIT refait un mouvement
filmé (arraché, épaulé-jeté, squat…), sans outil payant.

**Référence de qualité minimale : `exemples/arrache/reference_v2.mp4`.**
Toute nouvelle animation doit être au moins à ce niveau.

## Le style validé

- Athlète au corps humain réaliste, noir mat, sans cheveux.
- Débardeur et short bleu marine BEN&FIT (#0a206b), ceinture blanche, chaussures blanches.
- Barre aux disques bleu marine et blancs, **posée au sol au départ**, mains fermées sur la barre.
- Plateforme d'haltéro bois et caoutchouc, liseré bleu lumineux, studio sombre, caméra fixe de trois quarts.
- Clip de 12 s, à mettre en boucle :
  1. le mouvement à vitesse réelle, **sans texte** (pour couper au montage) ;
  2. le même mouvement au ralenti (×2) avec arrêts sur image, titre en haut,
     phases numérotées dans un bloc bleu marine et une consigne technique en dessous (police Coda).

## Fabrication, étape par étape

1. `bash contenu/benfit-3d/setup.sh` — installe tout et prépare le corps 3D.
2. Vidéo source : un seul mouvement, une seule personne, entière dans le cadre, caméra fixe.
3. Détection du mouvement :
   `mp311/bin/python -I scripts/pose.py video.mp4 work/pose.json`
4. Nettoyage, en gardant une répétition (image de début, image de fin, images figées à la fin) :
   `mp311/bin/python -I scripts/prep.py work/pose.json work/track.json 0 114 18`
   puis `mp311/bin/python -I scripts/prep2.py work/track.json work/sig.json`
5. Rendu des images (environ 11 s par image, sans carte graphique) :
   - vitesse réelle : `python3 scripts/rig.py out=work/frames2/f_ frames=1-115`
   - images intermédiaires pour le ralenti : `python3 scripts/rig.py out=work/frames2/h_ frames=19-114 sub=0.5`
   - test rapide : ajouter `res=560 frames=1,40,72` (et `cam=side` pour une vue de profil).
6. Montage : `FR=/home/claude/work/frames2 python3 scripts/compose12.py work/out/clip.mp4`

## À adapter pour un nouveau mouvement

- `compose12.py` : titre, phases, consignes, et images figées (`FREEZE`).
- `rig.py` (pensé pour l'arraché) :
  - `GRIP_HW` : largeur de prise (plus serrée pour l'épaulé-jeté) ;
  - `bar_target` et `solve` : trajet de la barre ; il faudra ajouter la réception en front rack ;
  - `feet` : réception en saut avec écartement ; le jeté en fente demande une autre logique.

## Fichiers

- `scripts/pose.py` : détection des 33 points du corps (MediaPipe).
- `scripts/prep.py`, `scripts/prep2.py` : nettoyage et adaptation du mouvement au personnage.
- `scripts/parse_mh.py` : prépare le corps MakeHuman (licence CC0).
- `scripts/rig.py` : personnage, squelette, barre, décor, éclairage, rendu (Blender).
- `scripts/compose12.py` : montage 12 s et textes.
- `exemples/arrache/` : données de l'arraché et clip de référence.
