# DA — Miniatures des Reels

Format 1080×1920. **Tous les textes dans la zone visible de la grille du profil (3:4 : de y = 240 à y = 1680).**
Exemples : `contenu/benfit-reels/miniatures/` · scripts : `contenu/benfit-reels/fabrique-montage/reel-cardio-muscle/thumb_cardio.py` et `thumb_studio.py`.

## Version « naturelle » (par défaut)
- **Photo** : Bene souriant si possible (le demander si les rushs n'en ont pas) ; c'est Bene qui choisit la photo finale.
- Étalonnage léger, comme le Reel.
- **En haut** : question manuscrite (Permanent Marker, marine) sur une **étiquette papier** légèrement inclinée avec scotch, mot-clé souligné au feutre bleu.
- **En bas** : mot-clé géant en Anton blanc bord bleu + **bloc bleu Coda** (« CARDIO » / « = MOINS DE MUSCLE ? »).

## Version « studio » (plus marquée, sans faire « IA »)
- Bene **détouré** (rembg, modèle `u2net_human_seg`), décor remplacé par un fond marine sombre avec brume légère.
- **Contre-jour bleu** `#2E6BFF` autour de la silhouette (comme une vraie lumière derrière lui).
- **Titre géant Anton derrière la tête** (effet profondeur), sous-titre au feutre blanc souligné bleu, « BEN&FIT » discret.

## Version « dark » (demandée le 21 nov. 2026)
- Photo réelle en ambiance low-key : décor presque noir et éteint, Bene détouré (rembg `u2net_human_seg`) gardé lisible, contraste plus dur, forte vignette, ombres à peine marine. Rien d'inventé sur le corps, pas de halo.
- Mêmes textes : titre au feutre blanc souligné bleu en haut, mot-clé Anton + bloc bleu Coda en bas.
- Exemple : `contenu/benfit-reels/miniatures/discipline-dark.jpg` · script : `fabrique-montage/reel-discipline/thumb_dark.py`.

## Refusé
- Visuels très chargés type éclairs, statue géante, flammes, couleurs orange/bleu néon (17 nov. 2026) : « ça fait boomer qui découvre GPT ».
