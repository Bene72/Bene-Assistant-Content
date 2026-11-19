# Bibliothèque d'effets « verre » BEN&FIT

Effets de motion design réutilisables pour les Reels (1080×1920, 30 fps), ajoutés le 19 nov. 2026.
Inspiration : les effets « Liquid Glass » de **corbinsylk** (Instagram) envoyés par Bene, **adaptés à la charte** :
marine `#0A206B` + bleu vif `#2E6BFF` + blanc, pas d'orange, pas de halo ni de lueur, entrées sans rebond.

Aperçus : dossier `apercus/` (une image par effet). Démo vidéo complète : `python demo.py RUSH.mp4`.

## Utilisation
```python
import sys; sys.path.insert(0, "contenu/benfit-reels/fabrique-montage/effets")
import effets as E

cv = E.Canvas(frame)          # frame = image du Reel, numpy uint8 (1920, 1080, 3)
E.fx_toggles(cv, t - debut)   # t - debut = temps écoulé depuis le début de l'effet (s)
frame = cv.out()
```
Chaque effet gère lui-même son entrée et sa sortie (fondu + glissé court) sur sa durée `dur`.
Les textes sont des paramètres : toujours les réécrire avec les mots du Reel.
Le verre floute **la vraie image derrière** (`Canvas.glass`) : ça marche sur n'importe quel rush.

Prérequis : `pip install pycairo numpy pillow`, ffmpeg, polices de `contenu/polices/` installées
(Coda, Anton, Permanent Marker, **Instrument Serif** pour l'italique des titres mixtes).

## Catalogue

| Effet | Fonction | Quand l'utiliser | Durée | Place |
|---|---|---|---|---|
| Interrupteurs | `fx_toggles(rows=…)` | checklist, règles, étapes à suivre (« 3 règles ») : chaque toggle s'allume quand Bene dit la règle | 4,6 s | bas du buste (y≈1240) |
| Graphe en verre | `fx_graphe(label, start, end, pts)` | une progression ou un résultat chiffré qui monte (allure, %, charge) | 5 s | bas du buste |
| Liste focus | `fx_focus(items, step, note)` | Reel en chapitres : l'étape en cours nette, les autres floues, « tu es ici » au feutre (ex. les 4 piliers) | 5,6 s (≈1 s par étape) | centre bas |
| Carte preuve | `fx_preuve(label, value, unit, sub, note)` | un résultat client ou perso : gros chiffre qui compte + souligné feutre + annotation | 4,8 s | bas du buste |
| Match-cut | `fx_matchcut(word)` | phrase forte / mot-clé : des pages de texte défilent en coupe sèche, le mot reste fixe au centre | 2,8 s | plein écran (insert) |
| Cartes en éventail | `fx_eventail(cards, hero)` | annoncer une liste (« 3 erreurs ») puis zoomer sur celle dont on parle | 5,2 s | centre bas |
| Pastilles épaule | `fx_epaule(chips, spots)` | avant / après, deux chiffres à côté de la tête (jamais sur le visage) | 4,4 s | à droite de la tête |

Outils communs : `glass_card` (carte en verre avec ombre, flou, filet blanc), `toggle`, `marker_arrow` (flèche au feutre
qui se dessine), `mixed_title` (titre « Mot *italique* »), `env` (entrée/sortie), `eo` / `eio` (courbes sans rebond).

## Règles d'usage (design system v2)
- **Un seul effet à l'écran à la fois**, 3 à 5 moments graphiques forts par Reel, en variant les effets.
- Jamais sur le visage : vérifier le cadrage du rush (placer `cy` / `spots` en conséquence).
- Laisser la zone des sous-titres libre : quand un effet est dans le bas, remonter ou masquer les sous-titres pendant l'effet.
- Le match-cut est un insert plein écran : une fois par Reel au maximum, sur LE mot-clé.

## Vus chez corbinsylk mais pas encore reproduits (à apprendre)
- **Relight** : changer l'éclairage du visage (golden hour, Rembrandt, stores vénitiens) → demande un modèle d'IA vidéo.
- **Graphe tenu en main** : la carte suit la main de Bene → demande du suivi de mouvement (tracking).
- **POV carrousel 3D** : écran de téléphone qui tourne en perspective avec des Reels qui défilent.
- **Écran « digital »** : mot en matrice de points / lignes de balayage.
- **Carrousels animés** (slides vidéo) : style « Liquid Glass » sombre et style éditorial crème + titres serif italiques.
