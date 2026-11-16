# Reel « Le cardio fait-il perdre du muscle ? » (16 nov. 2026)

Scripts du 5e Reel, à réutiliser comme modèle (DA v2 naturelle + cartes interface en verre dépoli).

Ordre : `transcribe.py` (dossier parent) → `edl_cardio.py` → `build_base_naturel.py` (dossier parent, vitesse ×1,08)
→ `data_cardio.py` (sous-titres) → `compose_cardio.py` (motion design) → `audio_cardio.py <durée>` (bruitages + voix à -14 LUFS, sans musique)
→ `thumb_cardio.py` (miniature).

Nouveautés par rapport à « 4 qualités » :
- `compose_cardio.py` est autonome (il n'importe plus `compose.py` v1).
- `frost()` : carte en verre dépoli (fond flouté + voile marine + liseré blanc), titres en typographie mixte (`card_title`).
- `check()` : case qui se coche, pour les fiches / checklists.
- Mot géant en bas d'écran à la place des sous-titres, une fois par Reel.
