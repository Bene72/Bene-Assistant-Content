# ============================================
# MAKE.COM — SCÉNARIOS AGENT 6 ONBOARDING
# ============================================

# ─────────────────────────────────────────────
# SCÉNARIO E1 — Déclencher onboarding dès signature
# Trigger : Webhooks → Custom webhook
# (appelé depuis Supabase trigger ou dashboard)
# ─────────────────────────────────────────────

Module 1 : Webhooks → Custom webhook
  → URL : MAKE_WEBHOOK_ONBOARDING
  → Brancher sur le trigger Supabase "lead.won"
    (via le trigger SQL t_lead_won du schema)

Module 2 : HTTP → Démarrer onboarding
  URL    : {AUTOFLOW_API_URL}/api/agents/onboarding
  Method : POST
  Headers : x-autoflow-token: {WEBHOOK_SECRET}
  Body :
  {
    "action": "start",
    "orgId": "{{1.org_id}}",
    "agentId": "{ONBOARDING_AGENT_ID}",
    "leadId": "{{1.lead_id}}",
    "planType": "{{1.plan_type}}"
  }

Module 3 : Gmail → Send an email (notif interne Benoit)
  To      : benoit.buon.lms@gmail.com
  Subject : 🎉 Nouveau client signé — {{1.client_name}}
  Content :
    L'onboarding de {{1.client_name}} a été déclenché automatiquement.
    Email de bienvenue + questionnaire envoyés.
    {{2.data.tasks_created}} tâches créées dans le dashboard.
    Questionnaire : {{2.data.questionnaire_url}}


# ─────────────────────────────────────────────
# SCÉNARIO E2 — Relance questionnaire J+2
# Trigger : Schedule → Every day at 11:00
# ─────────────────────────────────────────────

Module 1 : Schedule → Every day at 11:00

Module 2 : HTTP → Supabase (leads onboarding sans questionnaire depuis 2j)
  URL    : {SUPABASE_URL}/rest/v1/leads
           ?org_id=eq.{DEFAULT_ORG_ID}
           &stage=eq.won
           &enriched_data->>questionnaire_sent=eq.true
           &enriched_data->>questionnaire_completed=eq.false
           &enriched_data->>onboarding_started=lt.{{formatDate(addDays(now,-2),"YYYY-MM-DDTHH:mm:ssZ")}}
           &select=id,full_name,email,enriched_data
  Method : GET
  Headers : apikey + Authorization

Module 3 : Tools → Iterator

Module 4 : Filter
  Condition : {{3.enriched_data.reminder_j2_sent}} != true

Module 5 : HTTP → Relance J+2
  URL    : {AUTOFLOW_API_URL}/api/agents/onboarding
  Method : POST
  Body :
  {
    "action": "remind_questionnaire",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{ONBOARDING_AGENT_ID}",
    "leadId": "{{3.id}}",
    "reminderDay": 2
  }

Module 6 : HTTP → Marquer relance J+2 envoyée (Supabase PATCH)
  URL    : {SUPABASE_URL}/rest/v1/leads?id=eq.{{3.id}}
  Method : PATCH
  Body   : { "enriched_data": { ...{{3.enriched_data}}, "reminder_j2_sent": true } }


# ─────────────────────────────────────────────
# SCÉNARIO E3 — Relance questionnaire J+5
# (même logique que E2 mais avec reminderDay: 5)
# ─────────────────────────────────────────────
# Copier E2, changer :
# - filtre date : addDays(now,-5)
# - reminderDay: 5
# - filtre enriched_data.reminder_j5_sent != true
# - marquer reminder_j5_sent: true


# ── Variables Vercel à ajouter ─────────────────
# ONBOARDING_AGENT_ID = (UUID depuis Supabase)


# ══════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════

# Test démarrer onboarding
curl -X POST {AUTOFLOW_API_URL}/api/agents/onboarding \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "start",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{ONBOARDING_AGENT_ID}",
    "leadId": "UUID_LEAD_TEST",
    "planType": "Pro Coach 490€/mois"
  }'
# Attendu : email bienvenue + questionnaire envoyés, tâches créées

# Test afficher le questionnaire (navigateur)
# Ouvrir : {AUTOFLOW_API_URL}/api/agents/onboarding?lead=UUID_LEAD&org=UUID_ORG

# Test relance J+2
curl -X POST {AUTOFLOW_API_URL}/api/agents/onboarding \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "remind_questionnaire",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{ONBOARDING_AGENT_ID}",
    "leadId": "UUID_LEAD_TEST",
    "reminderDay": 2
  }'
