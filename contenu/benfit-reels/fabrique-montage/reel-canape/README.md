# Reel « canapé » (24 nov. 2026) : effets pilotés par les gestes

17,5 s (v3 avec la tornade), sans voix (son tendance ajouté sur Insta). Couleurs d'origine (BT.709 conservé).

1. **Carrousel au doigt** (sélection de personnage) : chaque balayage de la main fait tourner un carrousel 3D de ses vidéos
   d'entraînement (DB SNATCH, RUN, BIKE, BOX JUMP, PULL-UPS, SLED, SQUAT). Balayages détectés par **flux optique**
   (mouvement horizontal dans la zone des mains, `strokes()`), pas de modèle de main (MediaPipe n'est pas téléchargeable ici).
   Une carte de chaque côté, la carte du centre a son titre en chip bleu. Placé devant les jambes, jamais sur le visage.
2. **Claquement → tenue de sport** : coupe sèche sur l'attaque du son du claquement dans les deux prises (même cadre), flash blanc 3 images.
3. **Mur au clap** : au clap (détecté au son), tuiles vidéo qui apparaissent en vague depuis ses mains, **derrière** lui
   (détourage rembg `u2net_human_seg`), limité au haut du cadre (pas sur les jambes).

4. **Tornade « multivers »** (prise debout 150135, 21,8 → 27,4 s : il regarde autour de lui puis avance vers la caméra) :
   20 cartes vidéo en entonnoir (large en haut) tournent autour de lui de plus en plus vite, derrière puis devant
   (détourage). La **tête est repérée à chaque image** dans le détourage (`zone_tete`) : aucune carte ne passe dessus.
   Histoire : il se lève du canapé, il n'a plus le choix, il est pris dans la spirale (légendes ajoutées par Bene).

`python build_canape.py strokes` (voir les balayages détectés) → `stills T…` → `video` ; `python thumb_canape.py`.
Cartes : 7 vidéos (finit sur l'arraché barre) ; mur : 13 vidéos différentes (`MUR`), ajoutées le 24 nov. (vélo, tirage poulie, arraché, rameur, wall balls, jerk). Vidéo `lv_0_20260701102746` écartée (déjà montée, texte incrusté, chaussettes Bob l'éponge).
Rushs : 145737 (intro casque/téléphone), 145821 (balayages + claquement 13,74 s), 150014 (claquement tenue de sport 4,53 s),
150218 (clap 5,32 s). Prise 150135 (debout) : tornade.
Tournage : téléphone fixe, gestes francs, claquement et clap bien audibles.
