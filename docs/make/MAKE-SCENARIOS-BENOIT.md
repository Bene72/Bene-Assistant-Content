# Make.com - scénarios Ben&Fit / AutoFlow

Ce dossier remplace les anciens workflows n8n. La logique reste identique : Make écoute Gmail, formulaires et plannings, puis appelle les endpoints Vercel des agents.

## Variables à préparer dans Make

Crée ces variables dans chaque scénario, ou garde-les dans un bloc de notes sécurisé :

- AUTOFLOW_API_URL : URL Vercel du projet, exemple https://benfit.vercel.app
- WEBHOOK_SECRET : même valeur que la variable Vercel WEBHOOK_SECRET
- ORG_ID : valeur retournée par /api/admin/seed-benoit
- AGENT_COMMUNICATION_ID : valeur retournée par le seed
- AGENT_COMMERCIAL_ID : valeur retournée par le seed
- AGENT_REALISATION_ID : valeur retournée par le seed
- EMAIL_BENOIT : benoit.buon.lms@gmail.com

## Scénario 1 - Nouveau prospect site vers agent commercial

Déclencheur : Webhooks > Custom webhook. Branche ce webhook sur le formulaire du site ou Typeform.

Module HTTP > Make a request :

- Method : POST
- URL : {{AUTOFLOW_API_URL}}/api/agents/commercial
- Headers :
  - Content-Type: application/json
  - x-autoflow-token: {{WEBHOOK_SECRET}}
- Body type : Raw JSON

Body :

```json
{
  "action": "qualify",
  "orgId": "{{ORG_ID}}",
  "agentId": "{{AGENT_COMMERCIAL_ID}}",
  "leadData": {
    "name": "{{1.name}}",
    "email": "{{1.email}}",
    "phone": "{{1.phone}}",
    "goal": "{{1.goal}}",
    "message": "{{1.message}}",
    "source": "website"
  }
}
```

Routeur recommandé :

- Si score >= 75 : notification immédiate à toi + Benoit, puis email invitation Calendly.
- Si score entre 45 et 74 : email nurturing J+0, J+3, J+7.
- Si score < 45 : email poli avec ressources et invitation douce.

## Scénario 2 - Gmail entrant vers agent communication

Déclencheur : Gmail > Watch emails.

Filtres :

- À : benoit.buon.lms@gmail.com
- Exclure les newsletters et no-reply.
- Option prudente au début : ne pas envoyer automatiquement. Enregistrer le brouillon Gmail pour validation.

Module HTTP > Make a request :

- Method : POST
- URL : {{AUTOFLOW_API_URL}}/api/agents/communication
- Headers :
  - Content-Type: application/json
  - x-autoflow-token: {{WEBHOOK_SECRET}}

Body :

```json
{
  "orgId": "{{ORG_ID}}",
  "agentId": "{{AGENT_COMMUNICATION_ID}}",
  "contactEmail": "{{1.from.email}}",
  "contactName": "{{1.from.name}}",
  "message": "{{1.text}}",
  "channel": "email"
}
```

Module Gmail suivant : Create a draft avec le champ reply retourné par l'API.
Après 7 jours de vérification, tu peux passer de Create draft à Send email pour les cas simples.

## Scénario 3 - Relances clients

Déclencheur : Scheduler > Every day at 08:00.

Étape A : Supabase > appeler la fonction RPC get_clients_to_remind avec p_org_id = ORG_ID.
Étape B : Iterator sur chaque client retourné.
Étape C : HTTP vers /api/agents/communication pour générer le message adapté.
Étape D : Gmail Create draft ou Send email selon le niveau de confiance.

Types attendus :

- session_tomorrow : rappel séance J-1
- checkin_j3 : prise de nouvelles après séance
- inactive_j14 : client inactif depuis 14 jours
- renewal_pack : pack presque terminé

## Scénario 4 - Rapport hebdomadaire

Déclencheur : Scheduler > Every Monday at 08:00.

Module HTTP :

```json
{
  "action": "weekly_report",
  "orgId": "{{ORG_ID}}",
  "agentId": "{{AGENT_REALISATION_ID}}"
}
```

URL : {{AUTOFLOW_API_URL}}/api/agents/realisation

En sortie : envoyer le rapport par email à toi et à Benoit.

## Tests de validation

1. Ouvre {{AUTOFLOW_API_URL}}/api/health. Tu dois voir ok: true.
2. Appelle /api/admin/seed-benoit une seule fois en POST avec x-autoflow-token.
3. Copie les UUID retournés dans Vercel et dans Make.
4. Lance le scénario prospect avec un faux lead Hyrox.
5. Envoie un email test à Benoit depuis une autre adresse et vérifie le brouillon généré.

## Règle importante

Pendant les 7 premiers jours, Make doit créer des brouillons et non envoyer automatiquement, sauf pour les emails prospects simples. C'est la phase de calibration du ton de Benoit.
