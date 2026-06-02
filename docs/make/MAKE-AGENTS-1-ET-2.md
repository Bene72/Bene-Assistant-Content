# ============================================
# MAKE.COM — SCÉNARIOS AGENTS 1 & 2
# ============================================


# ══════════════════════════════════════════════
# AGENT 1 — ACQUISITION BOOST
# ══════════════════════════════════════════════

# ─────────────────────────────────────────────
# SCÉNARIO A1 — Prospect depuis site / formulaire
# Trigger : Webhooks → Custom webhook
# ─────────────────────────────────────────────

Module 1 : Webhooks → Custom webhook
  → Copier l'URL → mettre dans le formulaire site Benoit
  → Remplacer dans lead-magnet-hyrox.html :
    "VOTRE_MAKE_WEBHOOK_LEAD_MAGNET" → cette URL

Module 2 : HTTP → Make a request
  URL    : {AUTOFLOW_API_URL}/api/agents/acquisition-boost
  Method : POST
  Headers : x-autoflow-token: {WEBHOOK_SECRET}
  Body :
  {
    "action": "new_prospect",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{ACQUISITION_AGENT_ID}",
    "prospectData": {
      "name": "{{1.name}}",
      "email": "{{1.email}}",
      "phone": "{{1.phone}}",
      "message": "{{1.message}}",
      "goal": "{{1.objectif}}",
      "budget": "{{1.budget}}",
      "timeline": "{{1.quand}}",
      "source": "site_web"
    }
  }

Module 3 : Router
  Route A : {{2.data.qualification.score}} >= 70
  Route B : tout le reste

Module 4A : Gmail → Send an email
  To      : benoit.buon.lms@gmail.com
  Subject : 🔥 Lead CHAUD — {{1.name}} ({{2.data.qualification.score}}/100)
  Content :
    Nom : {{1.name}}
    Email : {{1.email}}
    Score : {{2.data.qualification.score}}/100
    Objectif : {{1.objectif}}
    Source : Site web
    → L'agent a déjà répondu. Tu peux personnaliser en répondant à {{1.email}}

Module 5 : Webhooks → Respond to a webhook
  Status : 200
  Body   : { "success": true }


# ─────────────────────────────────────────────
# SCÉNARIO A2 — Relances automatiques J+1/J+3/J+7
# Trigger : Schedule → Every day at 9:00
# ─────────────────────────────────────────────

Module 1 : Schedule → Every day at 09:00

Module 2 : HTTP → Supabase (tâches de relance dues)
  URL    : {SUPABASE_URL}/rest/v1/tasks
           ?status=eq.todo
           &title=like.Relance J*
           &due_date=lte.{{now}}
           &org_id=eq.{DEFAULT_ORG_ID}
           &select=id,title,metadata,due_date
  Method : GET
  Headers :
    apikey: {SUPABASE_ANON_KEY}
    Authorization: Bearer {SUPABASE_SERVICE_KEY}

Module 3 : Tools → Iterator
  Array : {{2}}

Module 4 : Tools → Set variable
  followup_day : {{if(contains(3.title, "J+1"), 1, if(contains(3.title, "J+3"), 3, 7))}}

Module 5 : HTTP → Make a request
  URL    : {AUTOFLOW_API_URL}/api/agents/acquisition-boost
  Method : POST
  Headers : x-autoflow-token: {WEBHOOK_SECRET}
  Body :
  {
    "action": "followup",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{ACQUISITION_AGENT_ID}",
    "leadId": "{{3.metadata.lead_id}}",
    "followupDay": {{4.followup_day}}
  }

Module 6 : HTTP → Supabase (marquer la tâche done)
  URL    : {SUPABASE_URL}/rest/v1/tasks?id=eq.{{3.id}}
  Method : PATCH
  Headers :
    apikey: {SUPABASE_ANON_KEY}
    Authorization: Bearer {SUPABASE_SERVICE_KEY}
    Content-Type: application/json
    Prefer: return=minimal
  Body : { "status": "done" }


# ══════════════════════════════════════════════
# AGENT 2 — RELANCE ARGENT
# ══════════════════════════════════════════════

# ─────────────────────────────────────────────
# SCÉNARIO B1 — Scan quotidien argent qui dort
# Trigger : Every day at 08:00
# ─────────────────────────────────────────────

Module 1 : Schedule → Every day at 08:00

Module 2 : HTTP → Scan (argent à récupérer)
  URL    : {AUTOFLOW_API_URL}/api/agents/relance-argent
  Method : POST
  Headers : x-autoflow-token: {WEBHOOK_SECRET}
  Body :
  {
    "action": "scan",
    "orgId": "{DEFAULT_ORG_ID}"
  }

Module 3 : Tools → Set variable
  total_at_stake : {{2.data.total_at_stake}}

Module 4 : Filter (si argent en jeu)
  Condition : {{3.total_at_stake}} > 0

Module 5 : HTTP → Déclencher les relances
  (Pour chaque inactif trouvé dans le scan)
  URL    : {AUTOFLOW_API_URL}/api/agents/relance-argent
  Method : POST
  Body :
  {
    "action": "send_relance",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{RELANCE_AGENT_ID}",
    "relanceType": "client_inactif",
    "targetData": {
      "lead_id": "{{lead.id}}",
      "name": "{{lead.full_name}}",
      "email": "{{lead.email}}",
      "amount_euros": 150,
      "context": "Client inactif depuis {{lead.days_inactive}} jours",
      "last_contact": "{{lead.last_contact_at}}"
    }
  }


# ─────────────────────────────────────────────
# SCÉNARIO B2 — Relance devis non signés
# Trigger : Every day at 10:00
# ─────────────────────────────────────────────

Module 1 : Schedule → Every day at 10:00

Module 2 : HTTP → Leads en stage "proposal" depuis > 2j
  URL    : {SUPABASE_URL}/rest/v1/leads
           ?stage=eq.proposal
           &org_id=eq.{DEFAULT_ORG_ID}
           &last_contact_at=lt.{{addDays(now, -2)}}
           &select=id,full_name,email,score,enriched_data,last_contact_at
  Method : GET
  Headers : apikey / Authorization (voir scénarios précédents)

Module 3 : Tools → Iterator

Module 4 : HTTP → Envoyer relance devis
  URL    : {AUTOFLOW_API_URL}/api/agents/relance-argent
  Method : POST
  Body :
  {
    "action": "send_relance",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{RELANCE_AGENT_ID}",
    "relanceType": "devis_non_signe",
    "targetData": {
      "lead_id": "{{3.id}}",
      "name": "{{3.full_name}}",
      "email": "{{3.email}}",
      "amount_euros": {{3.enriched_data.estimated_value}},
      "context": "Proposition envoyée, pas de réponse depuis {{dateDiff(now, 3.last_contact_at, 'days')}} jours",
      "last_contact": "{{3.last_contact_at}}"
    }
  }


# ─────────────────────────────────────────────
# SCÉNARIO B3 — Rapport mensuel argent récupéré
# Trigger : 1er du mois à 9:00
# ─────────────────────────────────────────────

Module 1 : Schedule → Every month, day 1, at 09:00

Module 2 : HTTP → Rapport
  URL    : {AUTOFLOW_API_URL}/api/agents/relance-argent
  Method : POST
  Body :
  {
    "action": "monthly_report",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{RELANCE_AGENT_ID}"
  }

  → Le rapport est envoyé directement par email à Benoit
     via Resend depuis l'agent (pas besoin de module Gmail ici)


# ══════════════════════════════════════════════
# AJOUTER DANS VERCEL — NOUVELLES VARIABLES ENV
# ══════════════════════════════════════════════

ACQUISITION_AGENT_ID  = (UUID créé via /api/seed ou Supabase)
RELANCE_AGENT_ID      = (UUID créé via /api/seed ou Supabase)

# Créer les agents dans Supabase directement :
# Table "agents" → Insert row
# type: "acquisition" pour l'agent Acquisition Boost
# type: "relance" pour l'agent Relance Argent
# system_prompt: celui du fichier system-prompts-coach.py
# org_id: {DEFAULT_ORG_ID}


# ══════════════════════════════════════════════
# TESTS RAPIDES
# ══════════════════════════════════════════════

# Test Agent Acquisition Boost
curl -X POST {AUTOFLOW_API_URL}/api/agents/acquisition-boost \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "new_prospect",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{ACQUISITION_AGENT_ID}",
    "prospectData": {
      "name": "Julie Test",
      "email": "julie.test@gmail.com",
      "message": "Je veux faire Hyrox Paris en novembre, je cherche un coach",
      "budget": "500€",
      "source": "site_web"
    }
  }'
# Attendu : score >= 75, priority "hot", email envoyé, notif Benoit

# Test Agent Relance Argent — Scan
curl -X POST {AUTOFLOW_API_URL}/api/agents/relance-argent \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "scan",
    "orgId": "{DEFAULT_ORG_ID}"
  }'
# Attendu : liste des inactifs, packs expirés, montant total en jeu

# Test relance manuelle
curl -X POST {AUTOFLOW_API_URL}/api/agents/relance-argent \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "send_relance",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{RELANCE_AGENT_ID}",
    "relanceType": "client_inactif",
    "targetData": {
      "lead_id": "uuid-lead-test",
      "name": "Thomas Test",
      "email": "thomas.test@gmail.com",
      "amount_euros": 490,
      "context": "Client inactif depuis 18 jours, objectif Hyrox"
    }
  }'
# Attendu : email de relance chaleureux généré et envoyé
