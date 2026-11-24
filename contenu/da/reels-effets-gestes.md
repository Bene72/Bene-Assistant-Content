# DA — Reels « effets gestes » (validé et adoré par Bene, 24 nov. 2026)

Format court (~15–18 s), **sans voix**, où les gestes de Bene déclenchent des effets « magiques » sur ses vraies vidéos
d'entraînement. Une petite **histoire** en 3–4 actes, des textes courts calés pile sur chaque action, un son tendance
ajouté sur Insta. Référence : Reel #10 « canapé » → `contenu/benfit-reels/fabrique-montage/reel-canape/`.

## Pourquoi ça marche
- **Identification** (« c'est moi », « c'est mon pote ») → partages. Hook en POV d'une situation que tout le monde vit.
- **Satisfaisant** : l'effet tombe pile sur le geste (claquement, clap) → on revoit en boucle.
- **Vraies images** de Bene (pas d'IA générée) : ses séances deviennent le décor de l'effet.

## Les effets disponibles (`reel-canape/build_canape.py`)
| Effet | Geste | Ce qui se passe |
|---|---|---|
| Carrousel au doigt | balayages de la main | carrousel 3D de ses vidéos (sélection de personnage), 1 carte par balayage ; la carte du centre a son titre en chip bleu |
| Claquement de doigts | claquement (son) | coupe sèche entre deux prises cadrées pareil + flash blanc 3 images → changement de tenue / de lieu |
| Mur au clap | clap (son) | mur de vidéos qui se construit en vague depuis ses mains, **derrière** lui |
| Tornade multivers | debout, il regarde autour de lui | ses vidéos tournent autour de lui en entonnoir, derrière puis devant, **jamais sur la tête** |
À ajouter dans la même logique (déjà repérés) : verre d'eau infini, finger tags, hand frame, pocket proof, ball toss, screen dive.

## Style validé
- **Couleurs d'origine**, aucun étalonnage (Bene : « il n'y a pas de couleur, c'est pas grave, j'adore comme ça »).
- Cartes / tuiles : coins arrondis, filet blanc, pas de halo, pas de rebond.
- **Textes** : Coda blanc bord bleu, mots-clés en bloc bleu `#2E6BFF`, **tiers haut** (le bas est pris par les effets et
  l'interface Instagram), petite arrivée (échelle 0,92 → 1 en 0,1 s), un texte par action. Script : `textes_canape.py`
  (`*mot-clé*` dans le texte).
- **Hook** en « POV : … » d'une situation vécue (« POV : t'as *pas envie* d'aller à la salle »), puis une chute par
  action (« …*ah.* », « *Trop tard.* », « …t'en sors *plus.* »).
- **Miniature** : l'image la plus spectaculaire (le mur) + le hook en Anton (« PAS ENVIE ? ») + bloc bleu Coda.
- **Caption** : une phrase d'identification + appel au partage (« Envoie ça à celui qui… »). **5 hashtags.**
- Banque de vidéos pour cartes / tuiles : au moins **10–13 vidéos différentes** (pas deux tuiles voisines identiques).
  Jamais de vidéo déjà montée (texte incrusté, logo) ni de personnage de dessin animé visible.

## Tournage (à rappeler à Bene avant chaque Reel de ce type)
- **Téléphone fixe** (trépied), on n'y touche plus entre les prises → les changements de tenue sont invisibles.
- Gestes **francs** : balayages horizontaux ~1 s avec une pause entre deux ; claquement et clap **bien audibles**, sans musique.
- Prise par « acte » (ex. : tenue canapé → tenue de sport), même place, même pose au moment du raccord.
- Laisser de l'**espace autour de lui** (les effets s'y affichent) ; plusieurs prises de chaque action, il en a fait et
  c'est parfait pour choisir.
- Rushs 60 i/s OK. Pas de parole nécessaire.

## Idées de prochains Reels dans ce format (à proposer)
1. **Le réveil** : POV le réveil sonne → il balaie pour « snooze » (carrousel d'excuses ? non : de séances) → claquement → en tenue → tornade.
2. **La télécommande** : il zappe avec la télécommande, chaque « chaîne » est une de ses séances (carrousel) → il éteint, clap → mur.
3. **Le frigo** (nutrition) : il ouvre le frigo, balaie entre « pizza » et « poulet-riz » (photos réelles) → claquement → assiette de prépa.
4. **Avant / après une prépa HYROX** : claquement entre la tenue du jour 1 et celle de la course, mur de ses séances de la prépa.
5. **Verre d'eau infini** : il parle hydratation pendant que l'eau coule sans fin (effet à construire).
6. **Le coach dans la poche** : il sort son téléphone (pocket proof) et l'écran montre l'app BoxLog / un bilan client.
7. **« Choisis ton athlète »** : carrousel des profils de ses athlètes (avec leur accord) façon jeu vidéo, stats en chips.
