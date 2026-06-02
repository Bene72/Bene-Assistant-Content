// ============================================
// AGENT SATISFACTION & AVIS GOOGLE — AutoFlow
// api/agents/satisfaction.js
// ============================================
// J+1 après prestation : message satisfaction
// Détecte : content / mécontent
// Si content  → demande avis Google
// Si mécontent → alerte humaine AVANT mauvais avis
// Suivi : nombre d'avis collectés, score moyen

import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const resend = new Resend(process.env.RESEND_API_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

// ============================================
// SYSTEM PROMPT — Agent Satisfaction
// ============================================
const SATISFACTION_SYSTEM_PROMPT = `Tu es l'agent satisfaction IA de {org_name}.
Tu envoies des messages de satisfaction après chaque prestation et tu gères les retours clients.

CONTEXTE
{org_context}

MISSIONS
1. Envoyer un message de satisfaction chaleureux J+1 après la prestation
2. Analyser la réponse du client (sentiment 0-10)
3. Si satisfait (score >= 7) → demander un avis Google de façon naturelle
4. Si insatisfait (score < 5) → alerter immédiatement le coach AVANT tout mauvais avis
5. Si neutre (5-6) → nurturing doux, proposer une solution

RÈGLES
- Jamais demander l'avis Google si le client semble insatisfait
- Toujours résoudre le problème avant de penser à la réputation
- Le message de satisfaction doit mentionner quelque chose de spécifique à la séance
- La demande d'avis doit être naturelle, jamais forcée
- Maximum 1 demande d'avis par client par mois

FORMAT RÉPONSE JSON strict :
{
  "message": "...",
  "sentiment_score": 8,
  "sentiment_label": "satisfait|neutre|insatisfait",
  "request_google_review": true,
  "google_review_message": "...",
  "alert_human": false,
  "alert_reason": null,
  "alert_urgency": "low|medium|high|critical",
  "followup_action": "none|nurturing|callback|refund_offer",
  "review_requested": false
}`;

// ============================================
// 1. ENVOYER LE MESSAGE DE SATISFACTION J+1
// ============================================
export async function sendSatisfactionCheck({ orgId, agentId, clientData }) {
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  const systemPrompt = SATISFACTION_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  // Générer le message de satisfaction personnalisé
  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 600,
    system: systemPrompt,
    messages: [{
      role: "user",
      content: `Génère le message de satisfaction J+1 pour :
Client : ${clientData.name}
Type de prestation : ${clientData.service_type || "séance de coaching"}
Date de la prestation : ${clientData.service_date || "hier"}
Détails : ${clientData.session_notes || "Séance standard"}
Objectif client : ${clientData.goal || "non précisé"}

Le message doit être chaleureux, court (3-4 phrases max), et demander si tout s'est bien passé.
Ton : décontracté et sincère. Tutoie le client.
Ne pas encore demander l'avis Google à ce stade.
Réponds JSON.`
    }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const result = json ? JSON.parse(json[0]) : { message: raw };

  // Envoyer l'email
  if (clientData.email) {
    await resend.emails.send({
      from: `${org.name} <contact@autoflow.fr>`,
      replyTo: org.email,
      to: clientData.email,
      subject: `Comment s'est passée ta séance, ${clientData.name?.split(" ")[0] || ""} ? 💪`,
      html: buildSatisfactionEmail(result.message, org, clientData),
    });
  }

  // Enregistrer l'action en base
  if (clientData.lead_id) {
    await supabase.from("lead_activities").insert({
      lead_id: clientData.lead_id,
      type: "satisfaction_sent",
      description: `Message satisfaction J+1 envoyé après ${clientData.service_type || "séance"}`,
    });
  }

  await supabase.from("events").insert({
    org_id: orgId,
    type: "satisfaction.sent",
    source: agentId,
    data: { client: clientData.name, email: clientData.email, service: clientData.service_type },
  });

  return { sent: true, message: result.message };
}

// ============================================
// 2. ANALYSER LA RÉPONSE DU CLIENT
// ============================================
export async function analyzeClientResponse({ orgId, agentId, clientData, clientResponse }) {
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  const systemPrompt = SATISFACTION_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 800,
    system: systemPrompt,
    messages: [{
      role: "user",
      content: `Client : ${clientData.name}
Réponse reçue : "${clientResponse}"
Service : ${clientData.service_type || "coaching"}
Objectif : ${clientData.goal || "non précisé"}

Analyse le sentiment, génère une réponse adaptée.
Si satisfait → prépare une demande d'avis Google naturelle.
Si insatisfait → génère une réponse empathique + alert_human: true.
Lien avis Google : ${process.env.GOOGLE_REVIEW_LINK || "https://g.page/r/VOTRE_LIEN_AVIS/review"}
Réponds JSON.`
    }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const result = json ? JSON.parse(json[0]) : null;
  if (!result) throw new Error("Analyse échouée");

  // Répondre au client
  if (clientData.email && result.message) {
    const body = result.request_google_review
      ? buildReviewRequestEmail(result.message, result.google_review_message, org, clientData)
      : buildFollowupEmail(result.message, org, clientData);

    await resend.emails.send({
      from: `${org.name} <contact@autoflow.fr>`,
      replyTo: org.email,
      to: clientData.email,
      subject: result.sentiment_label === "insatisfait"
        ? `On va arranger ça 🙏`
        : `Super ! Merci ${clientData.name?.split(" ")[0] || ""} 😊`,
      html: body,
    });
  }

  // ALERTE HUMAINE si client insatisfait
  if (result.alert_human) {
    await alertBadReview({ org, clientData, clientResponse, result });
  }

  // Logger l'avis si demandé
  if (result.request_google_review && clientData.lead_id) {
    await supabase.from("lead_activities").insert({
      lead_id: clientData.lead_id,
      type: "google_review_requested",
      description: `Demande d'avis Google envoyée — sentiment: ${result.sentiment_score}/10`,
      metadata: { sentiment_score: result.sentiment_score },
    });

    // Incrémenter le compteur d'avis demandés
    await supabase.rpc("increment_agent_stats", {
      p_agent_id: agentId,
      p_tasks: 1,
    });
  }

  // Event
  await supabase.from("events").insert({
    org_id: orgId,
    type: "satisfaction.analyzed",
    source: agentId,
    data: {
      client: clientData.name,
      sentiment_score: result.sentiment_score,
      sentiment_label: result.sentiment_label,
      review_requested: result.request_google_review,
      alert_sent: result.alert_human,
    },
  });

  return result;
}

// ============================================
// 3. ALERTE MAUVAIS AVIS — IMMÉDIATE
// ============================================
async function alertBadReview({ org, clientData, clientResponse, result }) {
  const { data: admins } = await supabase
    .from("users").select("email")
    .eq("org_id", org.id).in("role", ["owner", "admin"]);

  if (!admins?.length) return;

  const urgencyEmoji = { low: "⚠️", medium: "🔴", high: "🚨", critical: "🆘" }[result.alert_urgency] || "⚠️";

  await resend.emails.send({
    from: "AutoFlow <alerts@autoflow.fr>",
    to: admins.map(a => a.email),
    subject: `${urgencyEmoji} Client insatisfait — ${clientData.name} — Action requise MAINTENANT`,
    html: `
      <div style="font-family:sans-serif;max-width:560px;border-left:4px solid #e24b4a;padding-left:16px">
        <h2 style="color:#e24b4a;margin:0 0 16px">${urgencyEmoji} Client insatisfait détecté</h2>
        <p style="color:#666;font-size:13px">L'agent satisfaction a intercepté un retour négatif <strong>avant qu'un mauvais avis Google soit posté</strong>.</p>
        
        <table style="width:100%;border-collapse:collapse;margin:16px 0">
          <tr><td style="padding:8px;color:#888;font-size:13px">Client</td><td style="padding:8px;font-weight:600">${clientData.name}</td></tr>
          <tr style="background:#f9f9f9"><td style="padding:8px;color:#888;font-size:13px">Email</td><td style="padding:8px">${clientData.email}</td></tr>
          <tr><td style="padding:8px;color:#888;font-size:13px">Service</td><td style="padding:8px">${clientData.service_type || "coaching"}</td></tr>
          <tr style="background:#f9f9f9"><td style="padding:8px;color:#888;font-size:13px">Score satisfaction</td><td style="padding:8px;color:#e24b4a;font-weight:700">${result.sentiment_score}/10</td></tr>
          <tr><td style="padding:8px;color:#888;font-size:13px">Urgence</td><td style="padding:8px;font-weight:600">${result.alert_urgency?.toUpperCase()}</td></tr>
        </table>

        <div style="background:#fdf0f0;border-radius:6px;padding:14px;margin:16px 0">
          <strong style="font-size:13px;color:#e24b4a">Message du client :</strong>
          <p style="margin:8px 0 0;font-style:italic;color:#333">"${clientResponse}"</p>
        </div>

        <div style="background:#f0f7f0;border-radius:6px;padding:14px;margin:16px 0">
          <strong style="font-size:13px;color:#3B6D11">Réponse envoyée par l'agent :</strong>
          <p style="margin:8px 0 0;color:#333">${result.message}</p>
        </div>

        <p style="font-size:13px;color:#666"><strong>Action recommandée :</strong> Contacter ${clientData.name} directement par téléphone dans les 2 heures pour résoudre le problème avant qu'il ne poste un avis négatif.</p>
        
        <a href="tel:${clientData.phone || ''}" style="display:inline-block;background:#e24b4a;color:#fff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:600;margin-top:8px">
          📞 Appeler ${clientData.name?.split(" ")[0] || "le client"} →
        </a>
      </div>
    `,
  });
}

// ============================================
// 4. RAPPORT MENSUEL AVIS GOOGLE
// ============================================
export async function generateReviewReport({ orgId, agentId }) {
  const monthAgo = new Date();
  monthAgo.setMonth(monthAgo.getMonth() - 1);

  const { data: reviewRequests } = await supabase
    .from("lead_activities")
    .select("*")
    .eq("org_id", orgId)
    .eq("type", "google_review_requested")
    .gte("created_at", monthAgo.toISOString());

  const { data: alerts } = await supabase
    .from("events")
    .select("*")
    .eq("org_id", orgId)
    .eq("type", "satisfaction.analyzed")
    .gte("created_at", monthAgo.toISOString());

  const satisfiedCount = (alerts || []).filter(e => e.data?.sentiment_score >= 7).length;
  const unhappyCount = (alerts || []).filter(e => e.data?.sentiment_score < 5).length;
  const avgScore = alerts?.length
    ? Math.round((alerts.reduce((s, e) => s + (e.data?.sentiment_score || 0), 0) / alerts.length) * 10) / 10
    : 0;

  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: admins } = await supabase.from("users").select("email").eq("org_id", orgId).in("role", ["owner", "admin"]);

  if (admins?.length) {
    await resend.emails.send({
      from: "AutoFlow <reports@autoflow.fr>",
      to: admins.map(a => a.email),
      subject: `⭐ Rapport Satisfaction & Avis Google — ${org.name}`,
      html: `
        <div style="font-family:sans-serif;max-width:560px">
          <h2>⭐ Rapport Satisfaction — ${new Date().toLocaleDateString("fr-FR", { month: "long", year: "numeric" })}</h2>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0">
            <div style="background:#f9f9f9;border-radius:8px;padding:14px;text-align:center">
              <div style="font-size:28px;font-weight:700;color:#333">${reviewRequests?.length || 0}</div>
              <div style="font-size:12px;color:#888">Avis demandés</div>
            </div>
            <div style="background:#f9f9f9;border-radius:8px;padding:14px;text-align:center">
              <div style="font-size:28px;font-weight:700;color:#f26419">${avgScore}/10</div>
              <div style="font-size:12px;color:#888">Score moyen</div>
            </div>
            <div style="background:#fdf0f0;border-radius:8px;padding:14px;text-align:center">
              <div style="font-size:28px;font-weight:700;color:#e24b4a">${unhappyCount}</div>
              <div style="font-size:12px;color:#888">Alertes interceptées</div>
            </div>
          </div>
          <p style="color:#666;font-size:13px">${satisfiedCount} clients satisfaits sur ${alerts?.length || 0} retours collectés ce mois.</p>
          ${unhappyCount > 0 ? `<p style="color:#e24b4a;font-size:13px">⚠️ ${unhappyCount} mauvais avis potentiels interceptés avant publication.</p>` : ""}
        </div>
      `,
    });
  }

  return { reviewRequests: reviewRequests?.length, avgScore, satisfiedCount, unhappyCount };
}

// ============================================
// HELPERS EMAIL
// ============================================
function buildSatisfactionEmail(message, org, clientData) {
  return `
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',sans-serif;max-width:520px;margin:0 auto;color:#333;padding:20px">
  <div style="border-bottom:3px solid #f26419;padding-bottom:12px;margin-bottom:20px"><strong>${org.name}</strong></div>
  ${message.split('\n').map(p => p.trim() ? `<p style="margin:0 0 14px;line-height:1.7">${p}</p>` : '').join('')}
  <p style="color:#999;font-size:12px;margin-top:32px;border-top:1px solid #eee;padding-top:14px">
    ${org.name} · Réponds directement à cet email
  </p>
</body></html>`;
}

function buildReviewRequestEmail(message, reviewMessage, org, clientData) {
  const reviewLink = process.env.GOOGLE_REVIEW_LINK || "https://g.page/r/VOTRE_LIEN/review";
  return `
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',sans-serif;max-width:520px;margin:0 auto;color:#333;padding:20px">
  <div style="border-bottom:3px solid #f26419;padding-bottom:12px;margin-bottom:20px"><strong>${org.name}</strong></div>
  ${message.split('\n').map(p => p.trim() ? `<p style="margin:0 0 14px;line-height:1.7">${p}</p>` : '').join('')}
  ${reviewMessage ? `
  <div style="background:#fffbf0;border:1px solid #f0d890;border-radius:8px;padding:18px;margin:20px 0;text-align:center">
    <div style="font-size:24px;margin-bottom:8px">⭐⭐⭐⭐⭐</div>
    <p style="margin:0 0 14px;font-size:14px;color:#555">${reviewMessage}</p>
    <a href="${reviewLink}" style="background:#f26419;color:#fff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:600;font-size:14px;display:inline-block">
      Laisser un avis Google →
    </a>
    <p style="margin:10px 0 0;font-size:11px;color:#aaa">Ça prend 30 secondes et ça aide vraiment 🙏</p>
  </div>` : ''}
  <p style="color:#999;font-size:12px;margin-top:24px;border-top:1px solid #eee;padding-top:14px">${org.name}</p>
</body></html>`;
}

function buildFollowupEmail(message, org, clientData) {
  return `
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',sans-serif;max-width:520px;margin:0 auto;color:#333;padding:20px">
  <div style="border-bottom:3px solid #f26419;padding-bottom:12px;margin-bottom:20px"><strong>${org.name}</strong></div>
  ${message.split('\n').map(p => p.trim() ? `<p style="margin:0 0 14px;line-height:1.7">${p}</p>` : '').join('')}
  <p style="color:#999;font-size:12px;margin-top:32px;border-top:1px solid #eee;padding-top:14px">${org.name}</p>
</body></html>`;
}

// ============================================
// WEBHOOK HANDLER
// ============================================
export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (req.headers["x-autoflow-token"] !== process.env.WEBHOOK_SECRET)
    return res.status(401).json({ error: "Unauthorized" });

  const { action, orgId, agentId, clientData, clientResponse } = req.body;

  try {
    let result;
    switch (action) {
      case "send_satisfaction":
        result = await sendSatisfactionCheck({ orgId, agentId, clientData });
        break;
      case "analyze_response":
        result = await analyzeClientResponse({ orgId, agentId, clientData, clientResponse });
        break;
      case "monthly_report":
        result = await generateReviewReport({ orgId, agentId });
        break;
      default:
        return res.status(400).json({ error: `Action inconnue: ${action}` });
    }
    return res.status(200).json({ success: true, data: result });
  } catch (err) {
    console.error("Satisfaction agent error:", err);
    return res.status(500).json({ error: err.message });
  }
}
