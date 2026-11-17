# Jarvis à la maison : matériel et mise en place

Jarvis ne pilote pas les appareils directement : il parle à **Home Assistant**, une petite box qui gère toute la maison **en local** (lumières, capteurs, enceinte). Les automatismes simples (lumière quand ça bouge) tournent dans Home Assistant, même si Jarvis ou Internet sont coupés. Jarvis intervient pour ce qui demande de réfléchir : ton brief, tes questions, tes mails.

## Ce qu'il faut acheter

Prix relevés en 2026, à vérifier au moment de l'achat.

| Rôle | Produit | Prix indicatif |
|---|---|---|
| Le cerveau de la maison | **Home Assistant Green** (box prête à l'emploi, à brancher sur ta box Internet) | 179 € |
| La radio pour les capteurs et ampoules | **Home Assistant Connect ZBT-2** (clé USB Zigbee) | ~50 € |
| L'enceinte « Hey Jarvis » | **Home Assistant Voice Preview Edition** + un chargeur USB-C 5 V 2 A (non fourni) | ~60-70 € |
| Détecteurs de mouvement | Capteurs **Zigbee**, par exemple **Aqara Motion Sensor P1** (pile ~5 ans) | ordre de 20-30 € pièce |
| Lumières | Ampoules **Zigbee** : **IKEA KAJPLATS** (savent passer en Zigbee) ou **Philips Hue** | ~10-25 € pièce |
| Prises (lampe, cafetière…) | Prises connectées **Zigbee** (Aqara, Sonoff, Nous…) | ~10-20 € pièce |

**Règle d'or : tout en Zigbee.** La clé ZBT-2 fait Zigbee *ou* Thread, pas les deux en même temps. Avant d'acheter, vérifie « Zigbee » sur la boîte. Évite les appareils Wi-Fi « à application » et les gammes uniquement Thread/Matter (comme les nouveaux capteurs IKEA MYGGSPRAY).

### Par étapes (conseillé)
1. **Maintenant, 0 €** : Jarvis sur Telegram (vocaux, mails, brief). Rien à acheter.
2. **Étape maison, ~300 €** : Green + ZBT-2 + 1 capteur de mouvement + 2-3 ampoules + 1 prise. Tu valides que ça te sert.
3. **Étape voix, ~70 €** : l'enceinte Voice PE pour parler à Jarvis sans téléphone.

## Installer Home Assistant (étape maison)

1. Branche la **Green** sur ta box Internet (câble réseau) et sur le secteur, puis branche la **ZBT-2** sur un port USB de la Green, avec la rallonge fournie (éloigne-la un peu de la Green).
2. Sur ton PC, ouvre **http://homeassistant.local:8123** (patiente 10-20 min au premier démarrage) et crée ton compte.
3. Home Assistant détecte la ZBT-2 : choisis **Zigbee** (ZHA).
4. Ajoute tes appareils : *Paramètres > Appareils et services > Zigbee > Ajouter un appareil*, puis mets chaque appareil en mode appairage (voir sa notice). Range-les dans des **pièces** (Salon, Cuisine…) : Jarvis s'en sert pour comprendre « allume le salon ».
5. **Relie Jarvis à Home Assistant** :
   - Dans Home Assistant, clique sur ton nom en bas à gauche, onglet **Sécurité**, tout en bas : **Jetons d'accès longue durée > Créer un jeton**, nomme-le « Jarvis », copie-le (il ne s'affiche qu'une fois).
   - Sur le PC de Jarvis, double-clique sur `modifier_cle.bat` : choisis **Adresse de Home Assistant** (`http://homeassistant.local:8123`), puis **Jeton longue durée** (colle le jeton).
   - Relance `start.bat`, puis `/diag` sur Telegram : « Home Assistant » et « Routines maison » doivent être en vert.

Tu peux alors dire à Jarvis, par écrit ou en vocal : « allume le salon à 30 % », « éteins tout », « il fait combien dans la chambre ? ».

## Automatisations (à faire dans Home Assistant)

### 1. Lumière quand ça bouge (sans Jarvis, 100 % local)
Home Assistant l'a déjà, inutile d'écrire quoi que ce soit :
*Paramètres > Automatisations et scènes > Blueprints > **Motion-activated Light** > Créer une automatisation*. Choisis le capteur de mouvement, la lumière, et le délai avant extinction (par exemple 3 min). Une par pièce.

### 2. Brief au réveil
Le premier mouvement dans la cuisine le matin déclenche ton brief sur Telegram, une seule fois par jour. Le brief de 7h30 ne part pas en double.
Fichier : [`brief_reveil.yaml`](brief_reveil.yaml). Dans *Automatisations > Créer > ⋮ > Modifier en YAML*, colle le contenu, remplace le nom du capteur, enregistre.
Conseil : une fois ça en place, mets `BRIEF_TIME=10:00` dans `.env` (avec `modifier_cle.bat`). Le brief automatique devient alors un filet de sécurité, si tu n'es pas passé dans la cuisine.

### 3. Question à l'enceinte (étape voix)
Dis **« Hey Jarvis »** à l'enceinte :
- **Commandes de la maison** (« Hey Jarvis, allume le salon ») : traitées directement par Home Assistant, instantané, sans passer par Claude.
- **Questions** (« Hey Jarvis, dis-moi ce que j'ai demain ») : l'enceinte répond « Je regarde », Home Assistant transmet à Jarvis, qui répond à voix haute quelques secondes plus tard. Fichier : [`question_enceinte.yaml`](question_enceinte.yaml).

Par sécurité, depuis l'enceinte, Jarvis ne peut **ni lire tes mails ni parler de tes clients** : n'importe qui à la maison peut lui parler. Il a seulement accès à la maison, à l'agenda, à la to-do et aux anniversaires (réglable avec `HOME_VOICE_TOOLS`). Le reste passe par Telegram.

Mise en place de l'enceinte : branche-la, Home Assistant la détecte (*Paramètres > Appareils et services*). Dans ses réglages, choisis le mot d'activation **« Hey Jarvis »** et la langue **français**. Copie ensuite son identifiant (`assist_satellite.xxx`) dans `HA_SATELLITE` avec `modifier_cle.bat`.
Reconnaissance vocale de l'enceinte : les commandes de la maison fonctionnent en local et gratuitement. Pour les questions libres en français, la reconnaissance locale sur la Green est lente et approximative. Le plus simple est l'abonnement **Home Assistant Cloud** (quelques euros par mois), ou plus tard un ordinateur plus puissant.

### 4. Bonus : retour à la maison
Avec l'application Home Assistant sur ton téléphone (localisation), Jarvis peut te faire un point quand tu rentres. Fichier : [`retour_maison.yaml`](retour_maison.yaml).

## Comment ça marche (pour info)
Les automatisations envoient un événement `jarvis_routine` que Jarvis écoute :
- `routine: brief` → brief du matin sur Telegram (une fois par jour), `format: texte | vocal | les deux`
- `routine: question` + `text` + `satellite` → réponse lue sur l'enceinte (outils limités)
- `routine: message` + `text` → Jarvis traite le texte avec toutes ses compétences et te répond sur Telegram

Garde-fou : une même routine au plus toutes les 20 s, et 30 par heure au maximum, pour qu'un capteur qui s'emballe ne vide pas ton quota Claude.
