# Reel d'entraînement « Acteur principal » (23 nov. 2026)

Reel d'entraînement motivant, **21,7 s**. Demande de Bene : dynamique, motivationnel, très likeable, < 30 s, + photo résultat.

- **Voix off** : phrase dite par Bene en footing (rush 102125) : « Certains vont être narrateurs de ta vie, d'autres spectateurs. Mais c'est toi l'acteur principal. C'est à toi de faire tes choix, de les assumer. » La suite (« Rien ni personne ne pourra te… ») était incompréhensible : non utilisée.
- **Images sur la voix** : box jump au ralenti (accroche), Bene qui court face caméra (synchro, punch-in sur « l'acteur principal »), kipping pull-ups, sled.
- **Montage sans voix** (~10 s) avec chips bleus : back squat, DB snatch, bike, fentes sautées, box jump au ralenti, kipping pull-ups, snatch.
- **Fin** : photo résultat (vestiaire) + « C'EST TOI » (Anton) / bloc bleu « L'ACTEUR PRINCIPAL. ». La photo n'est pas dans le dépôt : passer son chemin dans `$PHOTO`.
- **Ralentis** : rushs 60 i/s lus à 0,5 (vraies images, pas d'interpolation).
- **Couleurs** d'origine (BT.709 conservé). **Son** : voix seule à -14 LUFS (traitement léger, -20 % comme demandé le 21 nov.), son ambiant des plans du montage 4 dB plus bas, rien sous la photo. Mono → stéréo à -3 dB (sinon +3 LU).

`python build_semaine.py edl` → `stills T…` → `video` ; `python thumb_semaine.py` pour la miniature.
Rushs : VID_20261119_102125 (footing), 20261123_103801 (box jumps), 20261117_104154 (pull-ups) + ceux du 20 nov.
