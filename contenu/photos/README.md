# « Optimise cette photo » — retouche SANS triche

Phrase à dire à Claude : **« Optimise cette photo »** (+ la photo en pièce jointe).
Variantes : « optimise-la plus doux » (`--force 0.6`) / « plus marqué » (`--force 1.4`).

## La règle (très important pour Bene)
Rendu plus lumineux, plus net, plus de relief — **mais rien d'inventé**. Chaque pixel vient de la photo d'origine.
- ✅ Autorisé : déboucher les ombres, exposition, contraste local / relief, netteté, balance des blancs,
  réduction de bruit légère, agrandissement ×2.
- ❌ Interdit : IA générative / « upscale IA » qui redessine, ajout de veines, d'abdos plus découpés, de barbe,
  corps plus sec, peau lissée, visage modifié. Raison : la photo sert de preuve physique pour le coaching,
  un physique retouché casse la crédibilité.

Origine (20 nov. 2026) : une autre IA avait « amélioré » un selfie vestiaire en inventant de la définition
musculaire. Bene a choisi « le meilleur des deux » : se rapprocher de ce rendu lumineux sans rien inventer.

## Utilisation
```
python optimise_photo.py entree.jpg sortie.jpg [--force 1.0] [--echelle 2]
```
Prérequis : `pip install opencv-python-headless pillow numpy`.
Vérifier toujours en comparant avant / après (même zone zoomée) : le fond reste sombre, seul le sujet s'éclaire.
