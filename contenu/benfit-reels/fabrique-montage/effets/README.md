# Bibliothèque d'effets « verre » BEN&FIT

Effets de motion design réutilisables pour les Reels (1080×1920, 30 fps) : **24 effets et outils**, ajoutés le 19 nov. 2026.
Inspiration : les vidéos d'effets envoyées par Bene (**corbinsylk**, **justyn.ai**, **geobertoo**, **tenfoldmarc**, **trainwithcharan**, **alirajabipro**, **jenna.nea**), **adaptées à la charte** :
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
Pour « texte derrière » et « contour découpé » (détourage de Bene) : `pip install onnxruntime` + le modèle
`u2net_human_seg.onnx` (voir `segmentation.py`, ~1 s par image : calculer le masque une fois par image et le passer
à `Canvas(frame, person_mask=…)` si plusieurs effets l'utilisent).
Pour « démo haut / Bene bas » et « téléphone » : `media = E.charger_media("clip.mp4" ou "anim.gif")`.

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
| Texte derrière | `fx_derriere(lignes, face, y)` | titre ou chiffres géants **derrière Bene** (il passe devant les lettres) : « 1 2 3 », « ZÉRO », « PACING » | 3,8 s | haut du cadre, derrière la tête |
| Contour découpé | `fx_decoupe(note, doodles)` | effet sticker : contour blanc autour de Bene + gribouillis qui tremblent + note au feutre ; moment perso ou drôle | 4,2 s | plein cadre |
| Démo haut / Bene bas | `fx_split(media, mots)` | montrer un exercice, une app, un extrait pendant que Bene explique ; un mot-clé bleu sous la démo | 5 s | écran séparé |
| Anneau macros | `fx_macros(kcal, macros)` | nutrition : anneau qui se remplit, kcal et grammes qui comptent | 5 s | bas du buste |
| Cadran d'effort | `fx_cadran(label, valeur)` | intensité (RPE 8/10, zone cardio) : l'aiguille tourne. ⚠️ proche des « jauges » refusées en v2 : seulement si le Reel parle vraiment d'intensité | 4,6 s | bas du buste |
| Carte barrée | `fx_barre(titre, barres, juste)` | idées reçues barrées au feutre, la bonne réponse écrite à la main (mythes) | 5,2 s | bas du buste |
| Téléphone | `fx_telephone(media)` | téléphone qui monte dans le cadre et lit une vidéo (exercice, app BoxLog, Reel cité) | 4,6 s | à droite |
| Calendrier | `fx_calendrier(seances, repos)` | semaine type : les séances se posent jour par jour, le repos est entouré | 5,4 s | bas du buste |
| Police qui change | `fx_police(mot, polices, derriere)` | titre géant qui change de police à chaque temps (Anton → serif italique → feutre → Coda) + menu « Police » en verre ; derrière Bene par défaut | 3 s | haut du cadre |
| Mot à mot géant | `fx_mot_a_mot(mots)` | phrase choc dite **un mot à la fois**, en très gros ; mots-clés en serif italique bleu clair (remplace les sous-titres le temps de la phrase) | selon la phrase | centre bas |
| Message qui s'écrit | `fx_message(nom, texte)` | DM d'un client ou question d'abonné qui se tape, puis « Envoyé » : pose le problème du Reel | 4,8 s | bas du buste |
| Curseur iOS | `fx_curseur(label, de, vers)` | curseur vertical du centre de contrôle qui monte (intensité, volume, effort) | 4 s | à droite |
| CTA commente | `fx_cta_commente(mot, sous)` | fin de Reel : COMMENTE « PROGRAMME » en géant (mot-clé à écrire en commentaire) | 3 s | bas |
| Cercle au feutre | `fx_entoure(cx, cy, rx, ry)` | entourer un mot, un chiffre, un détail de l'image (« air marker ») | 2 s | où il faut |
| Cadrage visage | `CadrageVisage(zoom)` (outil) | « face lock » : garde la tête de Bene au même endroit malgré la caméra à la main (tournage en courant) ; à appliquer à chaque image avant les effets | – | plein cadre |
| Swipe | `transition_swipe(a, b, p)` (outil) | transition entre deux plans façon coup de fouet horizontal, avec flou de mouvement (~0,25 s) | 0,25 s | transition |
| Rembobinage | `rembobiner(cv, t)` (outil) | habillage VHS ◀◀ RETOUR sur des images lues à l'envers et accélérées (« revenons en arrière ») | ~1,2 s | plein cadre |

Outils communs : `glass_card` (carte en verre avec ombre, flou, filet blanc), `toggle`, `marker_arrow` (flèche au feutre
qui se dessine), `mixed_title` (titre « Mot *italique* »), `env` (entrée/sortie), `eo` / `eio` (courbes sans rebond).

## Règles d'usage (design system v2)
- **Un seul effet à l'écran à la fois**, 3 à 5 moments graphiques forts par Reel, en variant les effets.
- Jamais sur le visage : vérifier le cadrage du rush (placer `cy` / `spots` en conséquence).
- Laisser la zone des sous-titres libre : quand un effet est dans le bas, remonter ou masquer les sous-titres pendant l'effet.
- Le match-cut est un insert plein écran : une fois par Reel au maximum, sur LE mot-clé.

## Historique des lots
- **Lot 1 (19 nov. 2026)**, corbinsylk « Liquid Glass » : interrupteurs, graphe, liste focus, carte preuve, match-cut, éventail, pastilles.
- **Lot 2 (19 nov. 2026)**, corbinsylk « 5 skills coach », liste « 17 video effects claude can create », justyn.ai :
  texte derrière, contour découpé (+ gribouillis), démo haut / Bene bas, anneau macros, cadran, carte barrée, téléphone, calendrier.
  Doublons écartés : *checklist* (= interrupteurs), *chart grow* (= graphe), *glass type* (= verre), *headline wall* (= texte
  derrière), *paper cut* + *doodle boil* (= contour découpé), *phone mockup* (= téléphone), carte flottante « mini course »
  (= encart flottant du design system), sous-titres en boîte (= nos sous-titres).

- **Lot 3 (19 nov. 2026, midi)**, trainwithcharan, geobertoo, alirajabipro, tenfoldmarc « 10 new video effects », jenna.nea :
  police qui change, mot à mot géant, message qui s'écrit, curseur iOS, CTA commente, cercle au feutre, cadrage visage,
  swipe, rembobinage. Doublons écartés : liste avec élément surligné (= liste focus), contour rouge + gribouillis
  (= contour découpé), mot sur flash blanc (= match-cut / mot géant), collage photo (= polaroid), « screen dive »
  téléphone en main (≈ téléphone), mur de miniatures (déjà à apprendre).

### Effets pilotés par les gestes (24 nov. 2026) — `reel-canape/build_canape.py`
| Effet | Fonction | Quand l'utiliser |
|---|---|---|
| Carrousel au doigt | `strokes()` + `draw_carousel()` | « sélection de personnage » : chaque balayage de la main fait tourner un carrousel 3D de vidéos |
| Claquement de doigts | coupe sur l'attaque du son + flash 3 images | changement de tenue / de lieu entre deux prises cadrées pareil |
| Mur au clap | `draw_wall()` + `person_masks()` | au clap, mur de vidéos qui se construit derrière Bene en vague depuis ses mains |
| Tornade multivers | `draw_tornado()` + `zone_tete()` | Bene debout au centre, ses vidéos tournent autour de lui en entonnoir (derrière/devant), jamais sur la tête |
Gestes détectés par le flux optique (mouvement) et le son (claquement, clap) : pas besoin de modèle de main.

## Vus mais pas encore reproduits (à apprendre)
- **Muscles qui s'allument** (anatomie 3D, muscles travaillés en couleur, corps qui tourne) : à faire avec la fabrique 3D
  `contenu/benfit-3d/` (corps MakeHuman + Blender), muscles en bleu BEN&FIT. Très utile pour les Reels technique.
- **Relight** : changer l'éclairage du visage (golden hour, Rembrandt, stores vénitiens) → demande un modèle d'IA vidéo.
- **Graphe tenu en main** : la carte suit la main de Bene → demande du suivi de mouvement (tracking).
- Effets de **suivi des mains** (tenfoldmarc) : étiquettes au bout des doigts (*finger tags*), objet entre les mains
  (*hand frame*), photo sortie de la poche (*pocket proof*), objet lancé (*ball toss*),
  plongée dans l'écran du téléphone (*screen dive*). À faire avec MediaPipe Hands (déjà dans l'environnement de `benfit-3d`).
- **POV carrousel 3D** : écran de téléphone qui tourne en perspective avec des Reels qui défilent.
- Mouvements de caméra : **zoom traversant** (zoom-through cut), **zoom numérique pixelisé**, **vertigo** (travelling compensé,
  demande le détourage), **pull-back reveal**, **orbit**.
- **Écran « digital »** : mot en matrice de points / lignes de balayage.
- Idée vue : **verre d'eau infini** (filet d'eau en boucle, verre qui reste plein) → boucle locale de la zone eau/verre, carafe immobile au tournage.
- Liste « 17 effets » encore à voir en détail : *couch wall*, *ui world*, *frame break*, *green screen*, *cover story*.
- Divers justyn.ai : bandes de couleurs de palette, étiquette « HELLO my name is », menu déroulant, mur de miniatures.
- **Carrousels animés** (slides vidéo) : style « Liquid Glass » sombre et style éditorial crème + titres serif italiques.
