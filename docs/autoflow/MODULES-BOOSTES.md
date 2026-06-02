# Modules AutoFlow boostes

Les agents suivants sont maintenant deployables via Vercel dans `/api/agents`.

## Endpoints

- `POST /api/agents/acquisition-boost` : qualification prospects, score, reponse rapide, sequence J+1/J+3/J+7.
- `POST /api/agents/relance-argent` : devis non signes, factures impayees, fins de pack, clients inactifs, renouvellements.
- `POST /api/agents/satisfaction` : satisfaction client, detection client content/mecontent, avis Google.
- `POST /api/agents/contenu-reseaux` : posts, carrousels, reels, calendrier editorial.
- `POST /api/agents/onboarding` : email de bienvenue, questionnaire, taches internes, relances documents.
- `POST /api/agents/devis` : proposition commerciale, devis, email d'accompagnement, relances.
- `POST /api/agents/coach-business` : copilote business hebdomadaire pour le client.
- `POST /api/agents/roi-reporting` : rapport ROI mensuel pour prouver la valeur AutoFlow.

Tous les appels doivent inclure le header :

```text
x-autoflow-token: WEBHOOK_SECRET
```

## Cockpit

Ouvre :

```text
https://bene-assistant.vercel.app/
```

Le cockpit permet de choisir un agent, de coller un payload JSON et de tester directement le module.

## Make

Les guides Make sont dans :

- `docs/make/MAKE-AGENTS-1-ET-2.md`
- `docs/make/MAKE-AGENTS-3-ET-5.md`
- `docs/make/MAKE-AGENT-6.md`
- `docs/make/MAKE-AGENT-7.md`
- `docs/make/MAKE-AGENTS-8-ET-9.md`

## Variables Vercel requises

```env
ANTHROPIC_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
SUPABASE_ANON_KEY=
RESEND_API_KEY=
WEBHOOK_SECRET=
BENOIT_EMAIL=benoit.buon.lms@gmail.com
BENOIT_CALENDLY_URL=https://calendly.com/benoit-coach
AUTOFLOW_FOUNDER_ENABLED=true
```

## Ordre de mise en route

1. Ajouter les variables Vercel.
2. Redeploy.
3. Tester `/api/health`.
4. Ouvrir le cockpit.
5. Tester Agent Acquisition Boost avec un faux lead.
6. Brancher Make module par module.