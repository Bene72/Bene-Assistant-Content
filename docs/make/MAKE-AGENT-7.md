# ============================================
# MAKE.COM — SCÉNARIOS AGENT 7 DEVIS
# ============================================

# ─────────────────────────────────────────────
# SCÉNARIO F1 — Générer un devis depuis un brief
# Trigger : Webhooks → Custom webhook
# (déclenché depuis le dashboard ou manuellement)
# ─────────────────────────────────────────────

Module 1 : Webhooks → Custom webhook
  → URL : MAKE_WEBHOOK_DEVIS
  → À appeler quand Benoit veut créer un devis

Module 2 : HTTP → Générer la proposition
  URL    : {AUTOFLOW_API_URL}/api/agents/devis
  Method : POST
  Headers : x-autoflow-token: {WEBHOOK_SECRET}
  Body :
  {
    "action": "generate",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{DEVIS_AGENT_ID}",
    "leadId": "{{1.lead_id}}",
    "briefData": {
      "client_name": "{{1.client_name}}",
      "client_email": "{{1.client_email}}",
      "needs": "{{1.needs}}",
      "goal": "{{1.goal}}",
      "budget": "{{1.budget}}",
      "timeline": "{{1.timeline}}",
      "context": "{{1.context}}"
    }
  }

Module 3 : Gmail → Send an email (copie interne)
  To      : benoit.buon.lms@gmail.com
  Subject : ✅ Devis {{2.data.devis_number}} généré — {{1.client_name}} — {{2.data.proposal.total_ttc}}€
  Content :
    Le devis a été envoyé automatiquement à {{1.client_email}}.
    3 relances planifiées : J+2, J+5, J+10.
    Consulter le dashboard pour suivre l'état.

  Note : Le devis complet est déjà envoyé au client par l'agent.
         Ce module est juste la notification interne.


# ─────────────────────────────────────────────
# SCÉNARIO F2 — Relances devis automatiques
# Trigger : Schedule → Every day at 10:30
# ─────────────────────────────────────────────

Module 1 : Schedule → Every day at 10:30

Module 2 : HTTP → Tâches de relance devis dues aujourd'hui
  URL    : {SUPABASE_URL}/rest/v1/tasks
           ?status=eq.todo
           &title=like.Relance devis*
           &due_date=lte.{{now}}
           &org_id=eq.{DEFAULT_ORG_ID}
           &select=id,title,metadata,due_date
  Method : GET
  Headers : apikey + Authorization

Module 3 : Tools → Iterator

Module 4 : HTTP → Vérifier si lead encore en proposal
  URL    : {SUPABASE_URL}/rest/v1/leads?id=eq.{{3.metadata.lead_id}}&select=stage
  Method : GET
  Headers : apikey + Authorization

Module 5 : Filter
  Condition : {{4[].stage}} = "proposal"
  (Ne pas relancer si déjà signé)

Module 6 : HTTP → Envoyer la relance
  URL    : {AUTOFLOW_API_URL}/api/agents/devis
  Method : POST
  Headers : x-autoflow-token: {WEBHOOK_SECRET}
  Body :
  {
    "action": "followup",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{DEVIS_AGENT_ID}",
    "leadId": "{{3.metadata.lead_id}}",
    "followupDay": {{3.metadata.followup_day}},
    "devisData": {
      "devis_number": "{{3.metadata.devis_number}}",
      "amount": {{3.metadata.amount}},
      "client_email": "{{3.metadata.client_email}}",
      "objections": {{3.metadata.objections}},
      "urgency_argument": "{{3.metadata.urgency_argument}}"
    }
  }

Module 7 : HTTP → Marquer la tâche done
  URL    : {SUPABASE_URL}/rest/v1/tasks?id=eq.{{3.id}}
  Method : PATCH
  Body   : { "status": "done" }


# ─────────────────────────────────────────────
# SCÉNARIO F3 — Devis accepté (webhook depuis email)
# Trigger : Gmail → Watch emails
# Filtre : objet contient "Accord devis" ou "j'accepte"
# ─────────────────────────────────────────────

Module 1 : Gmail → Watch emails
  Filter : Subject contains "Accord devis" OR "j'accepte" OR "je valide"

Module 2 : Tools → Text parser
  Pattern : DEV-\d{4}-\d{3}
  Text    : {{1.subject}}
  → Extraire le numéro de devis

Module 3 : HTTP → Marquer accepté + déclencher onboarding
  URL    : {AUTOFLOW_API_URL}/api/agents/devis
  Method : POST
  Body :
  {
    "action": "mark_accepted",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{DEVIS_AGENT_ID}",
    "devisNumber": "{{2.match}}"
  }

Module 4 : Gmail → Send an email (félicitations interne)
  To      : benoit.buon.lms@gmail.com
  Subject : 🎉 Devis {{2.match}} ACCEPTÉ !
  Content : {{1.from.value[].name}} a accepté la proposition. L'onboarding a été déclenché automatiquement.


# ── Déclencher manuellement depuis le dashboard ──
# Pour créer un devis sans passer par Make :
# curl -X POST {MAKE_WEBHOOK_DEVIS} \
#   -H "Content-Type: application/json" \
#   -d '{
#     "client_name": "Julie Laroche",
#     "client_email": "julie@gmail.com",
#     "lead_id": "UUID_LEAD",
#     "needs": "Préparer Hyrox Paris en novembre",
#     "goal": "Finir sous 1h30",
#     "budget": "500€",
#     "timeline": "4 mois"
#   }'


# ── Variables Vercel à ajouter ─────────────────
# DEVIS_AGENT_ID = (UUID depuis Supabase)


# ══════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════

# Test générer un devis complet
curl -X POST {AUTOFLOW_API_URL}/api/agents/devis \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "generate",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{DEVIS_AGENT_ID}",
    "briefData": {
      "client_name": "Julie Laroche",
      "client_email": "julie.test@gmail.com",
      "needs": "Préparation Hyrox Paris novembre 2026",
      "goal": "Finir en moins de 1h30, première course",
      "budget": "500€",
      "timeline": "4 mois",
      "context": "Active, fait de la salle 3x/semaine, jamais fait de CrossFit"
    }
  }'
# Attendu :
#   - Devis DEV-2026-XXX généré
#   - Email proposition envoyé à julie.test@gmail.com
#   - Email copie interne à Benoit
#   - 3 tâches de relance créées dans Supabase
#   - Lignes de devis adaptées au profil (8 semaines prépa Hyrox)

# Test relance J+5
curl -X POST {AUTOFLOW_API_URL}/api/agents/devis \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "followup",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{DEVIS_AGENT_ID}",
    "leadId": "UUID_LEAD_TEST",
    "followupDay": 5,
    "devisData": {
      "devis_number": "DEV-2026-001",
      "amount": 490,
      "client_email": "julie.test@gmail.com",
      "urgency_argument": "Je démarre un nouveau groupe en juin, 2 places restantes"
    }
  }'
# Attendu : email de relance avec levée d'objection + argument urgence

# Test marquer accepté
curl -X POST {AUTOFLOW_API_URL}/api/agents/devis \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "mark_accepted",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{DEVIS_AGENT_ID}",
    "leadId": "UUID_LEAD_TEST",
    "devisNumber": "DEV-2026-001"
  }'
# Attendu : lead → stage "won", onboarding déclenché automatiquement
