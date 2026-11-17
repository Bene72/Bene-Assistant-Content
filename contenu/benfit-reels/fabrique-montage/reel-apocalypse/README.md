# Reel « J'ai testé le bloc d'Apocalypse Training » (17 nov. 2026)

Modèle pour les **Reels d'entraînement** (séances filmées, sans parole) et les **collaborations**.

Ordre : `edl_apo.py` (liste des plans : rush, entrée, sortie, vitesse, zoom, section)
→ `build_base_apo.py` (assemblage + étalonnage naturel, vitesse par plan : ralentis 0,5, accélérés 1,2–1,4)
→ `compose_apo.py` (intro co-branding < 1 s, titre Anton, chips d'exercice numérotés, logos discrets en coin, carte de fin)
→ `audio_apo.py <durée>` (ambiance des rushs nettoyée + whooshs, -14 LUFS, sans musique)
→ `thumb_apo.py` (miniature).

Astuce placement : les chips changent de coin selon le plan (haut gauche sur fond de mur, bas droite sur le sol)
pour ne jamais passer sur Bene ni sur la charge. Vérifier avec `python3 compose_apo.py stills 3.5 10 ...`.
