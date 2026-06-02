// ============================================
// AGENT OFFRE & DEVIS INTELLIGENT — AutoFlow
// api/agents/devis.js
// ============================================
// Brief client → Proposition commerciale structurée
//             → Devis PDF-ready
//             → Email d'accompagnement
//             → Relance automatique J+2/J+5/J+10
//             → Résumé des objections probables

import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const resend = new Resend(process.env.RESEND_API_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

// ============================================
// SYSTEM PROMPT — Agent Devis
// ============================================
const DEVIS_SYSTEM_PROMPT = `Tu es l'expert commercial IA de {org_name}.
Tu transformes un brief client en proposition commerciale percutante et en devis structuré.

CONTEXTE
{org_context}

PHILOSOPHIE DEVIS
- Un devis n'est pas une liste de prix — c'est une réponse à un problème
- Toujours commencer par reformuler le problème du client
- Présenter la valeur AVANT le prix
- Justifier chaque ligne par un bénéfice concret
- Anticiper les objections (prix, délai, ROI)

STRUCTURE PROPOSITION COMMERCIALE
1. Compréhension du contexte (reformulation empathique)
2. Ce que tu vas obtenir (bénéfices, pas features)
3. Comment on travaille ensemble (méthode rassurante)
4. Investissement (prix avec justification)
5. Garanties et prochaine étape

RÈGLES PRICING
- Jamais s'excuser du prix
- Toujours ramener à un coût journalier ou hebdo pour relativiser
- Si budget serré évoqué → proposer une option allégée, pas une remise directe
- Mentionner ce qu'il en coûte de NE PAS agir (coût du statu quo)

FORMAT RÉPONSE JSON strict :
{
  "devis_number": "DEV-2026-001",
  "client_name": "...",
  "validity_days": 30,
  "problem_statement": "...",
  "solution_summary": "...",
  "lines": [
    {
      "label": "...",
      "description": "...",
      "quantity": 1,
      "unit": "forfait|mois|séance|heure",
      "unit_price": 490,
      "total": 490
    }
  ],
  "subtotal": 490,
  "discount": 0,
  "total_ht": 490,
  "tva_rate": 0,
  "total_ttc": 490,
  "payment_terms": "...",
  "proposal_email_subject": "...",
  "proposal_email_body": "...",
  "objections": [
    {"objection": "C'est trop cher", "reponse": "..."},
    {"objection": "J'ai besoin de réfléchir", "reponse": "..."},
    {"objection": "Je vais essayer seul d'abord", "reponse": "..."}
  ],
  "urgency_argument": "...",
  "guarantee": "...",
  "next_step": "..."
}`;

// ============================================
// GÉNÉRER UNE PROPOSITION COMMERCIALE
// ============================================
export async function generateProposal({ orgId, agentId, leadId, briefData }) {
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();
  const lead = leadId
    ? (await supabase.from("leads").select("*").eq("id", leadId).single()).data
    : null;

  const systemPrompt = DEVIS_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  // Numéro de devis auto
  const { count } = await supabase
    .from("events")
    .select("id", { count: "exact" })
    .eq("org_id", orgId)
    .eq("type", "devis.generated");
  const devisNumber = `DEV-${new Date().getFullYear()}-${String((count || 0) + 1).padStart(3, "0")}`;

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 2500,
    system: systemPrompt,
    messages: [{
      role: "user",
      content: `Génère la proposition commerciale et le devis pour ce brief.

CLIENT
- Nom : ${briefData.client_name || lead?.full_name || "Non précisé"}
- Email : ${briefData.client_email || lead?.email || ""}
- Entreprise/Contexte : ${briefData.company || "Indépendant"}
- Source : ${briefData.source || lead?.source || "Direct"}

BRIEF
- Besoin exprimé : ${briefData.needs || lead?.pain_points?.join(", ") || "Non précisé"}
- Objectif principal : ${briefData.goal || "Non précisé"}
- Budget évoqué : ${briefData.budget || lead?.budget_range || "Non mentionné"}
- Timeline souhaitée : ${briefData.timeline || lead?.timeline || "Non précisée"}
- Contexte supplémentaire : ${briefData.context || "Aucun"}

OFFRES DISPONIBLES
${briefData.available_offers || `
- Séance individuelle : 70€
- Pack 10 séances : 600€ (valable 6 mois)  
- Coaching en ligne mensuel : 150€/mois
- Préparation Hyrox complète (8 semaines) : 490€
`}

Numéro de devis : ${devisNumber}
Date : ${new Date().toLocaleDateString("fr-FR")}
Validité : 30 jours

Génère la proposition complète. Adapte les lignes de devis au besoin exprimé.
Réponds uniquement JSON.`
    }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const proposal = json ? JSON.parse(json[0]) : null;
  if (!proposal) throw new Error("Génération devis échouée");

  proposal.devis_number = devisNumber;
  proposal.org = { name: org.name, email: org.email };
  proposal.created_at = new Date().toISOString();
  proposal.valid_until = new Date(Date.now() + 30 * 86400000).toLocaleDateString("fr-FR");

  // Envoyer l'email de proposition
  const clientEmail = briefData.client_email || lead?.email;
  if (clientEmail && proposal.proposal_email_body) {
    await resend.emails.send({
      from: `${org.name} <contact@autoflow.fr>`,
      replyTo: org.email,
      to: clientEmail,
      subject: proposal.proposal_email_subject || `Votre proposition — ${org.name} — ${devisNumber}`,
      html: buildProposalEmail(proposal, org),
    });
  }

  // Envoyer le devis HTML à Benoit aussi
  const { data: admins } = await supabase.from("users").select("email").eq("org_id", orgId).in("role", ["owner", "admin"]);
  if (admins?.length) {
    await resend.emails.send({
      from: "AutoFlow <devis@autoflow.fr>",
      to: admins.map(a => a.email),
      subject: `📄 Devis généré — ${proposal.devis_number} — ${proposal.client_name} — ${proposal.total_ttc}€`,
      html: buildCoachDevisEmail(proposal, org),
    });
  }

  // Sauvegarder en base
  if (leadId) {
    await supabase.from("leads").update({
      stage: "proposal",
      last_contact_at: new Date().toISOString(),
      enriched_data: {
        ...lead?.enriched_data,
        last_devis: devisNumber,
        last_devis_amount: proposal.total_ttc,
        last_devis_date: new Date().toISOString(),
      },
    }).eq("id", leadId);

    await supabase.from("lead_activities").insert({
      lead_id: leadId,
      type: "devis_sent",
      description: `Devis ${devisNumber} envoyé — ${proposal.total_ttc}€`,
      metadata: { devis_number: devisNumber, amount: proposal.total_ttc },
    });
  }

  // Planifier les relances automatiques
  await scheduleDevisFollowups({ orgId, agentId, leadId, devisNumber, clientEmail, proposal });

  await supabase.from("events").insert({
    org_id: orgId,
    type: "devis.generated",
    source: agentId,
    data: { devis_number: devisNumber, amount: proposal.total_ttc, client: proposal.client_name, lead_id: leadId },
  });

  return { proposal, devis_number: devisNumber, sent_to: clientEmail };
}

// ============================================
// RELANCES DEVIS NON SIGNÉ
// ============================================
const FOLLOWUP_PROMPTS = {
  2: `Relance douce J+2. Demander si le client a eu le temps de regarder la proposition.
      Proposer de répondre à ses questions. Court, chaleureux, pas de pression.`,
  5: `Relance J+5. Lever une objection probable selon le profil du client.
      Rappeler 1 bénéfice clé. Proposer un appel de 15 min pour répondre aux questions.
      Inclure l'argument d'urgence du devis.`,
  10: `Dernière relance J+10. Créer une urgence légère et légitime.
       Rappeler la date d'expiration du devis. Proposer une dernière fois un échange.
       Ton direct mais respectueux.`,
};

export async function sendDevisFollowup({ orgId, agentId, leadId, devisData, followupDay }) {
  const { data: lead } = await supabase.from("leads").select("*").eq("id", leadId).single();
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  // Vérifier si le devis a déjà été signé
  if (lead?.stage === "won") {
    return { skipped: true, reason: "Devis déjà accepté" };
  }

  const systemPrompt = DEVIS_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 700,
    system: systemPrompt,
    messages: [{
      role: "user",
      content: `Client : ${lead?.full_name}
Devis : ${devisData.devis_number} — ${devisData.amount}€
Besoin : ${lead?.pain_points?.[0] || "coaching sportif"}
Objections probables : ${devisData.objections?.map(o => o.objection).join(", ") || "prix, délai"}
Urgence : ${devisData.urgency_argument || "offre valable 30 jours"}

${FOLLOWUP_PROMPTS[followupDay] || FOLLOWUP_PROMPTS[5]}

Réponds JSON : { "subject": "...", "body": "...", "stop_sequence": false }`
    }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const result = json ? JSON.parse(json[0]) : null;

  if (result?.stop_sequence) return { skipped: true, reason: "IA recommande d'arrêter" };

  const clientEmail = devisData.client_email || lead?.email;
  if (clientEmail && result?.body) {
    await resend.emails.send({
      from: `${org.name} <contact@autoflow.fr>`,
      replyTo: org.email,
      to: clientEmail,
      subject: result.subject || `Suite à ma proposition — ${org.name}`,
      html: buildFollowupEmail(result.body, org, devisData),
    });

    if (leadId) {
      await supabase.from("lead_activities").insert({
        lead_id: leadId,
        type: "devis_followup",
        description: `Relance devis J+${followupDay} — ${devisData.devis_number}`,
      });
    }
  }

  return { sent: true, day: followupDay };
}

// ============================================
// MARQUER UN DEVIS COMME SIGNÉ
// ============================================
export async function markDevisAccepted({ orgId, agentId, leadId, devisNumber }) {
  if (leadId) {
    await supabase.from("leads").update({
      stage: "won",
      last_contact_at: new Date().toISOString(),
    }).eq("id", leadId);

    await supabase.from("lead_activities").insert({
      lead_id: leadId,
      type: "devis_accepted",
      description: `Devis ${devisNumber} accepté — client signé`,
    });
  }

  await supabase.from("events").insert({
    org_id: orgId,
    type: "devis.accepted",
    source: agentId,
    data: { devis_number: devisNumber, lead_id: leadId },
  });

  // Déclencher l'onboarding automatiquement
  const onboardingPayload = {
    action: "start",
    orgId,
    agentId: process.env.ONBOARDING_AGENT_ID,
    leadId,
    planType: "Client signé via devis",
  };

  await fetch(`${process.env.AUTOFLOW_API_URL}/api/agents/onboarding`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-autoflow-token": process.env.WEBHOOK_SECRET,
    },
    body: JSON.stringify(onboardingPayload),
  });

  return { success: true, onboarding_triggered: true };
}

// ============================================
// PLANIFIER LES RELANCES DEVIS
// ============================================
async function scheduleDevisFollowups({ orgId, agentId, leadId, devisNumber, clientEmail, proposal }) {
  const followupDays = [2, 5, 10];
  for (const day of followupDays) {
    const due = new Date();
    due.setDate(due.getDate() + day);
    await supabase.from("tasks").insert({
      org_id: orgId,
      title: `Relance devis J+${day} — ${proposal.client_name} — ${devisNumber}`,
      status: "todo",
      priority: day === 2 ? "high" : day === 5 ? "high" : "medium",
      assigned_by_agent: agentId,
      auto_generated: true,
      due_date: due.toISOString(),
      metadata: {
        lead_id: leadId,
        devis_number: devisNumber,
        client_email: clientEmail,
        amount: proposal.total_ttc,
        objections: proposal.objections,
        urgency_argument: proposal.urgency_argument,
        followup_day: day,
      },
    });
  }
}

// ============================================
// HELPERS EMAIL
// ============================================
function buildProposalEmail(proposal, org) {
  const linesHtml = (proposal.lines || []).map(line => `
    <tr>
      <td style="padding:12px 16px;border-bottom:1px solid #f0ede8">
        <div style="font-size:14px;font-weight:500;color:#333">${line.label}</div>
        <div style="font-size:12px;color:#888;margin-top:3px">${line.description}</div>
      </td>
      <td style="padding:12px 16px;border-bottom:1px solid #f0ede8;text-align:center;color:#666;font-size:13px">${line.quantity} ${line.unit}</td>
      <td style="padding:12px 16px;border-bottom:1px solid #f0ede8;text-align:right;font-size:14px;font-weight:500;color:#333">${line.total?.toLocaleString("fr-FR")}€</td>
    </tr>`).join('');

  return `
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',sans-serif;max-width:620px;margin:0 auto;color:#333;padding:0">
  <div style="background:#1a1a1a;padding:28px 32px;border-radius:12px 12px 0 0">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <strong style="color:#fff;font-size:20px">${org.name}</strong>
      <span style="color:#f26419;font-size:13px;font-weight:600">${proposal.devis_number}</span>
    </div>
    <p style="color:rgba(255,255,255,0.6);font-size:12px;margin:6px 0 0">Proposition commerciale · Valable jusqu'au ${proposal.valid_until}</p>
  </div>

  <div style="background:#fff;padding:32px;border:1px solid #eee;border-top:none">
    ${proposal.proposal_email_body?.split('\n').map(p => p.trim() ? `<p style="margin:0 0 14px;line-height:1.7">${p}</p>` : '').join('') || ''}

    <div style="background:#f9f8f6;border-radius:8px;padding:20px;margin:24px 0">
      <p style="font-size:13px;font-weight:600;color:#666;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 6px">Ce que vous avez partagé</p>
      <p style="margin:0;font-size:14px;color:#333;font-style:italic">${proposal.problem_statement}</p>
    </div>

    <div style="background:#fff3ec;border-left:3px solid #f26419;padding:14px 18px;border-radius:4px;margin:20px 0">
      <p style="margin:0;font-size:14px;color:#333">${proposal.solution_summary}</p>
    </div>

    <table style="width:100%;border-collapse:collapse;border:1px solid #f0ede8;border-radius:8px;overflow:hidden;margin:24px 0">
      <thead style="background:#f9f8f6">
        <tr>
          <th style="padding:12px 16px;text-align:left;font-size:12px;color:#888;font-weight:500">PRESTATION</th>
          <th style="padding:12px 16px;text-align:center;font-size:12px;color:#888;font-weight:500">QTÉ</th>
          <th style="padding:12px 16px;text-align:right;font-size:12px;color:#888;font-weight:500">TOTAL</th>
        </tr>
      </thead>
      <tbody>${linesHtml}</tbody>
      <tfoot style="background:#f9f8f6">
        ${proposal.discount ? `<tr><td colspan="2" style="padding:10px 16px;font-size:13px;color:#888">Remise</td><td style="padding:10px 16px;text-align:right;font-size:13px;color:#3B6D11">-${proposal.discount}€</td></tr>` : ''}
        <tr>
          <td colspan="2" style="padding:14px 16px;font-size:15px;font-weight:700">TOTAL</td>
          <td style="padding:14px 16px;text-align:right;font-size:20px;font-weight:700;color:#f26419">${proposal.total_ttc?.toLocaleString("fr-FR")}€</td>
        </tr>
      </tfoot>
    </table>

    <div style="display:flex;gap:12px;margin:24px 0;flex-wrap:wrap">
      <div style="flex:1;min-width:140px;background:#f9f8f6;border-radius:8px;padding:14px;text-align:center">
        <div style="font-size:12px;color:#888;margin-bottom:4px">Modalités</div>
        <div style="font-size:13px;font-weight:500">${proposal.payment_terms || "À la signature"}</div>
      </div>
      <div style="flex:1;min-width:140px;background:#edfaf4;border-radius:8px;padding:14px;text-align:center">
        <div style="font-size:12px;color:#888;margin-bottom:4px">Garantie</div>
        <div style="font-size:13px;font-weight:500;color:#3B6D11">${proposal.guarantee || "Satisfaction garantie"}</div>
      </div>
      <div style="flex:1;min-width:140px;background:#fff3ec;border-radius:8px;padding:14px;text-align:center">
        <div style="font-size:12px;color:#888;margin-bottom:4px">Validité</div>
        <div style="font-size:13px;font-weight:500;color:#f26419">${proposal.validity_days || 30} jours</div>
      </div>
    </div>

    <div style="text-align:center;margin:28px 0;padding:24px;background:#1a1a1a;border-radius:8px">
      <p style="color:#fff;font-size:15px;margin:0 0 16px">${proposal.next_step || "Prêt à démarrer ?"}</p>
      <a href="mailto:${org.email}?subject=Accord devis ${proposal.devis_number}" style="background:#f26419;color:#fff;padding:14px 28px;text-decoration:none;border-radius:6px;font-weight:600;font-size:14px;display:inline-block">
        Accepter la proposition →
      </a>
      <p style="color:rgba(255,255,255,0.5);font-size:11px;margin:12px 0 0">Ou répondre directement à cet email</p>
    </div>

    <p style="color:#999;font-size:12px;border-top:1px solid #eee;padding-top:14px">${org.name} · ${proposal.devis_number} · Valable jusqu'au ${proposal.valid_until}</p>
  </div>
</body></html>`;
}

function buildCoachDevisEmail(proposal, org) {
  return `
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',sans-serif;max-width:560px;margin:0 auto;color:#333;padding:20px">
  <h2>📄 Devis envoyé — ${proposal.devis_number}</h2>
  <table style="width:100%;border-collapse:collapse;border:1px solid #eee;margin:16px 0">
    <tr style="background:#f9f9f9"><td style="padding:10px;color:#888;font-size:13px">Client</td><td style="padding:10px;font-weight:600">${proposal.client_name}</td></tr>
    <tr><td style="padding:10px;color:#888;font-size:13px">Montant</td><td style="padding:10px;font-size:18px;font-weight:700;color:#f26419">${proposal.total_ttc?.toLocaleString("fr-FR")}€</td></tr>
    <tr style="background:#f9f9f9"><td style="padding:10px;color:#888;font-size:13px">Validité</td><td style="padding:10px">Jusqu'au ${proposal.valid_until}</td></tr>
  </table>
  <div style="background:#fff8f3;border-left:3px solid #f26419;padding:14px;border-radius:4px;margin:16px 0">
    <strong style="font-size:13px">💡 Objections probables :</strong>
    ${(proposal.objections || []).map(o => `<p style="margin:8px 0 0;font-size:13px"><strong>${o.objection}</strong><br><span style="color:#666">${o.reponse}</span></p>`).join('')}
  </div>
  <p style="font-size:13px;color:#666">3 relances automatiques planifiées : J+2, J+5, J+10</p>
</body></html>`;
}

function buildFollowupEmail(body, org, devisData) {
  return `
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',sans-serif;max-width:520px;margin:0 auto;color:#333;padding:20px">
  <div style="border-bottom:3px solid #f26419;padding-bottom:12px;margin-bottom:20px"><strong>${org.name}</strong></div>
  ${body.split('\n').map(p => p.trim() ? `<p style="margin:0 0 14px;line-height:1.7">${p}</p>` : '').join('')}
  <div style="text-align:center;margin:20px 0">
    <a href="mailto:${org.email}?subject=Accord devis ${devisData.devis_number}" style="background:#f26419;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:600;display:inline-block">
      Valider la proposition →
    </a>
  </div>
  <p style="color:#999;font-size:12px;border-top:1px solid #eee;padding-top:14px">${org.name} · Réf. ${devisData.devis_number}</p>
</body></html>`;
}

// ============================================
// WEBHOOK HANDLER
// ============================================
export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (req.headers["x-autoflow-token"] !== process.env.WEBHOOK_SECRET)
    return res.status(401).json({ error: "Unauthorized" });

  const { action, orgId, agentId, leadId, briefData, devisData, devisNumber, followupDay } = req.body;

  try {
    let result;
    switch (action) {
      case "generate":
        result = await generateProposal({ orgId, agentId, leadId, briefData });
        break;
      case "followup":
        result = await sendDevisFollowup({ orgId, agentId, leadId, devisData, followupDay });
        break;
      case "mark_accepted":
        result = await markDevisAccepted({ orgId, agentId, leadId, devisNumber });
        break;
      default:
        return res.status(400).json({ error: `Action inconnue: ${action}` });
    }
    return res.status(200).json({ success: true, data: result });
  } catch (err) {
    console.error("Devis agent error:", err);
    return res.status(500).json({ error: err.message });
  }
}
