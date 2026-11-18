# DA — Reels face caméra (v2 « naturelle »)

**Référence complète : [`contenu/benfit-reels/design-system-v2.md`](../benfit-reels/design-system-v2.md)** (validée le 16 nov. 2026).
Méthode de montage : `contenu/methodes-claude/monteur-reels-benfit.md` · scripts : `contenu/benfit-reels/fabrique-montage/` (modèle le plus récent : `reel-cardio-muscle/`).

## L'essentiel
- **Étalonnage naturel** : correction légère + grain léger. Jamais saturé, jamais de halo.
- **Sous-titres** : Coda ExtraBold blanc, bords bleus, mots-clés dans un bloc `#2E6BFF`, 2 lignes max, calés au mot. On ne reformule jamais ce que dit Bene (seulement l'orthographe).
- **Accroche** en typographie animée dans les 3 premières secondes. **Carte de fin** : question + CTA commentaire.
- **3 à 5 moments graphiques forts**, un seul élément à l'écran à la fois, en variant les formats.
- **Son** : voix -14 LUFS, quelques bruitages, **pas de musique** (Bene ajoute un son tendance dans Edits : instrumental calme, volume 10-15 %).
- **Export** : 1080×1920, 30 fps, H.264 + AAC, qualité max. > 400 Mo → envoyer en 2 morceaux (`split`), sans réencoder, + commande cmd `copy /b fichier.part1 + fichier.part2 fichier.mp4`.

## Formats d'illustration (choisis au montage, passage par passage)
| Moment du discours | Format |
|---|---|
| chiffre, progression | chiffres empilés (Anton) ou **carte de barres bleues** (Bene l'adore) |
| méthode, planning | **carte interface en verre dépoli** : agenda, checklist qui se coche, fiche de séance |
| mouvement concret | vraie vidéo en encart ou **polaroid** (légende Permanent Marker) |
| comparaison A ≠ B | carte à deux colonnes |
| moment drôle | **sticker GIF** de `contenu/bibliotheque/` (jamais de personnage de film/animé, ni filigrane) |
| phrase forte | **mot géant** (une fois par Reel) ou punch-in |
| changement de partie | tag de chapitre « 02 · LA GESTION » souligné au feutre |

## Validé / aimé
- Reel « 4 qualités » v2 : motion design + GIFs drôles.
- Cartes interface (réf. Théo Parisi, Project Orange), typographie mixte gras + *italique serif*.
- Titre qui s'enflamme puis redevient net (réf. pierre_lesr), encart vidéo flottant sur le buste (réf. amaury.bodin).

## Refusé
- Le tout premier Reel (« Tu peux être fort… ») : trop « IA ».
- Look coloré/solaire poussé de la v1, volets bleus plein écran, jauges, barres de progression, écrans partagés type tableau de bord.
- Sous-titres jaunes (ressortent mal sur le t-shirt vert).
