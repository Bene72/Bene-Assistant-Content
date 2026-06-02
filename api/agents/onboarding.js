// ============================================
// AGENT ONBOARDING CLIENT — AutoFlow
// api/agents/onboarding.js
// ============================================
// Déclenché dès qu'un lead passe en "won"
// Étape 1 : Email de bienvenue personnalisé
// Étape 2 : Questionnaire initial (formulaire)
// Étape 3 : Création fiche client complète
// Étape 4 : Rappel documents à envoyer
// Étape 5 : Plan des prochaines étapes
// Étape 6 : Tâches internes auto-créées
// Étape 7 : Relance si questionnaire non rempli J+2/J+5

import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const resend = new Resend(process.env.RESEND_API_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

// ============================================
// SYSTEM PROMPT — Agent Onboarding
// ============================================
const ONBOARDING_SYSTEM_PROMPT = `Tu es l'agent d'onboarding IA de {org_name}.
Tu accueilles les nouveaux clients avec professionnalisme et chaleur.
Ton rôle : démarrer la relation sur les meilleures bases possibles.

CONTEXTE
{org_context}

PHILOSOPHIE ONBOARDING
- Le premier email est crucial — il conditionne la perception du coach
- Être précis sur les prochaines étapes — le client ne doit jamais se demander "et maintenant ?"
- Personnaliser chaque message avec l'objectif spécifique du client
- Créer de l'enthousiasme sans sur-promettre

SÉQUENCE ONBOARDING
J+0 : Email bienvenue chaleureux + questionnaire initial + prochaines étapes
J+2 : Relance questionnaire si non rempli (ton léger)
J+5 : Relance questionnaire si toujours non rempli (ton plus direct)
J+3 : Email "Voici ce qui t'attend" — programme général
J+7 : Check-in première semaine

FORMAT RÉPONSE JSON strict :
{
  "welcome_subject": "...",
  "welcome_message": "...",
  "questionnaire_intro": "...",
  "next_steps": ["étape 1", "étape 2", "étape 3"],
  "internal_tasks": [
    {"title": "...", "priority": "urgent|high|medium", "due_days": 1}
  ],
  "documents_needed": ["...", "..."],
  "tone_used": "...",
  "personalization_notes": "..."
}`;

// ============================================
// QUESTIONNAIRE INITIAL (HTML form)
// ============================================
function buildQuestionnaireHTML(clientName, orgName, webhookUrl) {
  const firstName = clientName?.split(" ")[0] || "toi";
  return `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Questionnaire initial — ${orgName}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'DM Sans', sans-serif; background: #f6f5f2; color: #1a1a1a; padding: 40px 20px; }
  .wrap { max-width: 600px; margin: 0 auto; }
  .header { background: #fff; border-radius: 12px 12px 0 0; padding: 32px; border-bottom: 3px solid #f26419; margin-bottom: 2px; }
  .header h1 { font-size: 22px; font-weight: 600; margin-bottom: 8px; }
  .header p { font-size: 14px; color: #6b6e7a; line-height: 1.6; }
  .form-card { background: #fff; border-radius: 0 0 12px 12px; padding: 32px; }
  .field { margin-bottom: 24px; }
  label { display: block; font-size: 13px; font-weight: 500; color: #333; margin-bottom: 8px; }
  label .req { color: #f26419; }
  input, textarea, select {
    width: 100%; padding: 12px 16px;
    border: 1px solid #e0ddd8; border-radius: 8px;
    font-family: 'DM Sans', sans-serif; font-size: 14px;
    color: #1a1a1a; background: #fafaf8;
    outline: none; transition: border-color 0.2s;
  }
  input:focus, textarea:focus, select:focus { border-color: #f26419; background: #fff; }
  textarea { min-height: 100px; resize: vertical; }
  .radio-group { display: flex; flex-direction: column; gap: 10px; }
  .radio-item { display: flex; align-items: center; gap: 10px; cursor: pointer; }
  .radio-item input[type="radio"] { width: auto; accent-color: #f26419; }
  .radio-item span { font-size: 14px; color: #333; }
  .scale-wrap { display: flex; gap: 8px; align-items: center; }
  .scale-btn {
    width: 40px; height: 40px; border: 1px solid #e0ddd8; border-radius: 8px;
    background: #fafaf8; font-size: 14px; font-weight: 500; cursor: pointer;
    transition: all 0.15s; display: flex; align-items: center; justify-content: center;
  }
  .scale-btn:hover, .scale-btn.selected { background: #f26419; color: #fff; border-color: #f26419; }
  .scale-labels { display: flex; justify-content: space-between; font-size: 11px; color: #999; margin-top: 6px; }
  .divider { height: 1px; background: #f0ede8; margin: 28px 0; }
  .section-title { font-size: 15px; font-weight: 600; color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid #f0ede8; }
  .submit-btn {
    width: 100%; padding: 16px; background: #f26419; color: #fff;
    border: none; border-radius: 8px; font-family: 'DM Sans', sans-serif;
    font-size: 15px; font-weight: 600; cursor: pointer; transition: opacity 0.2s;
    margin-top: 8px;
  }
  .submit-btn:hover { opacity: 0.9; }
  .submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .success { display: none; text-align: center; padding: 40px 20px; }
  .success-icon { font-size: 48px; margin-bottom: 16px; }
  .success h2 { font-size: 20px; font-weight: 600; margin-bottom: 8px; }
  .success p { font-size: 14px; color: #6b6e7a; line-height: 1.6; }
  .note { font-size: 12px; color: #999; margin-top: 6px; }
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>Bienvenue ${firstName} ! 🎉</h1>
    <p>Pour que ${orgName} puisse personnaliser ton suivi dès le premier jour, réponds à ces quelques questions. Ça prend 5 minutes.</p>
  </div>
  
  <div class="form-card" id="formCard">
    <!-- SECTION 1 : PROFIL -->
    <div class="section-title">Ton profil sportif</div>

    <div class="field">
      <label>Ton objectif principal <span class="req">*</span></label>
      <textarea id="objectif" placeholder="Ex: Finir Hyrox Paris en novembre sous 1h30, perdre 8kg, reprendre le sport après 2 ans d'arrêt..." required></textarea>
    </div>

    <div class="field">
      <label>Ton niveau sportif actuel <span class="req">*</span></label>
      <div class="radio-group">
        <label class="radio-item"><input type="radio" name="niveau" value="debutant"><span>Débutant — je reprends le sport</span></label>
        <label class="radio-item"><input type="radio" name="niveau" value="intermediaire"><span>Intermédiaire — je m'entraîne régulièrement</span></label>
        <label class="radio-item"><input type="radio" name="niveau" value="avance"><span>Avancé — je compète ou je m'entraîne intensément</span></label>
      </div>
    </div>

    <div class="field">
      <label>Fréquence d'entraînement actuelle</label>
      <select id="frequence">
        <option value="">Sélectionner...</option>
        <option value="0-1">0 à 1 fois par semaine</option>
        <option value="2-3">2 à 3 fois par semaine</option>
        <option value="4-5">4 à 5 fois par semaine</option>
        <option value="6+">6 fois et plus</option>
      </select>
    </div>

    <div class="field">
      <label>Motivations sur 10 — niveau de motivation actuel <span class="req">*</span></label>
      <div class="scale-wrap" id="scaleMotivation"></div>
      <div class="scale-labels"><span>😴 Pas motivé</span><span>🔥 Ultra motivé</span></div>
      <input type="hidden" id="motivation_score" value="">
    </div>

    <div class="divider"></div>

    <!-- SECTION 2 : SANTÉ -->
    <div class="section-title">Santé & contraintes</div>

    <div class="field">
      <label>Blessures ou douleurs actuelles</label>
      <textarea id="blessures" placeholder="Ex: Légère douleur au genou droit depuis 3 mois, ancienne entorse cheville... ou 'Aucune'" style="min-height:80px"></textarea>
      <p class="note">Ces informations restent confidentielles et permettent d'adapter ton programme.</p>
    </div>

    <div class="field">
      <label>Contre-indications médicales</label>
      <div class="radio-group">
        <label class="radio-item"><input type="radio" name="medical" value="non"><span>Non, aucune</span></label>
        <label class="radio-item"><input type="radio" name="medical" value="oui"><span>Oui — je précise dans les notes</span></label>
      </div>
    </div>

    <div class="field">
      <label>Disponibilités dans la semaine <span class="req">*</span></label>
      <textarea id="disponibilites" placeholder="Ex: Lundi et mercredi soir après 19h, samedi matin de 9h à 11h..." style="min-height:80px"></textarea>
    </div>

    <div class="divider"></div>

    <!-- SECTION 3 : ATTENTES -->
    <div class="section-title">Tes attentes</div>

    <div class="field">
      <label>Ce qui n'a pas fonctionné dans le passé</label>
      <textarea id="echecs" placeholder="Ex: J'ai essayé seul mais je manque de structure, j'ai arrêté faute de motivation..." style="min-height:80px"></textarea>
    </div>

    <div class="field">
      <label>Ce qui est important pour toi dans le coaching <span class="req">*</span></label>
      <textarea id="attentes" placeholder="Ex: Un suivi régulier, des programmes clairs, de la flexibilité, être challengé..."></textarea>
    </div>

    <div class="field">
      <label>As-tu une compétition ou une date cible ?</label>
      <input type="text" id="competition" placeholder="Ex: Hyrox Paris — 15 novembre 2026, ou 'Pas de date précise'">
    </div>

    <div class="field">
      <label>Quelque chose d'autre à nous dire ?</label>
      <textarea id="autres" placeholder="Tout ce qui pourrait aider à personnaliser ton accompagnement..." style="min-height:80px"></textarea>
    </div>

    <button class="submit-btn" onclick="submitForm()" id="submitBtn">
      Envoyer mon questionnaire →
    </button>
    <p class="note" style="text-align:center;margin-top:12px">Tes réponses sont transmises directement à ${orgName}</p>
  </div>

  <div class="success" id="successDiv">
    <div class="success-icon">🎯</div>
    <h2>Questionnaire envoyé !</h2>
    <p>Merci ${firstName} ! ${orgName} va analyser tes réponses et te contacter rapidement pour démarrer.<br><br>Surveille tes emails 📧</p>
  </div>
</div>

<script>
// Scale motivation
const scaleDiv = document.getElementById('scaleMotivation');
for (let i = 1; i <= 10; i++) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'scale-btn';
  btn.textContent = i;
  btn.onclick = () => {
    document.querySelectorAll('.scale-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    document.getElementById('motivation_score').value = i;
  };
  scaleDiv.appendChild(btn);
}

async function submitForm() {
  const objectif = document.getElementById('objectif').value.trim();
  const niveau = document.querySelector('input[name="niveau"]:checked')?.value;
  const disponibilites = document.getElementById('disponibilites').value.trim();
  const attentes = document.getElementById('attentes').value.trim();

  if (!objectif || !niveau || !disponibilites || !attentes) {
    alert('Merci de remplir les champs obligatoires (*)');
    return;
  }

  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Envoi en cours...';

  const data = {
    action: "questionnaire_completed",
    orgId: "${process.env.DEFAULT_ORG_ID || 'DEFAULT_ORG_ID'}",
    clientData: {
      objectif,
      niveau,
      frequence: document.getElementById('frequence').value,
      motivation_score: document.getElementById('motivation_score').value,
      blessures: document.getElementById('blessures').value,
      medical: document.querySelector('input[name="medical"]:checked')?.value,
      disponibilites,
      echecs: document.getElementById('echecs').value,
      attentes,
      competition: document.getElementById('competition').value,
      autres: document.getElementById('autres').value,
    }
  };

  try {
    await fetch('${webhookUrl}', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
  } catch(e) { /* silencieux */ }

  document.getElementById('formCard').style.display = 'none';
  document.getElementById('successDiv').style.display = 'block';
}
</script>
</body>
</html>`;
}

// ============================================
// ÉTAPE 1 — DÉCLENCHER L'ONBOARDING COMPLET
// ============================================
export async function startOnboarding({ orgId, agentId, leadId, planType }) {
  const { data: lead } = await supabase.from("leads").select("*").eq("id", leadId).single();
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  if (!lead || !lead.email) throw new Error("Lead introuvable ou email manquant");

  const systemPrompt = ONBOARDING_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  // Générer le contenu de bienvenue
  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1500,
    system: systemPrompt,
    messages: [{
      role: "user",
      content: `Nouveau client vient de signer.

Infos client :
- Prénom : ${lead.full_name?.split(" ")[0] || ""}
- Nom complet : ${lead.full_name}
- Email : ${lead.email}
- Objectif / Pain points : ${lead.pain_points?.join(", ") || "non précisé"}
- Source : ${lead.source || "non précisée"}
- Plan souscrit : ${planType || "Pro Coach 490€/mois"}
- Score qualification : ${lead.score}/100
- Notes : ${lead.notes || "aucune"}

Génère :
1. L'email de bienvenue chaleureux et personnalisé (200 mots max)
2. Les 3 prochaines étapes claires pour le client
3. La liste des tâches internes à créer pour Bene
4. Les documents éventuellement nécessaires

Rappelle l'objectif spécifique du client dans l'email. Tutoie le client. Ton : enthousiaste, pro, humain.
Réponds JSON strict.`
    }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const content = json ? JSON.parse(json[0]) : null;
  if (!content) throw new Error("Génération onboarding échouée");

  // URL questionnaire (hébergé sur Vercel)
  const questionnaireUrl = `${process.env.AUTOFLOW_API_URL}/questionnaire?lead=${leadId}&org=${orgId}`;

  // Envoyer l'email de bienvenue
  await resend.emails.send({
    from: `${org.name} <contact@autoflow.fr>`,
    replyTo: org.email,
    to: lead.email,
    subject: content.welcome_subject || `Bienvenue ${lead.full_name?.split(" ")[0] || ""} ! La suite se passe ici 🚀`,
    html: buildWelcomeEmail({
      message: content.welcome_message,
      nextSteps: content.next_steps,
      questionnaireUrl,
      questionnaireIntro: content.questionnaire_intro,
      org,
      lead,
      planType,
    }),
  });

  // Créer les tâches internes automatiquement
  const defaultTasks = [
    { title: `Créer fiche client — ${lead.full_name}`, priority: "urgent", due_days: 0 },
    { title: `Analyser questionnaire — ${lead.full_name}`, priority: "high", due_days: 2 },
    { title: `Créer programme semaines 1-2 — ${lead.full_name}`, priority: "high", due_days: 5 },
    { title: `Appel de lancement 30min — ${lead.full_name}`, priority: "high", due_days: 3 },
    { title: `Configurer suivi client — ${lead.full_name}`, priority: "medium", due_days: 7 },
  ];

  const allTasks = [...defaultTasks, ...(content.internal_tasks || [])];

  for (const task of allTasks) {
    const due = new Date();
    due.setDate(due.getDate() + (task.due_days || 0));
    await supabase.from("tasks").insert({
      org_id: orgId,
      title: task.title,
      priority: task.priority || "medium",
      status: "todo",
      assigned_by_agent: agentId,
      auto_generated: true,
      generation_context: `Onboarding — ${lead.full_name}`,
      due_date: due.toISOString(),
      metadata: { lead_id: leadId, onboarding: true },
    });
  }

  // Mettre à jour le lead en base
  await supabase.from("leads").update({
    stage: "won",
    last_contact_at: new Date().toISOString(),
    enriched_data: {
      ...lead.enriched_data,
      onboarding_started: new Date().toISOString(),
      plan_type: planType,
      questionnaire_sent: true,
      questionnaire_completed: false,
    },
  }).eq("id", leadId);

  // Logger
  await supabase.from("lead_activities").insert({
    lead_id: leadId,
    type: "onboarding_started",
    description: `Onboarding déclenché — email bienvenue + questionnaire envoyés`,
    metadata: { plan: planType, tasks_created: allTasks.length },
  });

  // Event
  await supabase.from("events").insert({
    org_id: orgId,
    type: "onboarding.started",
    source: agentId,
    data: { lead_id: leadId, client: lead.full_name, plan: planType },
  });

  return {
    success: true,
    client: lead.full_name,
    email_sent: true,
    tasks_created: allTasks.length,
    questionnaire_url: questionnaireUrl,
  };
}

// ============================================
// ÉTAPE 2 — TRAITER LE QUESTIONNAIRE REMPLI
// ============================================
export async function processQuestionnaire({ orgId, agentId, leadId, clientData }) {
  const { data: lead } = await supabase.from("leads").select("*").eq("id", leadId).single();
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  const systemPrompt = ONBOARDING_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  // Analyser les réponses et générer le plan personnalisé
  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 2000,
    system: systemPrompt,
    messages: [{
      role: "user",
      content: `Le client ${lead.full_name} vient de remplir son questionnaire.

RÉPONSES :
- Objectif principal : ${clientData.objectif}
- Niveau sportif : ${clientData.niveau}
- Fréquence actuelle : ${clientData.frequence}
- Motivation (1-10) : ${clientData.motivation_score}
- Blessures / contraintes : ${clientData.blessures || "Aucune"}
- Contre-indications médicales : ${clientData.medical}
- Disponibilités : ${clientData.disponibilites}
- Ce qui n'a pas marché avant : ${clientData.echecs || "Non précisé"}
- Attentes du coaching : ${clientData.attentes}
- Compétition cible : ${clientData.competition || "Aucune"}
- Autres infos : ${clientData.autres || "Aucune"}

Génère :
1. Un email de confirmation chaleureux qui résume ce que tu as compris
2. Le plan des 4 premières semaines adapté à son profil (général, pas détaillé)
3. Les tâches prioritaires internes pour Bene (créer le programme, planifier l'appel)
4. 3 points d'attention importants pour ce client

Format JSON avec :
{
  "welcome_subject": "...",
  "welcome_message": "...", 
  "four_week_plan": ["Semaine 1 : ...", "Semaine 2 : ...", "Semaine 3 : ...", "Semaine 4 : ..."],
  "internal_tasks": [{"title":"...","priority":"urgent|high|medium","due_days":0}],
  "attention_points": ["point 1", "point 2", "point 3"],
  "next_steps": ["étape 1", "étape 2"],
  "documents_needed": []
}`
    }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const analysis = json ? JSON.parse(json[0]) : null;
  if (!analysis) throw new Error("Analyse questionnaire échouée");

  // Envoyer l'email de confirmation avec le plan
  await resend.emails.send({
    from: `${org.name} <contact@autoflow.fr>`,
    replyTo: org.email,
    to: lead.email,
    subject: analysis.welcome_subject || `Ton plan est prêt, ${lead.full_name?.split(" ")[0]} ! 💪`,
    html: buildPlanEmail({ analysis, org, lead }),
  });

  // Notifier Benoit avec le résumé
  const { data: admins } = await supabase.from("users").select("email").eq("org_id", orgId).in("role", ["owner", "admin"]);
  if (admins?.length) {
    await resend.emails.send({
      from: "AutoFlow <onboarding@autoflow.fr>",
      to: admins.map(a => a.email),
      subject: `📋 Questionnaire rempli — ${lead.full_name} — À lire`,
      html: buildCoachSummaryEmail({ lead, clientData, analysis, org }),
    });
  }

  // Créer les tâches prioritaires
  for (const task of (analysis.internal_tasks || [])) {
    const due = new Date();
    due.setDate(due.getDate() + (task.due_days || 1));
    await supabase.from("tasks").insert({
      org_id: orgId,
      title: task.title,
      priority: task.priority,
      status: "todo",
      assigned_by_agent: agentId,
      auto_generated: true,
      generation_context: `Post-questionnaire — ${lead.full_name}`,
      due_date: due.toISOString(),
    });
  }

  // Marquer le questionnaire comme complété
  await supabase.from("leads").update({
    enriched_data: {
      ...lead.enriched_data,
      questionnaire_completed: true,
      questionnaire_data: clientData,
      attention_points: analysis.attention_points,
      four_week_plan: analysis.four_week_plan,
    },
  }).eq("id", leadId);

  await supabase.from("lead_activities").insert({
    lead_id: leadId,
    type: "questionnaire_completed",
    description: "Questionnaire rempli — plan 4 semaines généré — email confirmation envoyé",
  });

  return { success: true, plan: analysis.four_week_plan, tasks_created: analysis.internal_tasks?.length };
}

// ============================================
// ÉTAPE 3 — RELANCE QUESTIONNAIRE NON REMPLI
// ============================================
export async function remindQuestionnaire({ orgId, agentId, leadId, reminderDay }) {
  const { data: lead } = await supabase.from("leads").select("*").eq("id", leadId).single();
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();

  // Vérifier si le questionnaire est déjà rempli
  if (lead.enriched_data?.questionnaire_completed) {
    return { skipped: true, reason: "Questionnaire déjà complété" };
  }

  const firstName = lead.full_name?.split(" ")[0] || "";
  const questionnaireUrl = `${process.env.AUTOFLOW_API_URL}/questionnaire?lead=${leadId}&org=${orgId}`;

  const messages = {
    2: {
      subject: `${firstName}, tu as oublié quelque chose 😄`,
      body: `Salut ${firstName} !\n\nContent de t'avoir à bord ! Je voulais juste te rappeler que ton questionnaire initial est prêt à remplir — ça prend 5 minutes et ça me permet de personnaliser ton programme dès le début.\n\nPlus vite tu le remplis, plus vite on démarre sérieusement ! 💪`,
    },
    5: {
      subject: `Dernier rappel questionnaire — ${firstName}`,
      body: `Salut ${firstName},\n\nJe vois que le questionnaire n'est pas encore rempli. Sans tes réponses, je ne peux pas créer ton programme personnalisé et on perd du temps précieux.\n\nPrends 5 minutes maintenant — c'est important pour que ton accompagnement soit vraiment adapté à toi.`,
    },
  };

  const msg = messages[reminderDay] || messages[2];

  await resend.emails.send({
    from: `${org.name} <contact@autoflow.fr>`,
    replyTo: org.email,
    to: lead.email,
    subject: msg.subject,
    html: buildReminderEmail(msg.body, questionnaireUrl, org, lead),
  });

  await supabase.from("lead_activities").insert({
    lead_id: leadId,
    type: "questionnaire_reminder",
    description: `Relance questionnaire J+${reminderDay} envoyée`,
  });

  return { sent: true, day: reminderDay };
}

// ============================================
// HELPERS EMAIL
// ============================================
function buildWelcomeEmail({ message, nextSteps, questionnaireUrl, questionnaireIntro, org, lead, planType }) {
  const firstName = lead.full_name?.split(" ")[0] || "";
  return `
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',sans-serif;max-width:580px;margin:0 auto;color:#333;padding:0">
  <div style="background:#f26419;padding:28px 32px;border-radius:12px 12px 0 0">
    <h1 style="color:#fff;margin:0;font-size:24px">Bienvenue ${firstName} ! 🎉</h1>
    <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px">${planType || "Pro Coach"} — ${org.name}</p>
  </div>
  <div style="background:#fff;padding:32px;border:1px solid #eee;border-top:none;border-radius:0 0 12px 12px">
    ${message.split('\n').map(p => p.trim() ? `<p style="margin:0 0 14px;line-height:1.7;font-size:15px">${p}</p>` : '').join('')}

    <div style="background:#fff8f3;border-left:3px solid #f26419;border-radius:4px;padding:16px 20px;margin:24px 0">
      <p style="margin:0 0 10px;font-weight:600;font-size:14px">📋 ${questionnaireIntro || "Première étape — ton questionnaire initial"}</p>
      <a href="${questionnaireUrl}" style="display:inline-block;background:#f26419;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:600;font-size:14px">
        Remplir mon questionnaire →
      </a>
      <p style="margin:10px 0 0;font-size:12px;color:#999">5 minutes · Confidentiel · Indispensable pour ton programme</p>
    </div>

    ${nextSteps?.length ? `
    <div style="margin:24px 0">
      <p style="font-weight:600;font-size:14px;margin-bottom:14px">La suite se passe comme ça :</p>
      ${nextSteps.map((step, i) => `
        <div style="display:flex;gap:12px;margin-bottom:10px;align-items:flex-start">
          <div style="width:24px;height:24px;border-radius:50%;background:#f26419;color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px">${i+1}</div>
          <p style="margin:0;font-size:14px;line-height:1.5;color:#444">${step}</p>
        </div>`).join('')}
    </div>` : ''}

    <p style="color:#888;font-size:13px;margin-top:24px;border-top:1px solid #eee;padding-top:16px">
      ${org.name} · Réponds directement à cet email si tu as des questions
    </p>
  </div>
</body></html>`;
}

function buildPlanEmail({ analysis, org, lead }) {
  const firstName = lead.full_name?.split(" ")[0] || "";
  return `
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',sans-serif;max-width:580px;margin:0 auto;color:#333;padding:0">
  <div style="background:#1a1a1a;padding:28px 32px;border-radius:12px 12px 0 0">
    <h1 style="color:#fff;margin:0;font-size:22px">Ton plan est prêt, ${firstName} 💪</h1>
  </div>
  <div style="background:#fff;padding:32px;border:1px solid #eee;border-top:none;border-radius:0 0 12px 12px">
    ${analysis.welcome_message.split('\n').map(p => p.trim() ? `<p style="margin:0 0 14px;line-height:1.7">${p}</p>` : '').join('')}

    ${analysis.four_week_plan?.length ? `
    <div style="margin:24px 0">
      <p style="font-weight:600;font-size:15px;margin-bottom:16px">Tes 4 premières semaines :</p>
      ${analysis.four_week_plan.map((week, i) => `
        <div style="padding:12px 16px;background:${i%2===0?'#f9f9f9':'#fff'};border-radius:6px;margin-bottom:8px;border-left:3px solid #f26419">
          <p style="margin:0;font-size:14px;line-height:1.5">${week}</p>
        </div>`).join('')}
    </div>` : ''}

    ${analysis.next_steps?.length ? `
    <div style="background:#fff8f3;border-radius:8px;padding:16px 20px;margin:20px 0">
      <p style="font-weight:600;font-size:14px;margin-bottom:10px">Prochaines étapes :</p>
      ${analysis.next_steps.map(s => `<p style="margin:0 0 8px;font-size:14px">→ ${s}</p>`).join('')}
    </div>` : ''}

    <p style="color:#888;font-size:12px;margin-top:24px;border-top:1px solid #eee;padding-top:14px">${org.name}</p>
  </div>
</body></html>`;
}

function buildCoachSummaryEmail({ lead, clientData, analysis, org }) {
  return `
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',sans-serif;max-width:600px;margin:0 auto;color:#333;padding:20px">
  <h2>📋 Questionnaire rempli — ${lead.full_name}</h2>
  <table style="width:100%;border-collapse:collapse;border:1px solid #eee;border-radius:8px;overflow:hidden;margin:16px 0">
    <tr style="background:#f9f9f9"><td style="padding:10px;color:#888;font-size:13px;width:40%">Objectif</td><td style="padding:10px;font-size:13px">${clientData.objectif}</td></tr>
    <tr><td style="padding:10px;color:#888;font-size:13px">Niveau</td><td style="padding:10px;font-size:13px">${clientData.niveau}</td></tr>
    <tr style="background:#f9f9f9"><td style="padding:10px;color:#888;font-size:13px">Motivation</td><td style="padding:10px;font-size:13px;font-weight:600;color:#f26419">${clientData.motivation_score}/10</td></tr>
    <tr><td style="padding:10px;color:#888;font-size:13px">Disponibilités</td><td style="padding:10px;font-size:13px">${clientData.disponibilites}</td></tr>
    <tr style="background:#f9f9f9"><td style="padding:10px;color:#888;font-size:13px">Blessures</td><td style="padding:10px;font-size:13px">${clientData.blessures || "Aucune"}</td></tr>
    <tr><td style="padding:10px;color:#888;font-size:13px">Compétition cible</td><td style="padding:10px;font-size:13px">${clientData.competition || "Aucune"}</td></tr>
  </table>
  ${analysis.attention_points?.length ? `
  <div style="background:#fdf0f0;border-left:3px solid #e24b4a;padding:14px;border-radius:4px;margin:16px 0">
    <strong style="font-size:13px;color:#e24b4a">⚠️ Points d'attention</strong>
    <ul style="margin:8px 0 0;padding-left:18px">${analysis.attention_points.map(p => `<li style="font-size:13px;margin-bottom:5px">${p}</li>`).join('')}</ul>
  </div>` : ''}
  <p style="font-size:12px;color:#999">Généré par AutoFlow — ${org.name}</p>
</body></html>`;
}

function buildReminderEmail(body, questionnaireUrl, org, lead) {
  return `
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',sans-serif;max-width:520px;margin:0 auto;color:#333;padding:20px">
  <div style="border-bottom:3px solid #f26419;padding-bottom:12px;margin-bottom:20px"><strong>${org.name}</strong></div>
  ${body.split('\n').map(p => p.trim() ? `<p style="margin:0 0 14px;line-height:1.7">${p}</p>` : '').join('')}
  <div style="text-align:center;margin:24px 0">
    <a href="${questionnaireUrl}" style="background:#f26419;color:#fff;padding:14px 28px;text-decoration:none;border-radius:6px;font-weight:600;display:inline-block">
      Remplir maintenant →
    </a>
  </div>
  <p style="color:#999;font-size:12px;border-top:1px solid #eee;padding-top:14px">${org.name}</p>
</body></html>`;
}

// ============================================
// ROUTE : Afficher le questionnaire (GET)
// ============================================
export async function serveQuestionnaire(req, res) {
  const { lead, org } = req.query;
  if (!lead || !org) return res.status(400).send("Paramètres manquants");

  const { data: leadData } = await supabase.from("leads").select("full_name").eq("id", lead).single();
  const { data: orgData } = await supabase.from("organisations").select("name").eq("id", org).single();

  const webhookUrl = `${process.env.AUTOFLOW_API_URL}/api/agents/onboarding`;
  const html = buildQuestionnaireHTML(
    leadData?.full_name || "vous",
    orgData?.name || "votre coach",
    webhookUrl
  );

  res.setHeader("Content-Type", "text/html");
  return res.status(200).send(html);
}

// ============================================
// WEBHOOK HANDLER
// ============================================
export default async function handler(req, res) {
  // GET → afficher le questionnaire
  if (req.method === "GET") return serveQuestionnaire(req, res);

  if (req.method !== "POST") return res.status(405).end();

  const { action, orgId, agentId, leadId, planType, clientData, reminderDay } = req.body;

  // Questionnaire complété (appelé depuis le formulaire HTML côté client)
  if (action === "questionnaire_completed") {
    const token = req.headers["x-autoflow-token"];
    if (token && token !== process.env.WEBHOOK_SECRET) return res.status(401).end();
    try {
      const result = await processQuestionnaire({ orgId, agentId: agentId || process.env.ONBOARDING_AGENT_ID, leadId, clientData });
      return res.status(200).json({ success: true, data: result });
    } catch (err) {
      return res.status(500).json({ error: err.message });
    }
  }

  // Actions internes protégées par token
  if (req.headers["x-autoflow-token"] !== process.env.WEBHOOK_SECRET)
    return res.status(401).json({ error: "Unauthorized" });

  try {
    let result;
    switch (action) {
      case "start":
        result = await startOnboarding({ orgId, agentId, leadId, planType });
        break;
      case "remind_questionnaire":
        result = await remindQuestionnaire({ orgId, agentId, leadId, reminderDay });
        break;
      default:
        return res.status(400).json({ error: `Action inconnue: ${action}` });
    }
    return res.status(200).json({ success: true, data: result });
  } catch (err) {
    console.error("Onboarding agent error:", err);
    return res.status(500).json({ error: err.message });
  }
}
