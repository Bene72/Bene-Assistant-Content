# Reel « séance à deux » BEN&FIT × Apocalypse Training (26 nov. 2026)

~78 s (v2), séance haltéro avec l'ami d'Apocalypse Training. **Pas de sous-titres** (demande de Bene), répliques gardées avec leur son.
Structure : accroche (réception d'arraché au ralenti + « SÉANCE À DEUX ») → « sponsorisé par Apocalypse » (selfie)
→ **ÉCHAUFFEMENT** (mobilité accélérée, barre à vide) → **BLOC 1** arraché (+ « passation de pouvoir », écran partagé)
→ **BLOC 2** arraché autre plateau → **BLOC 3** épaulé-jeté → **RENFORT** rowing haltère → carte de fin co-branding.

v2 (retours de Bene) : **barre de progression retirée** (« vraiment moche ») ; +13 s de plans de discussion (Apocalypse qui rigole,
Bene qui explique le tirage lourd, « tu passes », « pas mal de passer au-dessus ») et d'angles ; **qualité max** : zooms
plafonnés ~1,45×, agrandissement Lanczos (le bilinéaire rendait mou), CRF 10.

Animations (`build_seance.py`) : bandeau de
chapitre qui balaie (Anton + sous-titre Coda + n° 01/05), rampes de vitesse (ralenti 0,4–0,5 sur les réceptions,
rushs 60 i/s), punch-ins sur les réceptions, flash 3 images sur les plus belles, écran partagé Bene | Apocalypse,
transitions coup de fouet + whoosh. Couleurs d'origine. Son : ambiance basse (musique de salle), répliques -14 LUFS.
Une 3e personne (sweat rose) visible dans 142735 : plans recadrés / évités.
Noms des blocs déduits de l'ordre des rushs (à corriger dans `PLANS` si besoin). Logos absents du dépôt
(`contenu/logos/` vide) → co-branding en texte.

`python build_seance.py plan` → `stills T…` → `video` ; `python thumb_seance.py`.

## Version « vlog » (27 nov.) — `build_vlog.py`, à partir du montage de Bene
Son montage gardé tel quel (plans longs, vitesse réelle, aucun texte) + seulement : selfie « sponsorisé par Apocalypse »
en accroche, long plan d'arraché resserré sur 2 reps, ~70 s, et **3 transitions néon orange** (filet de lumière qui balaie
+ whoosh et petit impact grave). Orange = demande de Bene pour ces transitions. Pas de repères de chapitres (« horrible »).
Résolution d'origine 1440×2560. Lecture image par image (sinon mémoire saturée).
