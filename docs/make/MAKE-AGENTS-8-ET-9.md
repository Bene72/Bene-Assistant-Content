# ============================================
# MAKE.COM — SCÉNARIOS AGENTS 8 & 9
# ============================================


# ══════════════════════════════════════════════
# AGENT 8 — COACH BUSINESS (rapport lundi)
# ══════════════════════════════════════════════

# ─────────────────────────────────────────────
# SCÉNARIO G1 — Rapport hebdo lundi 7h
# Trigger : Schedule → Every week, Monday 07:00
# ─────────────────────────────────────────────

Module 1 : Schedule
  → Every week
  → Day : Monday
  → Time : 07:00

Module 2 : HTTP → Générer et envoyer le rapport
  URL    : {AUTOFLOW_API_URL}/api/agents/coach-business
  Method : POST
  Headers :
    x-autoflow-token : {WEBHOOK_SECRET}
    Content-Type     : application/json
  Body :
  {
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{COACH_BUSINESS_AGENT_ID}"
  }
  Timeout : 60 secondes

  → L'agent collecte toutes les données, génère le rapport
     et l'envoie directement à Benoit par email.
  → Aucun module supplémentaire nécessaire.

Module 3 : Tools → Error handler (optionnel)
  → Si erreur → envoyer une notif Slack ou Gmail à Benoit
  Gmail subject : ⚠️ Rapport lundi non envoyé — vérifier AutoFlow


# ── Variable env à ajouter dans Vercel ────────
# COACH_BUSINESS_AGENT_ID = (UUID depuis Supabase)


# ══════════════════════════════════════════════
# AGENT 9 — ROI & REPORTING MENSUEL
# ══════════════════════════════════════════════

# ─────────────────────────────────────────────
# SCÉNARIO H1 — Rapport ROI mensuel (1er du mois)
# Trigger : Schedule → Every month, day 1, 08:00
# ─────────────────────────────────────────────

Module 1 : Schedule
  → Every month
  → Day of month : 1
  → Time : 08:00

Module 2 : HTTP → Générer le rapport ROI
  URL    : {AUTOFLOW_API_URL}/api/agents/roi-reporting
  Method : POST
  Headers :
    x-autoflow-token : {WEBHOOK_SECRET}
    Content-Type     : application/json
  Body :
  {
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{ROI_AGENT_ID}"
  }
  Timeout : 90 secondes

Module 3 : Filter
  Condition : {{2.success}} = true

Module 4 : Gmail → Send an email (copie interne)
  To      : benoit.buon.lms@gmail.com
  Subject : ✅ Rapport ROI {{formatDate(now, "MMMM YYYY")}} envoyé
  Content :
    ROI net ce mois : +{{2.data.roi_net}}€
    Multiplicateur : x{{2.data.roi_multiplier}}
    Rapport envoyé automatiquement à tes emails.

  Note : le rapport complet est déjà envoyé par l'agent.
         Ce module est juste un accusé de réception interne.


# ── Variable env à ajouter dans Vercel ────────
# ROI_AGENT_ID = (UUID depuis Supabase)


# ══════════════════════════════════════════════
# CRÉER LES AGENTS EN BASE — SUPABASE
# ══════════════════════════════════════════════
# Aller dans Supabase → Table Editor → agents → Insert row

# Agent Coach Business
{
  "org_id": "{DEFAULT_ORG_ID}",
  "name": "Agent Coach Business",
  "type": "reporting",
  "status": "active",
  "model": "claude-sonnet-4-20250514",
  "temperature": 0.3,
  "system_prompt": "Tu es le copilote business IA de Benoit, coach fitness CrossFit Hyrox à Nantes. Tu analyses les données de la semaine et génères un récap actionnable chaque lundi. Ton : direct, honnête, comme un bon associé."
}

# Agent ROI Reporting
{
  "org_id": "{DEFAULT_ORG_ID}",
  "name": "Agent ROI Reporting",
  "type": "reporting",
  "status": "active",
  "model": "claude-sonnet-4-20250514",
  "temperature": 0.2,
  "system_prompt": "Tu es l'analyste ROI d'AutoFlow pour Benoit coach à Nantes. Tu calcules et présentes la valeur concrète d'AutoFlow chaque mois. Sois précis, chiffré, et orienté valeur client."
}


# ══════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════

# Test Agent Coach Business (rapport lundi)
curl -X POST {AUTOFLOW_API_URL}/api/agents/coach-business \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{COACH_BUSINESS_AGENT_ID}"
  }'
# Attendu :
#   - Email "☕ Ton lundi business" reçu par Benoit
#   - Score semaine sur 10
#   - Accroche + bullets + action prioritaire + opportunité
#   - Métriques : leads, signés, heures économisées, automations

# Test Agent ROI Reporting (rapport mensuel)
curl -X POST {AUTOFLOW_API_URL}/api/agents/roi-reporting \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{ROI_AGENT_ID}"
  }'
# Attendu :
#   - Email "📊 Bilan [mois] — AutoFlow vous a rapporté X€ nets"
#   - ROI net calculé et affiché
#   - Décomposition valeur (temps + argent + prospects)
#   - Activité par agent
#   - Suggestion upsell si ROI > 5x


# ══════════════════════════════════════════════
# RÉCAP COMPLET — TOUS LES AGENTS AUTOFLOW
# ══════════════════════════════════════════════

# ── 9 agents déployés ─────────────────────────

# 1. agent-communication.js        → /api/agents/communication
#    Répond emails/chat, détecte sentiment, escalade

# 2. agent-commercial.js           → /api/agents/commercial
#    Qualifie leads, scoring, séquences email

# 3. agent-realisation.js          → /api/agents/realisation
#    Projets, tâches, rapports hebdo équipe

# 4. agent-acquisition-boost.js    → /api/agents/acquisition-boost
#    Multi-sources, réponse 5min, relances J+1/J+3/J+7

# 5. agent-relance-argent.js       → /api/agents/relance-argent
#    Devis, impayés, inactifs, renouvellements

# 6. agent-satisfaction.js         → /api/agents/satisfaction
#    Satisfaction J+1, détection sentiment, avis Google

# 7. agent-contenu-reseaux.js      → /api/agents/contenu-reseaux
#    Posts Instagram, Reels, carrousels, calendrier

# 8. agent-onboarding.js           → /api/agents/onboarding
#    Bienvenue, questionnaire, tâches, relances

# 9. agent-devis.js                → /api/agents/devis
#    Proposition commerciale, devis, relances signature

# 10. agent-coach-business.js      → /api/agents/coach-business
#     Rapport lundi matin copilote

# 11. agent-roi-reporting.js       → /api/agents/roi-reporting
#     Bilan ROI mensuel anti-churn

# ── 14 scénarios Make ─────────────────────────

# A1 : Prospect formulaire site → qualification
# A2 : Relances automatiques J+1/J+3/J+7
# B1 : Scan argent qui dort quotidien
# B2 : Relances devis non signés
# B3 : Rapport mensuel argent récupéré
# C1 : Message satisfaction J+1
# C2 : Analyse réponse + avis Google
# C3 : Rapport satisfaction mensuel
# D1 : Contenu semaine automatique (lundi)
# D2 : Calendrier mensuel Instagram
# D3 : Témoignage → contenu (webhook)
# E1 : Onboarding dès signature
# E2 : Relance questionnaire J+2
# E3 : Relance questionnaire J+5
# F1 : Générer devis depuis brief
# F2 : Relances devis automatiques
# F3 : Devis accepté → onboarding
# G1 : Rapport lundi matin (hebdo)
# H1 : Rapport ROI mensuel

# ── Variables Vercel complètes ─────────────────

# ANTHROPIC_API_KEY
# SUPABASE_URL
# SUPABASE_ANON_KEY
# SUPABASE_SERVICE_KEY
# RESEND_API_KEY
# WEBHOOK_SECRET
# AUTOFLOW_API_URL
# DEFAULT_ORG_ID
# COMM_AGENT_ID
# COMMERCIAL_AGENT_ID
# REAL_AGENT_ID
# ACQUISITION_AGENT_ID
# RELANCE_AGENT_ID
# SATISFACTION_AGENT_ID
# CONTENU_AGENT_ID
# ONBOARDING_AGENT_ID
# DEVIS_AGENT_ID
# COACH_BUSINESS_AGENT_ID
# ROI_AGENT_ID
# GOOGLE_REVIEW_LINK
