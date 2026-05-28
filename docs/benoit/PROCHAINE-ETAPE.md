# Prochaine étape - mise en production Benoit

## Objectif immédiat

Faire passer Ben&Fit de site vitrine à système opérationnel : capter les prospects, répondre vite, suivre les clients et générer les relances.

## Ordre exact

1. Dans Supabase, exécuter supabase/schema.sql.
2. Dans Supabase, exécuter supabase/functions-benoit.sql.
3. Dans Vercel, renseigner les variables de .env.example.
4. Déployer le dépôt.
5. Tester /api/health.
6. Appeler /api/admin/seed-benoit une seule fois.
7. Copier les UUID retournés dans les variables Vercel et Make.
8. Créer les 4 scénarios Make du guide docs/make/MAKE-SCENARIOS-BENOIT.md.
9. Laisser les réponses email en brouillon pendant 7 jours.
10. Faire le point avec Benoit après 20 à 30 vrais messages.
11. Ouvrir /assistant.html pour utiliser l'assistant fondateur AutoFlow sur ton offre, ton site et tes prochaines ventes.

## Ce qui manque encore

Stripe n'est pas encore créé. Ce n'est pas bloquant pour démarrer le suivi, les réponses et la qualification prospects. Les liens Stripe restent à remplacer dès que Benoit les a :

- BENOIT_STRIPE_SEANCE_URL
- BENOIT_STRIPE_PACK_URL
- BENOIT_STRIPE_ONLINE_URL

## Tests rapides

### Health

```bash
curl https://TON-DOMAINE-VERCEL/api/health
```

### Agent commercial

```bash
curl -X POST https://TON-DOMAINE-VERCEL/api/agents/commercial \
  -H "Content-Type: application/json" \
  -H "x-autoflow-token: TON_WEBHOOK_SECRET" \
  -d '{
    "action":"qualify",
    "orgId":"TON_ORG_ID",
    "agentId":"TON_AGENT_COMMERCIAL_ID",
    "leadData":{
      "name":"Test Hyrox",
      "email":"test@example.com",
      "goal":"Je prépare un Hyrox dans 10 semaines et je veux un coach à Nantes",
      "source":"test"
    }
  }'
```

### Agent communication

```bash
curl -X POST https://TON-DOMAINE-VERCEL/api/agents/communication \
  -H "Content-Type: application/json" \
  -H "x-autoflow-token: TON_WEBHOOK_SECRET" \
  -d '{
    "orgId":"TON_ORG_ID",
    "agentId":"TON_AGENT_COMMUNICATION_ID",
    "contactEmail":"test@example.com",
    "contactName":"Client Test",
    "message":"Salut Benoit, tu as des créneaux pour préparer un Hyrox ?",
    "channel":"email"
  }'
```
