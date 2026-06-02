# ============================================
# MAKE.COM — SCÉNARIOS AGENTS 3 & 5
# + Variables Vercel + Tests
# ============================================


# ══════════════════════════════════════════════
# AGENT 3 — SATISFACTION & AVIS GOOGLE
# ══════════════════════════════════════════════

# ─────────────────────────────────────────────
# SCÉNARIO C1 — Message satisfaction J+1
# Trigger : Schedule → Every day at 10:00
# ─────────────────────────────────────────────

Module 1 : Schedule → Every day at 10:00

Module 2 : HTTP → Supabase (séances d'hier)
  URL    : {SUPABASE_URL}/rest/v1/tasks
           ?status=eq.done
           &title=like.%séance%
           &completed_at=gte.{yesterday_start}
           &completed_at=lte.{yesterday_end}
           &org_id=eq.{DEFAULT_ORG_ID}
           &select=id,title,metadata,org_id
  Method : GET
  Headers : apikey + Authorization

  Note : remplacer {yesterday_start} et {yesterday_end} par :
    {{formatDate(addDays(now, -1), "YYYY-MM-DDT00:00:00Z")}}
    {{formatDate(addDays(now, -1), "YYYY-MM-DDT23:59:59Z")}}

Module 3 : Tools → Iterator
  Array : {{2}}

Module 4 : HTTP → Envoyer satisfaction
  URL    : {AUTOFLOW_API_URL}/api/agents/satisfaction
  Method : POST
  Headers : x-autoflow-token: {WEBHOOK_SECRET}
  Body :
  {
    "action": "send_satisfaction",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{SATISFACTION_AGENT_ID}",
    "clientData": {
      "lead_id": "{{3.metadata.lead_id}}",
      "name": "{{3.metadata.client_name}}",
      "email": "{{3.metadata.client_email}}",
      "phone": "{{3.metadata.client_phone}}",
      "service_type": "{{3.metadata.service_type}}",
      "service_date": "{{formatDate(addDays(now,-1), "DD/MM/YYYY")}}",
      "goal": "{{3.metadata.client_goal}}",
      "session_notes": "{{3.title}}"
    }
  }


# ─────────────────────────────────────────────
# SCÉNARIO C2 — Analyser réponse client
# Trigger : Gmail → Watch emails (réponses au message satisfaction)
# ─────────────────────────────────────────────

Module 1 : Gmail → Watch emails
  Label : INBOX
  Filter : Objet contient "séance" OU "Comment s'est passée"
  Only unread : Yes

Module 2 : HTTP → Analyser la réponse
  URL    : {AUTOFLOW_API_URL}/api/agents/satisfaction
  Method : POST
  Body :
  {
    "action": "analyze_response",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{SATISFACTION_AGENT_ID}",
    "clientData": {
      "name": "{{1.from.value[].name}}",
      "email": "{{1.from.value[].address}}",
      "service_type": "coaching sportif",
      "lead_id": null
    },
    "clientResponse": "{{1.text}}"
  }

Module 3 : Router
  Route A : {{2.data.alert_human}} = true
  Route B : {{2.data.request_google_review}} = true
  Route C : tout le reste

Module 4A : Gmail → Send an email (ALERTE interne)
  To      : benoit.buon.lms@gmail.com
  Subject : 🚨 Client insatisfait — action requise
  Content : Voir le dashboard ou vérifier l'email d'alerte envoyé automatiquement

  Note : L'agent envoie déjà l'alerte détaillée par email
         Ce module est un double rappel Benoit si besoin

Module 4B : Gmail → Mark as read


# ─────────────────────────────────────────────
# SCÉNARIO C3 — Rapport mensuel satisfaction
# Trigger : 1er du mois à 9:30
# ─────────────────────────────────────────────

Module 1 : Schedule → Every month, day 1, at 09:30

Module 2 : HTTP → Rapport
  URL    : {AUTOFLOW_API_URL}/api/agents/satisfaction
  Method : POST
  Body :
  {
    "action": "monthly_report",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{SATISFACTION_AGENT_ID}"
  }
  → Rapport envoyé directement à Benoit par l'agent


# ── Variable env à ajouter dans Vercel ────────
# SATISFACTION_AGENT_ID = (UUID depuis Supabase)
# GOOGLE_REVIEW_LINK    = https://g.page/r/VOTRE_CODE/review
#
# Pour trouver ton lien Google :
# Google Maps → ta fiche → "Demander des avis" → copier le lien court


# ══════════════════════════════════════════════
# AGENT 5 — CONTENU RÉSEAUX
# ══════════════════════════════════════════════

# ─────────────────────────────────────────────
# SCÉNARIO D1 — Contenu semaine automatique
# Trigger : Chaque lundi à 7:00
# ─────────────────────────────────────────────

Module 1 : Schedule → Every week, Monday at 07:00

Module 2 : HTTP → Générer contenu semaine
  URL    : {AUTOFLOW_API_URL}/api/agents/contenu-reseaux
  Method : POST
  Headers : x-autoflow-token: {WEBHOOK_SECRET}
  Body :
  {
    "action": "week_content",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{CONTENU_AGENT_ID}",
    "weekTheme": "CrossFit et préparation Hyrox"
  }

  → Email avec les 3 contenus de la semaine envoyé automatiquement à Benoit
  → Il n'a plus qu'à copier/coller et publier


# ─────────────────────────────────────────────
# SCÉNARIO D2 — Calendrier mensuel
# Trigger : 25 du mois précédent à 8:00
# ─────────────────────────────────────────────

Module 1 : Schedule → Every month, day 25, at 08:00

Module 2 : HTTP → Calendrier mensuel
  URL    : {AUTOFLOW_API_URL}/api/agents/contenu-reseaux
  Method : POST
  Body :
  {
    "action": "monthly_calendar",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{CONTENU_AGENT_ID}",
    "month": "{{formatDate(addMonths(now, 1), "MMMM YYYY")}}"
  }


# ─────────────────────────────────────────────
# SCÉNARIO D3 — Témoignage → Contenu (webhook)
# Trigger : Webhooks → Custom webhook
# À appeler manuellement quand Benoit reçoit un bon retour client
# ─────────────────────────────────────────────

Module 1 : Webhooks → Custom webhook
  → URL à noter : MAKE_WEBHOOK_TESTIMONIAL

Module 2 : HTTP → Transformer témoignage
  URL    : {AUTOFLOW_API_URL}/api/agents/contenu-reseaux
  Method : POST
  Body :
  {
    "action": "testimonial_to_content",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{CONTENU_AGENT_ID}",
    "testimonial": "{{1.testimonial}}",
    "clientName": "{{1.client_name}}",
    "clientGoal": "{{1.client_goal}}"
  }

Module 3 : Gmail → Send an email
  To      : benoit.buon.lms@gmail.com
  Subject : ✨ 3 contenus générés depuis le témoignage de {{1.client_name}}
  Content :
    Post Instagram : {{2.data.post.caption}}
    ---
    Slide carrousel : {{2.data.carrousel_slide1.titre}}
    ---
    Concept Reel : {{2.data.reel_concept.concept}}

  → Benoit déclenche ce scénario en envoyant un curl ou via un bouton dans le dashboard

  Exemple curl pour déclencher :
  curl -X POST {MAKE_WEBHOOK_TESTIMONIAL} \
    -H "Content-Type: application/json" \
    -d '{
      "testimonial": "Bene m''a aidé à finir mon premier Hyrox en 1h18, c''est dingue !",
      "client_name": "Thomas",
      "client_goal": "Finir Hyrox Paris sous 1h30"
    }'


# ── Variable env à ajouter dans Vercel ────────
# CONTENU_AGENT_ID = (UUID depuis Supabase)


# ══════════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════════

# Test Agent Satisfaction — Envoyer message
curl -X POST {AUTOFLOW_API_URL}/api/agents/satisfaction \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "send_satisfaction",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{SATISFACTION_AGENT_ID}",
    "clientData": {
      "name": "Thomas Test",
      "email": "thomas.test@gmail.com",
      "service_type": "séance CrossFit 1h",
      "service_date": "hier",
      "goal": "Préparer Hyrox"
    }
  }'
# Attendu : email satisfaction envoyé à thomas.test@gmail.com

# Test Agent Satisfaction — Analyser réponse positive
curl -X POST {AUTOFLOW_API_URL}/api/agents/satisfaction \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "analyze_response",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{SATISFACTION_AGENT_ID}",
    "clientData": {
      "name": "Thomas Test",
      "email": "thomas.test@gmail.com",
      "service_type": "CrossFit"
    },
    "clientResponse": "Super séance ! Je suis épuisé mais content, merci Bene !"
  }'
# Attendu : sentiment_score >= 7, request_google_review: true, email avec lien avis Google

# Test Agent Satisfaction — Analyser réponse négative
curl -X POST {AUTOFLOW_API_URL}/api/agents/satisfaction \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "analyze_response",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{SATISFACTION_AGENT_ID}",
    "clientData": {
      "name": "Marie Test",
      "email": "marie.test@gmail.com",
      "service_type": "coaching en ligne"
    },
    "clientResponse": "Honnêtement pas très satisfaite, je trouve le suivi insuffisant"
  }'
# Attendu : alert_human: true, email alerte envoyé à Benoit, request_google_review: false

# Test Agent Contenu — Post simple
curl -X POST {AUTOFLOW_API_URL}/api/agents/contenu-reseaux \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "generate_post",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{CONTENU_AGENT_ID}",
    "postType": "post",
    "topic": "Les 3 erreurs que font les débutants en CrossFit"
  }'
# Attendu : caption complet, hashtags, hook, heure de publication

# Test Agent Contenu — Script Reel
curl -X POST {AUTOFLOW_API_URL}/api/agents/contenu-reseaux \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "generate_post",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{CONTENU_AGENT_ID}",
    "postType": "reel",
    "topic": "Ma préparation type pour un Hyrox — une semaine dans ma vie"
  }'
# Attendu : script complet 45s, structure hook/valeur/CTA, directions visuelles

# Test Agent Contenu — Calendrier mensuel
curl -X POST {AUTOFLOW_API_URL}/api/agents/contenu-reseaux \
  -H "x-autoflow-token: {WEBHOOK_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "monthly_calendar",
    "orgId": "{DEFAULT_ORG_ID}",
    "agentId": "{CONTENU_AGENT_ID}",
    "month": "Juillet 2026"
  }'
# Attendu : 12 posts planifiés, email calendrier envoyé à Benoit
