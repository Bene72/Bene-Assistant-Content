// ============================================
// AGENT COMMERCIAL — AutoFlow
// agents/commercial.js
// ============================================
// Gère : qualification leads, scoring, séquences email, CRM auto

import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const resend = new Resend(process.env.RESEND_API_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

// ============================================
// SYSTEM PROMPT — Agent Commercial
// ============================================
const COMMERCIAL_SYSTEM_PROMPT = "Tu es l'agent commercial IA de Benoit, coach fitness/CrossFit/Hyrox.\nTu qualifies les nouveaux prospects entrants et génères des emails de suivi personnalisés qui convertissent.\n\n## CONTEXTE BUSINESS\n- Offres : séance individuelle 70€ | pack 10 séances 600€ | coaching en ligne 150€/mois\n- Cible idéale : 25-45 ans, actif ou voulant le devenir, motivé, budget moyen-haut\n- Différenciation : spécialité Hyrox (rare), combo physique + en ligne, suivi personnalisé poussé\n- Capacité max : environ 20 clients actifs en simultané\n\n## SCORING LEADS (0-100)\n- Objectif clair (Hyrox, perte de poids, prise de masse, remise en forme) → +25 pts\n- Timeline courte (< 3 mois) → +20 pts\n- Budget évoqué ou profil CSP+ → +20 pts\n- Déjà pratiqué CrossFit/fitness → +15 pts\n- Localisation proche ou ok pour distanciel → +10 pts\n- Répond rapidement (< 2h) → +10 pts\n\n## RÈGLES DE CONVERSION\n1. Toujours proposer l'appel découverte gratuit 20 min en premier — jamais vendre directement\n2. Mettre en avant la spécialité Hyrox si le prospect mentionne une course ou de la compétition\n3. Utiliser les résultats clients concrets : \"un de mes clients a fini son premier Hyrox en 1h12 après 4 mois\"\n4. Ne jamais brader — le prix est une preuve de qualité\n5. Créer de l'urgence légitime : \"il me reste 2 créneaux ce mois-ci\"\n\n## SÉQUENCES EMAIL PAR PROFIL\n\n### Prospect Hyrox/Compétition\n- J+0 : Appel découverte + résultats clients Hyrox spécifiques\n- J+3 : Contenu valeur (plan type 8 semaines Hyrox)\n- J+7 : Témoignage client Hyrox + offre pack prépa\n- J+14 : Dernière chance avant fermeture du créneau\n\n### Prospect Fitness/Remise en forme\n- J+0 : Appel découverte + transformation avant/après\n- J+3 : Les 3 erreurs que font les gens seuls en salle\n- J+7 : Offre pack découverte (3 séances à tarif réduit)\n- J+14 : Relance douce + offre coaching en ligne si distance\n\n### Prospect En ligne\n- J+0 : Comment fonctionne le coaching en ligne + vidéo démo\n- J+3 : Résultats clients à distance\n- J+7 : Offre 1er mois à tarif découverte\n\n## FORMAT DE RÉPONSE (JSON strict)\n{\n  \"score\": 75,\n  \"profile\": \"hyrox|fitness|online|general\",\n  \"stage\": \"new|contacted|qualified|proposal|won|lost\",\n  \"next_action\": \"send_discovery_call|send_sequence|call_directly|disqualify\",\n  \"next_action_at\": \"2026-05-28T10:00:00Z\",\n  \"email_subject\": \"...\",\n  \"email_body\": \"...\",\n  \"notes\": \"...\",\n  \"disqualified\": false,\n  \"disqualification_reason\": null\n}";

// ============================================
// QUALIFICATION D'UN LEAD
// ============================================
export async function qualifyLead({ orgId, agentId, leadData }) {
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();

  const prompt = `
Qualifie ce lead pour ${org.name} :

**Données du formulaire :**
Nom : ${leadData.full_name || "Non renseigné"}
Email : ${leadData.email}
Entreprise : ${leadData.company || "Non renseigné"}
Taille : ${leadData.company_size || "Non renseignée"}
Poste : ${leadData.job_title || "Non renseigné"}
Budget estimé : ${leadData.budget || "Non renseigné"}
Timeline : ${leadData.timeline || "Non renseignée"}
Besoins exprimés : ${leadData.needs || "Non renseignés"}
Source : ${leadData.source || "Formulaire"}

Génère la qualification complète avec un email de suivi personnalisé.
Le premier email doit être chaleureux, personnalisé, et proposer un audit gratuit de 30 min.
`;

  const systemPrompt = COMMERCIAL_SYSTEM_PROMPT.replace("{org_name}", org.name);

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1500,
    system: systemPrompt,
    messages: [{ role: "user", content: prompt }],
  });

  const rawText = completion.content[0].text;
  const jsonMatch = rawText.match(/\{[\s\S]*\}/);
  const qualification = JSON.parse(jsonMatch[0]);

  // Sauvegarder le lead qualifié
  let leadId;
  const existingLead = leadData.id;

  if (existingLead) {
    await supabase.from("leads").update({
      score: qualification.score,
      stage: qualification.stage,
      budget_range: qualification.budget_range,
      timeline: qualification.timeline,
      pain_points: qualification.pain_points,
      next_action: qualification.next_action,
      next_action_at: qualification.next_action_at,
      notes: qualification.notes,
      last_contact_at: new Date().toISOString(),
    }).eq("id", existingLead);
    leadId = existingLead;
  } else {
    const { data: newLead } = await supabase.from("leads").insert({
      org_id: orgId,
      agent_id: agentId,
      email: leadData.email,
      full_name: leadData.full_name,
      company: leadData.company,
      phone: leadData.phone,
      source: leadData.source || "formulaire",
      score: qualification.score,
      stage: qualification.stage,
      budget_range: qualification.budget_range,
      timeline: qualification.timeline,
      pain_points: qualification.pain_points,
      next_action: qualification.next_action,
      next_action_at: qualification.next_action_at,
      notes: qualification.notes,
      last_contact_at: new Date().toISOString(),
    }).select().single();
    leadId = newLead.id;
  }

  // Logger l'activité
  await supabase.from("lead_activities").insert({
    lead_id: leadId,
    type: "score_updated",
    description: `Score calculé : ${qualification.score}/100 — Stage : ${qualification.stage}`,
    metadata: { qualification },
  });

  // Envoyer l'email de premier contact si score > 30
  if (qualification.score > 30 && !qualification.disqualified && qualification.email_body) {
    await sendLeadEmail({
      to: leadData.email,
      toName: leadData.full_name,
      fromName: org.name,
      subject: qualification.email_subject,
      body: qualification.email_body,
    });

    await supabase.from("lead_activities").insert({
      lead_id: leadId,
      type: "email_sent",
      description: `Email de qualification envoyé : "${qualification.email_subject}"`,
    });
  }

  // Event global
  await supabase.from("events").insert({
    org_id: orgId,
    type: "lead.qualified",
    source: agentId,
    data: { lead_id: leadId, score: qualification.score, stage: qualification.stage },
  });

  return { leadId, qualification };
}

// ============================================
// SÉQUENCE EMAIL AUTOMATISÉE
// ============================================
const EMAIL_SEQUENCES = {
  qualified: [
    { delay_days: 0, type: "first_contact" },
    { delay_days: 3, type: "value_proposition" },
    { delay_days: 7, type: "case_study" },
    { delay_days: 14, type: "last_chance" },
  ],
  proposal: [
    { delay_days: 1, type: "proposal_followup" },
    { delay_days: 4, type: "objection_handling" },
    { delay_days: 10, type: "decision_nudge" },
  ],
};

export async function generateSequenceEmail({ orgId, agentId, leadId, emailType }) {
  const [leadData, orgData] = await Promise.all([
    supabase.from("leads").select("*").eq("id", leadId).single(),
    supabase.from("organisations").select("*").eq("id", orgId).single(),
  ]);

  const lead = leadData.data;
  const org = orgData.data;

  const emailTemplates = {
    first_contact: `Génère un email de premier contact pour ce lead qualifié. Mentionne leur secteur, leur problème principal et propose un audit gratuit de 30 minutes.`,
    value_proposition: `Génère un email de relance J+3 qui présente 2-3 cas clients similaires avec des résultats chiffrés. Inclure un témoignage court.`,
    case_study: `Génère un email J+7 avec un cas client détaillé dans le même secteur. Focus sur le ROI et les économies de temps.`,
    last_chance: `Génère un email J+14 "dernière chance" avec une offre spéciale (audit offert ou remise). Créer l'urgence sans pression excessive.`,
    proposal_followup: `Génère un email de suivi de proposition J+1. Demander si des questions se posent et proposer un appel de 15 min.`,
    objection_handling: `Génère un email qui anticipe les 3 objections principales (coût, temps, ROI) et les traite avec des arguments factuels.`,
    decision_nudge: `Génère un email final de nudge à la décision. Rappeler les bénéfices clés et créer un sentiment d'urgence légitime.`,
  };

  const prompt = `
Lead : ${lead.full_name} (${lead.company})
Secteur : ${lead.enriched_data?.sector || "PME"}
Score : ${lead.score}/100
Pain points : ${lead.pain_points?.join(", ")}
Budget : ${lead.budget_range}
Timeline : ${lead.timeline}

${emailTemplates[emailType] || emailTemplates.first_contact}

Format réponse JSON : { "subject": "...", "body_html": "...", "body_text": "..." }
`;

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1200,
    system: `Tu rédiges des emails commerciaux B2B pour ${org.name}. 
Ton : professionnel, humain, jamais agressif. 
Longueur : 150-250 mots. 
Inclure toujours un CTA clair.
Répondre UNIQUEMENT en JSON.`,
    messages: [{ role: "user", content: prompt }],
  });

  const rawText = completion.content[0].text;
  const jsonMatch = rawText.match(/\{[\s\S]*\}/);
  const emailContent = JSON.parse(jsonMatch[0]);

  // Envoyer l'email
  await sendLeadEmail({
    to: lead.email,
    toName: lead.full_name,
    fromName: org.name,
    subject: emailContent.subject,
    body: emailContent.body_html,
  });

  await supabase.from("lead_activities").insert({
    lead_id: leadId,
    type: "email_sent",
    description: `Séquence "${emailType}" : "${emailContent.subject}"`,
    metadata: { email_type: emailType },
  });

  return emailContent;
}

// ============================================
// ENRICHISSEMENT LEAD (via recherche web)
// ============================================
export async function enrichLead({ leadId, orgId, agentId }) {
  const { data: lead } = await supabase.from("leads").select("*").eq("id", leadId).single();

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 800,
    tools: [{ type: "web_search_20250305", name: "web_search" }],
    system: "Tu enrichis les données d'un lead B2B. Recherche des infos sur l'entreprise et renvoie uniquement du JSON.",
    messages: [{
      role: "user",
      content: `Recherche ces infos sur l'entreprise "${lead.company}" :
      - Secteur d'activité principal
      - Taille approximative (employés)
      - Présence web/réseaux
      - Actualités récentes
      
      Renvoie JSON : { "sector": "...", "size": "...", "tech_stack": [], "recent_news": "...", "linkedin_url": "..." }`
    }],
  });

  const fullResponse = completion.content
    .map(item => (item.type === "text" ? item.text : ""))
    .filter(Boolean).join("\n");

  const jsonMatch = fullResponse.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    const enriched = JSON.parse(jsonMatch[0]);
    await supabase.from("leads").update({ enriched_data: enriched }).eq("id", leadId);
    return enriched;
  }
  return null;
}

// ============================================
// ENVOI EMAIL
// ============================================
async function sendLeadEmail({ to, toName, fromName, subject, body }) {
  return resend.emails.send({
    from: `${fromName} <commercial@autoflow.fr>`,
    to: `${toName || ""} <${to}>`,
    subject,
    html: body,
  });
}

// ============================================
// WEBHOOK HANDLER
// ============================================
export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();

  const token = req.headers["x-autoflow-token"];
  if (token !== process.env.WEBHOOK_SECRET) return res.status(401).end();

  const { action, orgId, agentId, leadData, leadId, emailType } = req.body;

  try {
    let result;
    switch (action) {
      case "qualify":
        result = await qualifyLead({ orgId, agentId, leadData });
        break;
      case "sequence_email":
        result = await generateSequenceEmail({ orgId, agentId, leadId, emailType });
        break;
      case "enrich":
        result = await enrichLead({ leadId, orgId, agentId });
        break;
      default:
        return res.status(400).json({ error: "Unknown action" });
    }
    return res.status(200).json({ success: true, data: result });
  } catch (err) {
    console.error("Commercial agent error:", err);
    return res.status(500).json({ error: err.message });
  }
}
