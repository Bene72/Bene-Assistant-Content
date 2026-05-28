# Assistant fondateur AutoFlow

Cet assistant sert à développer AutoFlow : site, offres, scripts de vente, propositions commerciales, workflows Make et livrables clients.

## Ce qu'il sait déjà

- AutoFlow vend des assistants IA et automatisations métiers.
- Premier cas client : Benoit, coach fitness, CrossFit et Hyrox à Nantes.
- Offre validée : Pro Coach à 490€/mois.
- Problèmes traités : suivi clients, relances, acquisition, admin, réponses emails.
- Stack : GitHub, Vercel, Supabase, Make, Anthropic, Resend.

## Endpoint

```text
POST /api/agents/founder
```

Header :

```text
x-autoflow-token: WEBHOOK_SECRET
```

Body :

```json
{
  "mode": "strategy",
  "message": "Crée une offre AutoFlow pour les kinés.",
  "context": "Optionnel : notes client, prix, cible, objections."
}
```

## Cockpit

Après déploiement, ouvre :

```text
/assistant.html
```

Entre WEBHOOK_SECRET, choisis un mode, puis demande ce que tu veux produire.

## Méthode de travail

1. Créer une offre claire pour une cible.
2. Créer la page ou section de vente.
3. Créer le script d'appel découverte.
4. Créer l'email d'approche.
5. Créer le workflow Make type.
6. Répliquer sur un nouveau métier.

## Prochaines niches à tester

- Coachs sportifs.
- Kinés.
- Ostéopathes.
- Centres de formation.
- Artisans premium.
- Cabinets de conseil locaux.

## Règle produit

Chaque nouveau client doit produire un template réutilisable : prompt, workflow Make, onboarding, email, proposition commerciale.
