// ============================================
// AGENT RELANCE ARGENT — AutoFlow
// api/agents/relance-argent.js
// ============================================
// Récupère l'argent qui dort :
// → Devis non signés
// → Factures impayées
// → Fins de pack
// → Clients inactifs à relancer
// → Renouvellements à proposer

import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const resend = new Resend(process.env.RESEND_API_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

// ============================================
// TYPES DE RELANCES & URGENCE
// ============================================
const RELANCE_CONFIG = {
  devis_non_signe: {
    label: "Devis non signé",
    emoji: "📋",
    urgency_days: [2, 5, 10, 20],
    max_relances: 4,
    tone: "pro et direct",
    cta: "signer le devis",
  },
  facture_impayee: {
    label: "Facture impayée",
    emoji: "💰",
    urgency_days: [3, 7, 14, 30],
    max_relances: 4,
    tone: "ferme mais courtois",
    cta: "procéder au règlement",
  },
  fin_de_pack: {
    label: "Fin de pack",
    emoji: "📦",
    urgency_days: [7, 3, 1],      // avant la fin
    max_relances: 3,
    tone: "chaleureux et valorisant",
    cta: "renouveler le pack",
  },
  client_inactif: {
    label: "Client inactif",
    emoji: "💤",
    urgency_days: [14, 30, 60],
    max_relances: 3,
    tone: "humain et sans pression",
    cta: "reprendre les séances",
  },
  renouvellement: {
    label: "Renouvellement",
    emoji: "🔄",
    urgency_days: [30, 14, 7],    // avant l'échéance
    max_relances: 3,
    tone: "positif et axé résultats",
    cta: "renouveler l'abonnement",
  },
};

// ============================================
// SYSTEM PROMPT — Agent Relance Argent
// ============================================
const RELANCE_SYSTEM_PROMPT = `Tu es l'agent de relance financière IA de {org_name}.
Tu rédiges des messages de relance qui récupèrent l'argent qui dort, sans nuire à la relation client.

CONTEXTE
{org_context}

PHILOSOPHIE
- La relance doit préserver la relation en priorité
- Ton adapté : ferme pour les impayés, chaleureux pour les inactifs
- Toujours rappeler la valeur reçue avant de demander le paiement
- Offrir une porte de sortie facile (lien paiement, lien réservation)
- Jamais d'accusation, toujours des questions ouvertes si problème

RÈGLES PAR TYPE
Devis non signé :
- J+2 : "Tu as eu le temps de regarder ?" — léger, sans pression
- J+5 : Lever une objection probable (prix, délai, confiance)
- J+10 : Urgence légère ("je démarre d'autres projets")
- J+20 : Dernière chance + modification possible

Facture impayée :
- J+3 : Rappel doux — "peut-être un oubli ?"
- J+7 : Rappel direct avec lien de paiement
- J+14 : Ferme — conséquences possibles mentionnées
- J+30 : Mise en demeure amiable

Fin de pack :
- J-7 : "Tu as X séances restantes — on en parle ?"
- J-3 : Valoriser les progrès, proposer le renouvellement
- J-1 : Dernière chance avant expiration

Client inactif :
- J+14 : Message chaleureux — "comment tu vas ?"
- J+30 : Proposition de reprise avec offre de retour
- J+60 : Dernier contact — laisser la porte ouverte

FORMAT RÉPONSE JSON strict :
{
  "subject": "...",
  "message": "...",
  "tone_used": "...",
  "amount_at_stake_euros": 490,
  "urgency_level": "low|medium|high|critical",
  "include_payment_link": true,
  "include_booking_link": false,
  "suggested_next_step": "...",
  "stop_sequence": false,
  "stop_reason": null
}`;

// ============================================
// SCAN AUTOMATIQUE — tout ce qui dort
// ============================================
export async function scanMoneyToRecover({ orgId }) {
  const now = new Date();
  const results = { devis: [], factures: [], packs: [], inactifs: [], total_at_stake: 0 };

  // 1. DEVIS NON SIGNÉS (depuis les tâches avec metadata type="devis")
  const { data: devisTasks } = await supabase
    .from("tasks")
    .select("*")
    .eq("org_id", orgId)
    .eq("status", "todo")
    .like("title", "%devis%")
    .lt("created_at", new Date(now - 2 * 86400000).toISOString());

  results.devis = devisTasks || [];

  // 2. LEADS "PROPOSAL" SANS RÉPONSE (proxy pour devis)
  const { data: proposals } = await supabase
    .from("leads")
    .select("*")
    .eq("org_id", orgId)
    .eq("stage", "proposal")
    .lt("last_contact_at", new Date(now - 2 * 86400000).toISOString());

  // 3. CLIENTS INACTIFS (stage "won" mais pas contactés depuis 14j)
  const { data: inactifs } = await supabase
    .from("leads")
    .select("*")
    .eq("org_id", orgId)
    .eq("stage", "won")
    .lt("last_contact_at", new Date(now - 14 * 86400000).toISOString());

  results.inactifs = inactifs || [];

  // 4. PACKS EN FIN DE VIE
  const { data: packLeads } = await supabase
    .from("leads")
    .select("*")
    .eq("org_id", orgId)
    .eq("stage", "won")
    .not("enriched_data->pack_sessions_total", "is", null);

  results.packs = (packLeads || []).filter(l => {
    const total = parseInt(l.enriched_data?.pack_sessions_total || 0);
    const used = parseInt(l.enriched_data?.pack_sessions_used || 0);
    return (total - used) <= 2;
  });

  // Calculer le montant total en jeu
  results.total_at_stake =
    (proposals?.length || 0) * 490 +
    (results.inactifs.length) * 150 +
    (results.packs.length) * 600;

  return results;
}

// ============================================
// GÉNÉRER ET ENVOYER UNE RELANCE
// ============================================
export async function sendRelance({ orgId, agentId, relanceType, targetData }) {
  const config = RELANCE_CONFIG[relanceType];
  if (!config) throw new Error(`Type de relance inconnu: ${relanceType}`);

  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  // Vérifier le nombre de relances déjà envoyées
  const { data: pastRelances } = await supabase
    .from("lead_activities")
    .select("id")
    .eq("lead_id", targetData.lead_id)
    .eq("type", `relance_${relanceType}`);

  const relanceCount = pastRelances?.length || 0;

  // Ne pas relancer au-delà du max
  if (relanceCount >= config.max_relances) {
    return { skipped: true, reason: `Max relances atteint (${config.max_relances})` };
  }

  const systemPrompt = RELANCE_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  const prompt = buildRelancePrompt({ relanceType, config, targetData, relanceCount, org });

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 900,
    system: systemPrompt,
    messages: [{ role: "user", content: prompt }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const result = json ? JSON.parse(json[0]) : null;
  if (!result) throw new Error("Génération relance échouée");

  // Ne pas envoyer si l'IA recommande d'arrêter
  if (result.stop_sequence) {
    return { skipped: true, reason: result.stop_reason };
  }

  // Envoyer l'email
  if (targetData.email) {
    const paymentLinks = buildPaymentLinksSection(relanceType, org, result, targetData);

    await resend.emails.send({
      from: `${org.name} <contact@autoflow.fr>`,
      replyTo: org.email,
      to: targetData.email,
      subject: result.subject,
      html: buildRelanceEmail(result.message, org, paymentLinks),
    });
  }

  // Logger
  if (targetData.lead_id) {
    await supabase.from("lead_activities").insert({
      lead_id: targetData.lead_id,
      type: `relance_${relanceType}`,
      description: `Relance #${relanceCount + 1} — ${config.label} — ${result.amount_at_stake_euros}€ en jeu`,
      metadata: { relance_count: relanceCount + 1, urgency: result.urgency_level, subject: result.subject },
    });
  }

  // Notifier si montant critique
  if (result.urgency_level === "critical" || result.amount_at_stake_euros >= 300) {
    await notifyCriticalRelance({ org, targetData, config, result, relanceCount });
  }

  // Event
  await supabase.from("events").insert({
    org_id: orgId,
    type: `relance.${relanceType}`,
    source: agentId,
    data: {
      lead_id: targetData.lead_id,
      relance_count: relanceCount + 1,
      amount: result.amount_at_stake_euros,
      urgency: result.urgency_level,
    },
  });

  return { sent: true, relance_count: relanceCount + 1, subject: result.subject, amount: result.amount_at_stake_euros };
}

// ============================================
// RAPPORT MENSUEL "ARGENT RÉCUPÉRÉ"
// ============================================
export async function generateMoneyReport({ orgId, agentId }) {
  const monthAgo = new Date();
  monthAgo.setMonth(monthAgo.getMonth() - 1);

  // Relances envoyées ce mois
  const { data: relancesLogs } = await supabase
    .from("lead_activities")
    .select("*")
    .eq("org_id", orgId)
    .like("type", "relance_%")
    .gte("created_at", monthAgo.toISOString());

  // Leads qui ont avancé (contacted → qualified → won) après relance
  const { data: conversions } = await supabase
    .from("leads")
    .select("*")
    .eq("org_id", orgId)
    .eq("stage", "won")
    .gte("updated_at", monthAgo.toISOString());

  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();

  const totalRelances = relancesLogs?.length || 0;
  const estimatedRecovered = (conversions?.length || 0) * 490; // estimation moyenne

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 800,
    system: `Tu génères un rapport mensuel "argent récupéré" concis et impactant pour un indépendant. Format HTML.`,
    messages: [{
      role: "user",
      content: `
Génère le rapport mensuel :
- ${totalRelances} relances envoyées automatiquement
- ${conversions?.length || 0} clients convertis/renouvelés après relance
- Montant estimé récupéré : ${estimatedRecovered}€
- Organisation : ${org.name}

Rapport HTML court (max 200 mots), avec les chiffres clés en gros, un message positif, et la liste des actions du mois prochain.
`,
    }],
  });

  const reportHtml = completion.content[0].text;

  // Envoyer aux admins
  const { data: admins } = await supabase.from("users").select("email").eq("org_id", orgId).in("role", ["owner", "admin"]);

  if (admins?.length) {
    await resend.emails.send({
      from: "AutoFlow <reports@autoflow.fr>",
      to: admins.map(a => a.email),
      subject: `💰 Rapport mensuel Relance Argent — ${org.name}`,
      html: reportHtml,
    });
  }

  return { totalRelances, estimatedRecovered, reportHtml };
}

// ============================================
// HELPERS
// ============================================
function buildRelancePrompt({ relanceType, config, targetData, relanceCount, org }) {
  return `
Type de relance : ${config.label} (#${relanceCount + 1} sur ${config.max_relances} max)
Ton requis : ${config.tone}
CTA objectif : ${config.cta}

Client :
- Nom : ${targetData.name || "Non renseigné"}
- Email : ${targetData.email}
- Montant en jeu : ${targetData.amount_euros || "Non précisé"}€
- Contexte : ${targetData.context || "Non précisé"}
- Dernière interaction : ${targetData.last_contact || "Inconnue"}
- Historique : ${targetData.history || "Premier contact"}

Organisation : ${org.name}

Génère la relance optimale. Si tu juges qu'il faut arrêter la séquence (client manifestement non intéressé, situation sensible), indique stop_sequence: true.
`;
}

function buildPaymentLinksSection(relanceType, org, result, targetData) {
  if (!result.include_payment_link) return "";
  const link = targetData.payment_link || org.website;
  if (!link) return "";
  return `
  <div style="margin:24px 0;padding:20px;background:#fff8f5;border-left:3px solid #f26419;border-radius:4px">
    <p style="margin:0 0 12px;font-size:13px;color:#666">Lien de paiement sécurisé :</p>
    <a href="${link}" style="background:#f26419;color:#fff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:600;display:inline-block">
      Régler maintenant →
    </a>
  </div>`;
}

function buildRelanceEmail(message, org, paymentSection) {
  return `
<!DOCTYPE html>
<html>
<body style="font-family:'Helvetica Neue',sans-serif;max-width:560px;margin:0 auto;color:#333;padding:20px">
  <div style="border-bottom:2px solid #f26419;padding-bottom:12px;margin-bottom:20px">
    <strong>${org.name}</strong>
  </div>
  ${message.split('\n').map(p => p.trim() ? `<p style="margin:0 0 14px;line-height:1.7">${p}</p>` : '').join('')}
  ${paymentSection}
  <p style="color:#bbb;font-size:11px;margin-top:32px;border-top:1px solid #eee;padding-top:14px">
    ${org.name} · Message automatique — Répondre directement à cet email si besoin
  </p>
</body>
</html>`;
}

async function notifyCriticalRelance({ org, targetData, config, result, relanceCount }) {
  const { data: admins } = await supabase.from("users").select("email").eq("org_id", org.id).in("role", ["owner", "admin"]);
  if (!admins?.length) return;

  await resend.emails.send({
    from: "AutoFlow <alerts@autoflow.fr>",
    to: admins.map(a => a.email),
    subject: `${config.emoji} Relance critique — ${targetData.name} — ${result.amount_at_stake_euros}€`,
    html: `
      <h3>${config.emoji} Relance #${relanceCount + 1} envoyée</h3>
      <p><strong>Client :</strong> ${targetData.name} (${targetData.email})</p>
      <p><strong>Type :</strong> ${config.label}</p>
      <p><strong>Montant en jeu :</strong> ${result.amount_at_stake_euros}€</p>
      <p><strong>Urgence :</strong> ${result.urgency_level}</p>
      <p style="color:#666;font-size:13px">Si pas de réponse dans 3 jours, une prise de contact direct est recommandée.</p>
    `,
  });
}

// ============================================
// WEBHOOK HANDLER
// ============================================
export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (req.headers["x-autoflow-token"] !== process.env.WEBHOOK_SECRET)
    return res.status(401).json({ error: "Unauthorized" });

  const { action, orgId, agentId, relanceType, targetData } = req.body;

  try {
    let result;
    switch (action) {
      case "scan":
        result = await scanMoneyToRecover({ orgId });
        break;
      case "send_relance":
        result = await sendRelance({ orgId, agentId, relanceType, targetData });
        break;
      case "monthly_report":
        result = await generateMoneyReport({ orgId, agentId });
        break;
      default:
        return res.status(400).json({ error: `Action inconnue: ${action}` });
    }
    return res.status(200).json({ success: true, data: result });
  } catch (err) {
    console.error("Relance Argent error:", err);
    return res.status(500).json({ error: err.message });
  }
}
