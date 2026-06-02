// ============================================
// AGENT ACQUISITION BOOST — AutoFlow
// api/agents/acquisition-boost.js
// ============================================
// Sources : site web, Instagram DM, Facebook Ads,
//           formulaire, Calendly, email entrant
// Fonctions : qualification IA, score priorité,
//             réponse < 5min, relances J+1/J+3/J+7,
//             notif lead chaud, appel découverte auto

import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const resend = new Resend(process.env.RESEND_API_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

// ============================================
// SYSTEM PROMPT — Acquisition Boost
// ============================================
const ACQUISITION_SYSTEM_PROMPT = `Tu es l'agent d'acquisition IA de {org_name}.
Tu traites les prospects entrants depuis toutes les sources et tu les convertis en clients.

CONTEXTE CLIENT
{org_context}

SCORING PRIORITÉ (0-100)
Calcule un score précis :
- Intention d'achat claire → +30 pts
- Timeline courte (< 1 mois) → +25 pts
- Budget mentionné ou profil CSP+ → +20 pts
- Problème urgent/douloureux → +15 pts
- Déjà client ou référé → +10 pts

PRIORITÉS
- Score 80-100 → CHAUD 🔥 — répondre en < 5 min, notifier immédiatement
- Score 50-79 → TIÈDE ⚡ — répondre en < 30 min, séquence nurturing
- Score 0-49 → FROID ❄️ — répondre en < 2h, contenu valeur

RÈGLES CONVERSION
1. Premier message : toujours chaleureux + proposition concrète (appel découverte, démo, RDV)
2. Inclure le lien de réservation si score >= 50
3. Personnaliser selon la source (Instagram = décontracté, email = pro, formulaire = structuré)
4. Jamais de vente directe au premier contact
5. Mentionner un résultat client similaire si pertinent

SÉQUENCES
J+0 : Email bienvenue + proposition appel découverte
J+1 : Si pas de réponse → relance courte (preuve sociale)
J+3 : Si toujours pas → valeur gratuite (conseil, ressource)
J+7 : Dernière relance + offre limitée si pertinent

FORMAT RÉPONSE JSON strict :
{
  "score": 85,
  "priority": "hot|warm|cold",
  "source_type": "instagram|facebook_ads|website|formulaire|calendly|email|referral",
  "response_message": "...",
  "response_channel": "email|instagram_dm|sms",
  "include_booking_link": true,
  "notify_human": true,
  "notify_reason": "Lead chaud score 85 — réponse immédiate recommandée",
  "sequence_type": "hyrox|fitness|online|general|b2b",
  "next_followup_days": 1,
  "tags": ["hyrox", "nantes", "compétition"],
  "estimated_value_euros": 490
}`;

// ============================================
// TRAITER UN NOUVEAU PROSPECT
// ============================================
export async function processNewProspect({ orgId, agentId, prospectData }) {
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  const systemPrompt = ACQUISITION_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  // Construire le prompt de qualification
  const qualificationPrompt = `
Nouveau prospect entrant — SOURCE : ${prospectData.source || "non précisée"}

Données collectées :
- Nom/Pseudo : ${prospectData.name || "Non renseigné"}
- Email : ${prospectData.email || "Non renseigné"}
- Téléphone : ${prospectData.phone || "Non renseigné"}
- Message/Demande : ${prospectData.message || prospectData.needs || "Non renseigné"}
- Budget évoqué : ${prospectData.budget || "Non mentionné"}
- Timeline : ${prospectData.timeline || "Non mentionnée"}
- Objectif : ${prospectData.goal || prospectData.objectif || "Non précisé"}
- Localisation : ${prospectData.location || "Non précisée"}
- Profil Instagram/Social : ${prospectData.social_handle || "Non renseigné"}
- Heure de la demande : ${new Date().toLocaleString("fr-FR")}

Qualifie ce prospect et génère une réponse personnalisée selon la source.
`;

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1200,
    system: systemPrompt,
    messages: [{ role: "user", content: qualificationPrompt }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const result = json ? JSON.parse(json[0]) : null;
  if (!result) throw new Error("Qualification échouée");

  // Créer ou mettre à jour le lead en base
  const { data: lead } = await supabase.from("leads").upsert({
    org_id: orgId,
    agent_id: agentId,
    email: prospectData.email,
    full_name: prospectData.name,
    phone: prospectData.phone,
    company: prospectData.company,
    source: prospectData.source || "inconnu",
    score: result.score,
    stage: result.score >= 50 ? "contacted" : "new",
    pain_points: [prospectData.message || prospectData.needs].filter(Boolean),
    notes: `Source: ${result.source_type} | Séquence: ${result.sequence_type} | Valeur estimée: ${result.estimated_value_euros}€`,
    last_contact_at: new Date().toISOString(),
    enriched_data: {
      priority: result.priority,
      tags: result.tags,
      estimated_value: result.estimated_value_euros,
      source_type: result.source_type,
    },
  }, { onConflict: "email,org_id" }).select().single();

  // Logger l'activité
  await supabase.from("lead_activities").insert({
    lead_id: lead.id,
    type: "score_updated",
    description: `Qualification automatique — Score: ${result.score}/100 — Priorité: ${result.priority}`,
    metadata: result,
  });

  // Envoyer la réponse au prospect
  if (prospectData.email && result.response_message) {
    const bookingLink = org.website || "https://calendly.com/benoit-coach";
    const emailBody = buildProspectEmail(result.response_message, org.name, bookingLink, result.include_booking_link);

    await resend.emails.send({
      from: `${org.name} <contact@autoflow.fr>`,
      to: prospectData.email,
      subject: buildSubjectLine(result, prospectData, org.name),
      html: emailBody,
    });

    await supabase.from("lead_activities").insert({
      lead_id: lead.id,
      type: "email_sent",
      description: `Réponse automatique J+0 envoyée (score ${result.score}/100)`,
    });
  }

  // Notifier si lead chaud
  if (result.notify_human && result.score >= 70) {
    await notifyHotLead({ org, lead, result, prospectData });
  }

  // Planifier les relances
  await scheduleFollowUps({ orgId, agentId, leadId: lead.id, result, prospectData });

  // Event global
  await supabase.from("events").insert({
    org_id: orgId,
    type: "lead.acquired",
    source: agentId,
    data: { lead_id: lead.id, score: result.score, priority: result.priority, source: result.source_type },
  });

  return { lead, qualification: result };
}

// ============================================
// PLANIFIER LES RELANCES J+1, J+3, J+7
// ============================================
async function scheduleFollowUps({ orgId, agentId, leadId, result, prospectData }) {
  const followUpDays = result.priority === "hot" ? [1, 3] : result.priority === "warm" ? [1, 3, 7] : [3, 7];

  for (const day of followUpDays) {
    const dueDate = new Date();
    dueDate.setDate(dueDate.getDate() + day);

    await supabase.from("tasks").insert({
      org_id: orgId,
      title: `Relance J+${day} — ${prospectData.name || prospectData.email}`,
      description: `Séquence: ${result.sequence_type} | Score: ${result.score} | Source: ${result.source_type}`,
      status: "todo",
      priority: result.priority === "hot" ? "urgent" : result.priority === "warm" ? "high" : "medium",
      assigned_by_agent: agentId,
      auto_generated: true,
      due_date: dueDate.toISOString(),
      metadata: { lead_id: leadId, followup_day: day, sequence_type: result.sequence_type },
    });
  }
}

// ============================================
// EXÉCUTER UNE RELANCE AUTOMATIQUE
// ============================================
export async function executeFollowUp({ orgId, agentId, leadId, followupDay }) {
  const { data: lead } = await supabase.from("leads").select("*").eq("id", leadId).single();
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  // Vérifier si le lead a déjà répondu — si oui, annuler la relance
  const { data: recentActivity } = await supabase
    .from("lead_activities")
    .select("*")
    .eq("lead_id", leadId)
    .eq("type", "lead_responded")
    .gte("created_at", new Date(Date.now() - followupDay * 86400000).toISOString());

  if (recentActivity?.length > 0) {
    return { skipped: true, reason: "Lead a déjà répondu" };
  }

  const followupTemplates = {
    1: {
      hot:   `Envoie une relance courte et directe J+1. Demande si {name} a eu le temps de regarder. Rappelle brièvement la valeur. Inclure lien Calendly.`,
      warm:  `Relance J+1 chaleureuse. Ajouter une preuve sociale (1 témoignage client similaire). Proposer l'appel découverte.`,
      cold:  `Relance J+1 avec un conseil gratuit utile selon son objectif. Pas de vente. Juste de la valeur.`,
    },
    3: {
      hot:   `Relance J+3 avec urgence légère : "il me reste 1 créneau cette semaine". Résultats d'un client similaire.`,
      warm:  `Relance J+3 avec contenu valeur (ex: "les 3 erreurs que font les gens seuls"). Proposer l'appel découverte.`,
      cold:  `Relance J+3 avec ressource gratuite. Lien programme PDF ou article de blog.`,
    },
    7: {
      hot:   `Dernière relance J+7. Offre spéciale limitée ou accès prioritaire. Ton direct.`,
      warm:  `Relance J+7 douce. "Je ferme ce créneau bientôt". Pas de pression excessive.`,
      cold:  `Dernier email J+7. Court. "Si tu changes d'avis, je suis là." Garder la relation.`,
    },
  };

  const template = followupTemplates[followupDay]?.[lead.enriched_data?.priority || "warm"] || followupTemplates[3].warm;
  const prompt = template.replace("{name}", lead.full_name?.split(" ")[0] || "toi");

  const systemPrompt = ACQUISITION_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 800,
    system: systemPrompt,
    messages: [{
      role: "user",
      content: `Lead : ${lead.full_name} — Objectif: ${lead.pain_points?.[0] || "non précisé"} — Score: ${lead.score}/100\n\n${prompt}\n\nRéponds JSON avec "response_message" uniquement.`
    }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const result = json ? JSON.parse(json[0]) : { response_message: raw };

  // Envoyer l'email de relance
  await resend.emails.send({
    from: `${org.name} <contact@autoflow.fr>`,
    to: lead.email,
    subject: `Re: Votre demande — ${org.name}`,
    html: buildProspectEmail(result.response_message, org.name, org.website, true),
  });

  await supabase.from("lead_activities").insert({
    lead_id: leadId,
    type: "email_sent",
    description: `Relance automatique J+${followupDay} envoyée`,
  });

  return { sent: true, day: followupDay };
}

// ============================================
// NOTIFIER LEAD CHAUD
// ============================================
async function notifyHotLead({ org, lead, result, prospectData }) {
  const { data: admins } = await supabase
    .from("users").select("email")
    .eq("org_id", org.id).in("role", ["owner", "admin"]);

  if (!admins?.length) return;

  await resend.emails.send({
    from: "AutoFlow <alerts@autoflow.fr>",
    to: admins.map(a => a.email),
    subject: `🔥 Lead chaud — ${prospectData.name || prospectData.email} (${result.score}/100)`,
    html: `
      <div style="font-family:sans-serif;max-width:500px">
        <h2 style="color:#f26419">🔥 Nouveau lead chaud !</h2>
        <table style="width:100%;border-collapse:collapse">
          <tr><td style="padding:8px;color:#666">Nom</td><td style="padding:8px;font-weight:600">${prospectData.name || "Non renseigné"}</td></tr>
          <tr style="background:#f9f9f9"><td style="padding:8px;color:#666">Email</td><td style="padding:8px">${prospectData.email}</td></tr>
          <tr><td style="padding:8px;color:#666">Source</td><td style="padding:8px">${result.source_type}</td></tr>
          <tr style="background:#f9f9f9"><td style="padding:8px;color:#666">Score</td><td style="padding:8px;font-weight:700;color:#f26419">${result.score}/100</td></tr>
          <tr><td style="padding:8px;color:#666">Objectif</td><td style="padding:8px">${prospectData.message || prospectData.needs || "Non précisé"}</td></tr>
          <tr style="background:#f9f9f9"><td style="padding:8px;color:#666">Valeur estimée</td><td style="padding:8px;font-weight:600">${result.estimated_value_euros}€/mois</td></tr>
        </table>
        <p style="color:#666;font-size:13px;margin-top:16px">${result.notify_reason}</p>
        <p style="font-size:13px;color:#666">L'agent a déjà envoyé une réponse automatique. Si tu veux personnaliser, réponds directement à ${prospectData.email}</p>
      </div>
    `,
  });
}

// ============================================
// HELPERS EMAIL
// ============================================
function buildSubjectLine(result, prospectData, orgName) {
  const firstName = prospectData.name?.split(" ")[0] || "";
  if (result.score >= 80) return `${firstName ? firstName + ", " : ""}on peut commencer quand tu veux — ${orgName}`;
  if (result.source_type === "instagram") return `Salut ! Suite à ton message 👋`;
  if (result.source_type === "facebook_ads") return `Merci pour ton intérêt — voici la suite`;
  return `Merci pour ta demande — ${orgName}`;
}

function buildProspectEmail(message, orgName, bookingLink, includeBooking) {
  return `
<!DOCTYPE html>
<html>
<body style="font-family:'Helvetica Neue',sans-serif;max-width:560px;margin:0 auto;color:#333;padding:20px">
  <div style="border-bottom:3px solid #f26419;padding-bottom:16px;margin-bottom:24px">
    <strong style="font-size:18px">${orgName}</strong>
  </div>
  ${message.split('\n').map(p => p.trim() ? `<p style="margin:0 0 14px;line-height:1.7">${p}</p>` : '').join('')}
  ${includeBooking && bookingLink ? `
  <div style="margin:28px 0;text-align:center">
    <a href="${bookingLink}" style="background:#f26419;color:#fff;padding:14px 28px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block">
      Réserver un appel découverte gratuit →
    </a>
  </div>` : ''}
  <p style="color:#999;font-size:12px;margin-top:32px;border-top:1px solid #eee;padding-top:16px">
    ${orgName} · Réponse automatisée par AutoFlow IA
  </p>
</body>
</html>`;
}

// ============================================
// WEBHOOK HANDLER PRINCIPAL
// ============================================
export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (req.headers["x-autoflow-token"] !== process.env.WEBHOOK_SECRET)
    return res.status(401).json({ error: "Unauthorized" });

  const { action, orgId, agentId, prospectData, leadId, followupDay } = req.body;

  try {
    let result;
    switch (action) {
      case "new_prospect":
        result = await processNewProspect({ orgId, agentId, prospectData });
        break;
      case "followup":
        result = await executeFollowUp({ orgId, agentId, leadId, followupDay });
        break;
      default:
        return res.status(400).json({ error: `Action inconnue: ${action}` });
    }
    return res.status(200).json({ success: true, data: result });
  } catch (err) {
    console.error("Acquisition boost error:", err);
    return res.status(500).json({ error: err.message });
  }
}
