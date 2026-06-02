// ============================================
// AGENT ROI & REPORTING — AutoFlow
// api/agents/roi-reporting.js
// ============================================
// Le 1er de chaque mois, le client reçoit
// la preuve chiffrée de ce qu'AutoFlow lui rapporte.
// C'est ce qui évite le churn et justifie l'upsell.
//
// Calcule :
// → Temps total économisé ce mois
// → Argent récupéré via relances
// → Prospects traités automatiquement
// → Avis Google obtenus
// → Valeur équivalente si fait manuellement
// → ROI net du mois (valeur générée vs prix AutoFlow)

import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const resend = new Resend(process.env.RESEND_API_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

// ============================================
// TARIFS HORAIRES DE RÉFÉRENCE (pour calcul ROI)
// ============================================
const TARIFS = {
  reponse_email: 0.25,        // 15 min par email traité
  qualification_lead: 0.5,    // 30 min par lead qualifié manuellement
  relance_client: 0.25,       // 15 min par relance manuelle
  creation_devis: 1.5,        // 1h30 par devis manuel
  rapport_semaine: 2,         // 2h par rapport hebdo manuel
  onboarding_client: 2,       // 2h par onboarding manuel
  contenu_instagram: 0.75,    // 45 min par post Instagram
  suivi_satisfaction: 0.25,   // 15 min par message satisfaction
  taux_horaire_coach: 70,     // valeur horaire du coach (= prix séance)
};

// ============================================
// SYSTEM PROMPT
// ============================================
const ROI_SYSTEM_PROMPT = `Tu es l'analyste ROI d'AutoFlow.
Tu produis des rapports mensuels qui prouvent la valeur concrète d'AutoFlow pour le client.
Ton rôle : transformer des chiffres en arguments de rétention et d'upsell.

PHILOSOPHIE
- Montrer le ROI NET (valeur générée MOINS le coût de l'abonnement)
- Comparer à "si tu avais fait ça manuellement"
- Pointer les opportunités non encore exploitées
- Suggérer l'upgrade si le ROI justifie un plan supérieur
- Finir sur une note positive et motivante

FORMAT RÉPONSE JSON :
{
  "month": "Mai 2026",
  "headline": "...",
  "roi_net": 1840,
  "roi_multiplier": 4.8,
  "highlights": ["...", "..."],
  "time_saved_hours": 38.5,
  "money_recovered": 980,
  "prospects_handled": 14,
  "top_performing_agent": "communication",
  "top_performing_reason": "...",
  "missed_opportunity": "...",
  "upsell_suggestion": null,
  "next_month_focus": "...",
  "client_message": "..."
}`;

// ============================================
// COLLECTER LES DONNÉES DU MOIS
// ============================================
async function collectMonthData(orgId) {
  const monthAgo = new Date();
  monthAgo.setMonth(monthAgo.getMonth() - 1);
  const monthStart = monthAgo.toISOString();

  const [
    events, leads, tasks,
    conversations, reviewRequests,
    relances, devis, onboardings,
    contentGenerated, wonLeads,
  ] = await Promise.all([
    supabase.from("events").select("type,data").eq("org_id", orgId).gte("created_at", monthStart),
    supabase.from("leads").select("id,stage,score,source,created_at").eq("org_id", orgId).gte("created_at", monthStart),
    supabase.from("tasks").select("id,status,auto_generated").eq("org_id", orgId).eq("auto_generated", true).gte("created_at", monthStart),
    supabase.from("conversations").select("id,message_count,status").eq("org_id", orgId).gte("created_at", monthStart),
    supabase.from("lead_activities").select("id").eq("org_id", orgId).eq("type", "google_review_requested").gte("created_at", monthStart),
    supabase.from("lead_activities").select("id,type,metadata").eq("org_id", orgId).like("type", "relance_%").gte("created_at", monthStart),
    supabase.from("lead_activities").select("id,metadata").eq("org_id", orgId).eq("type", "devis_sent").gte("created_at", monthStart),
    supabase.from("lead_activities").select("id").eq("org_id", orgId).eq("type", "onboarding_started").gte("created_at", monthStart),
    supabase.from("events").select("id").eq("org_id", orgId).eq("type", "contenu.generated").gte("created_at", monthStart),
    supabase.from("leads").select("id,enriched_data").eq("org_id", orgId).eq("stage", "won").gte("updated_at", monthStart),
  ]);

  const ev = events.data || [];
  const evLeads = ev.filter(e => e.type === "lead.acquired").length;
  const evMessages = ev.filter(e => e.type === "agent.message").length;
  const evRelances = relances.data?.length || 0;
  const evDevis = devis.data?.length || 0;
  const evOnboardings = onboardings.data?.length || 0;
  const evContent = contentGenerated.data?.length || 0;
  const evReviews = reviewRequests.data?.length || 0;
  const newLeads = leads.data?.length || 0;
  const newWon = wonLeads.data?.length || 0;
  const autoTasks = tasks.data?.length || 0;
  const totalMessages = (conversations.data || []).reduce((s, c) => s + (c.message_count || 0), 0);

  // Calcul temps économisé
  const timeSaved = (
    evMessages * TARIFS.reponse_email +
    evLeads * TARIFS.qualification_lead +
    evRelances * TARIFS.reponse_email +
    evDevis * TARIFS.creation_devis +
    4 * TARIFS.rapport_semaine +            // 4 rapports hebdo
    evOnboardings * TARIFS.onboarding_client +
    evContent * TARIFS.contenu_instagram +
    totalMessages * TARIFS.suivi_satisfaction
  );

  const timeSavedEuros = Math.round(timeSaved * TARIFS.taux_horaire_coach);

  // Argent récupéré via relances (estimation)
  const moneyRecovered = (relances.data || []).reduce((s, r) => {
    const amount = r.metadata?.amount || 0;
    return s + (amount * 0.3); // taux de conversion estimé 30%
  }, 0);

  // Valeur prospects traités
  const prospectsValue = evLeads * 70; // valeur moyenne d'un lead qualifié

  // Valeur totale générée
  const totalValue = timeSavedEuros + moneyRecovered + prospectsValue;

  // Prix de l'abonnement
  const planPrice = 490; // Pro Coach

  return {
    timeSaved: Math.round(timeSaved * 10) / 10,
    timeSavedEuros,
    moneyRecovered: Math.round(moneyRecovered),
    prospectsValue: Math.round(prospectsValue),
    totalValue: Math.round(totalValue),
    roiNet: Math.round(totalValue - planPrice),
    roiMultiplier: Math.round((totalValue / planPrice) * 10) / 10,
    planPrice,
    // Volumes
    newLeads,
    newWon,
    evMessages,
    evRelances,
    evDevis,
    evOnboardings,
    evContent,
    evReviews,
    autoTasks,
    totalMessages,
    // Par agent
    byAgent: {
      communication: evMessages,
      acquisition: evLeads,
      relance: evRelances,
      contenu: evContent,
      satisfaction: evReviews,
      onboarding: evOnboardings,
      devis: evDevis,
    },
  };
}

// ============================================
// GÉNÉRER ET ENVOYER LE RAPPORT ROI
// ============================================
export async function sendMonthlyROIReport({ orgId, agentId }) {
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  const stats = await collectMonthData(orgId);
  const monthName = new Date(Date.now() - 15 * 86400000)
    .toLocaleDateString("fr-FR", { month: "long", year: "numeric" });

  const systemPrompt = ROI_SYSTEM_PROMPT;

  const prompt = `Génère le rapport ROI mensuel pour ${org.name} — ${monthName}.

DONNÉES DU MOIS :
Temps économisé : ${stats.timeSaved}h (valeur : ${stats.timeSavedEuros}€ au taux horaire du coach)
Argent récupéré via relances : ${stats.moneyRecovered}€
Valeur prospects traités : ${stats.prospectsValue}€
VALEUR TOTALE GÉNÉRÉE : ${stats.totalValue}€
Coût AutoFlow ce mois : ${stats.planPrice}€
ROI NET : +${stats.roiNet}€ (x${stats.roiMultiplier})

Volumes :
- ${stats.newLeads} nouveaux prospects qualifiés automatiquement
- ${stats.newWon} clients signés
- ${stats.evMessages} messages clients traités sans intervention
- ${stats.evRelances} relances envoyées automatiquement
- ${stats.evDevis} devis générés
- ${stats.evOnboardings} onboardings déclenchés
- ${stats.evContent} contenus Instagram générés
- ${stats.evReviews} demandes d'avis Google envoyées
- ${stats.autoTasks} tâches créées automatiquement

Agent le plus actif : ${Object.entries(stats.byAgent).sort((a,b) => b[1]-a[1])[0]?.[0]}

Plan actuel : Pro Coach 490€/mois
Plan supérieur : Elite Business Copilot 790€/mois

Génère le rapport. Si ROI > 5x → suggérer l'upsell Elite.
Réponds JSON strict.`;

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1200,
    system: systemPrompt,
    messages: [{ role: "user", content: prompt }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const report = json ? JSON.parse(json[0]) : null;
  if (!report) throw new Error("Génération rapport ROI échouée");

  // Envoyer l'email
  const { data: admins } = await supabase
    .from("users").select("email").eq("org_id", orgId).in("role", ["owner", "admin"]);

  if (admins?.length) {
    await resend.emails.send({
      from: "AutoFlow <reporting@autoflow.fr>",
      to: admins.map(a => a.email),
      subject: `📊 Bilan ${monthName} — AutoFlow vous a rapporté ${stats.roiNet.toLocaleString("fr-FR")}€ nets`,
      html: buildROIEmail(report, stats, org, monthName),
    });
  }

  // Logger
  await supabase.from("events").insert({
    org_id: orgId,
    type: "report.monthly_roi",
    source: agentId,
    data: {
      month: monthName,
      roi_net: stats.roiNet,
      roi_multiplier: stats.roiMultiplier,
      total_value: stats.totalValue,
    },
  });

  return { sent: true, roi_net: stats.roiNet, roi_multiplier: stats.roiMultiplier, stats };
}

// ============================================
// EMAIL ROI
// ============================================
function buildROIEmail(report, stats, org, monthName) {
  const roiColor = stats.roiMultiplier >= 5 ? "#3B6D11"
    : stats.roiMultiplier >= 3 ? "#f26419" : "#185FA5";

  const agentRows = Object.entries(stats.byAgent)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([agent, count]) => `
      <tr>
        <td style="padding:10px 16px;font-size:13px;color:#333;border-bottom:1px solid #f0ede8">${
          { communication:"💬 Communication", acquisition:"🎯 Acquisition",
            relance:"💰 Relance Argent", contenu:"📱 Contenu Réseaux",
            satisfaction:"⭐ Satisfaction", onboarding:"🚀 Onboarding",
            devis:"📄 Devis" }[agent] || agent
        }</td>
        <td style="padding:10px 16px;text-align:right;font-size:13px;font-weight:600;color:#333;border-bottom:1px solid #f0ede8">${count} actions</td>
      </tr>`).join("");

  return `
<!DOCTYPE html>
<html><body style="font-family:'Helvetica Neue',sans-serif;max-width:600px;margin:0 auto;color:#333;padding:0;background:#f6f5f2">

  <!-- HERO -->
  <div style="background:#1a1a1a;padding:36px 32px;border-radius:12px 12px 0 0;text-align:center">
    <p style="color:rgba(255,255,255,0.5);font-size:12px;text-transform:uppercase;letter-spacing:2px;margin:0 0 12px">Bilan mensuel · ${monthName}</p>
    <div style="font-size:52px;font-weight:800;color:${roiColor};line-height:1">+${stats.roiNet.toLocaleString("fr-FR")}€</div>
    <div style="color:rgba(255,255,255,0.7);font-size:16px;margin:8px 0">générés nets ce mois</div>
    <div style="display:inline-block;background:${roiColor}20;border:1px solid ${roiColor}40;color:${roiColor};font-size:13px;font-weight:600;padding:6px 16px;border-radius:99px;margin-top:12px">
      ROI x${stats.roiMultiplier} — vous gagnez ${stats.roiMultiplier}€ pour chaque euro investi
    </div>
  </div>

  <div style="background:#fff;padding:32px;border:1px solid #eee;border-top:none;border-radius:0 0 12px 12px">

    <!-- HEADLINE -->
    <div style="background:#fff8f3;border-left:3px solid #f26419;padding:14px 18px;border-radius:4px;margin-bottom:28px">
      <p style="margin:0;font-size:15px;font-weight:500;line-height:1.6">${report.headline}</p>
    </div>

    <!-- VALEUR DÉCOMPOSÉE -->
    <p style="font-size:12px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:0.8px;margin:0 0 14px">Comment on calcule ça</p>
    <table style="width:100%;border-collapse:collapse;border:1px solid #f0ede8;border-radius:8px;overflow:hidden;margin-bottom:28px">
      <tr style="background:#f9f8f6">
        <td style="padding:12px 16px;font-size:13px;color:#888">Temps économisé (${stats.timeSaved}h × 70€)</td>
        <td style="padding:12px 16px;text-align:right;font-size:14px;font-weight:600;color:#3B6D11">+${stats.timeSavedEuros.toLocaleString("fr-FR")}€</td>
      </tr>
      <tr>
        <td style="padding:12px 16px;font-size:13px;color:#888">Argent récupéré via relances</td>
        <td style="padding:12px 16px;text-align:right;font-size:14px;font-weight:600;color:#3B6D11">+${stats.moneyRecovered.toLocaleString("fr-FR")}€</td>
      </tr>
      <tr style="background:#f9f8f6">
        <td style="padding:12px 16px;font-size:13px;color:#888">Valeur prospects qualifiés (${stats.newLeads})</td>
        <td style="padding:12px 16px;text-align:right;font-size:14px;font-weight:600;color:#3B6D11">+${stats.prospectsValue.toLocaleString("fr-FR")}€</td>
      </tr>
      <tr style="background:#fdf9f6">
        <td style="padding:12px 16px;font-size:13px;font-weight:600">Total valeur générée</td>
        <td style="padding:12px 16px;text-align:right;font-size:16px;font-weight:700;color:#f26419">${stats.totalValue.toLocaleString("fr-FR")}€</td>
      </tr>
      <tr style="background:#f9f8f6">
        <td style="padding:12px 16px;font-size:13px;color:#888">Coût AutoFlow Pro Coach</td>
        <td style="padding:12px 16px;text-align:right;font-size:14px;color:#e24b4a">-${stats.planPrice}€</td>
      </tr>
      <tr style="background:#edfaf4">
        <td style="padding:14px 16px;font-size:15px;font-weight:700">ROI NET du mois</td>
        <td style="padding:14px 16px;text-align:right;font-size:20px;font-weight:800;color:#3B6D11">+${stats.roiNet.toLocaleString("fr-FR")}€</td>
      </tr>
    </table>

    <!-- HIGHLIGHTS -->
    ${report.highlights?.length ? `
    <div style="margin-bottom:28px">
      <p style="font-size:12px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:0.8px;margin:0 0 12px">Points forts du mois</p>
      ${report.highlights.map(h => `
        <div style="display:flex;gap:10px;margin-bottom:8px">
          <span style="color:#3B6D11;font-weight:700;flex-shrink:0">✓</span>
          <span style="font-size:14px;color:#333;line-height:1.5">${h}</span>
        </div>`).join("")}
    </div>` : ""}

    <!-- ACTIVITÉ PAR AGENT -->
    <p style="font-size:12px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:0.8px;margin:0 0 12px">Activité par agent</p>
    <table style="width:100%;border-collapse:collapse;border:1px solid #f0ede8;border-radius:8px;overflow:hidden;margin-bottom:28px">
      ${agentRows}
    </table>

    <!-- OPPORTUNITÉ MANQUÉE -->
    ${report.missed_opportunity ? `
    <div style="background:#fffbf0;border-left:3px solid #BA7517;padding:14px 18px;border-radius:4px;margin-bottom:16px">
      <p style="font-size:12px;font-weight:600;color:#BA7517;text-transform:uppercase;letter-spacing:0.5px;margin:0 0 6px">💡 Opportunité non exploitée</p>
      <p style="margin:0;font-size:14px;color:#333">${report.missed_opportunity}</p>
    </div>` : ""}

    <!-- UPSELL -->
    ${report.upsell_suggestion ? `
    <div style="background:#1a1a1a;border-radius:8px;padding:20px 24px;margin-bottom:16px">
      <p style="color:rgba(255,255,255,0.6);font-size:12px;margin:0 0 8px">Recommandation</p>
      <p style="color:#fff;font-size:14px;margin:0 0 14px">${report.upsell_suggestion}</p>
      <a href="mailto:${org.email}?subject=Upgrade Elite Business Copilot" style="background:#f26419;color:#fff;padding:10px 20px;text-decoration:none;border-radius:6px;font-size:13px;font-weight:600;display:inline-block">
        Passer à Elite Business →
      </a>
    </div>` : ""}

    <!-- FOCUS MOIS PROCHAIN -->
    <div style="background:#f9f8f6;border-radius:8px;padding:16px 20px;margin-bottom:8px">
      <p style="font-size:12px;font-weight:600;color:#888;margin:0 0 6px">Le mois prochain, on focus sur</p>
      <p style="font-size:14px;font-weight:500;color:#333;margin:0">${report.next_month_focus}</p>
    </div>

    <p style="font-size:13px;color:#888;font-style:italic;margin:16px 0 0;line-height:1.6">${report.client_message}</p>

    <p style="color:#ccc;font-size:11px;margin-top:24px;text-align:center;border-top:1px solid #f0ede8;padding-top:16px">
      AutoFlow · ${org.name} · Rapport ${monthName}
    </p>
  </div>
</body></html>`;
}

// ============================================
// WEBHOOK HANDLER
// ============================================
export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (req.headers["x-autoflow-token"] !== process.env.WEBHOOK_SECRET)
    return res.status(401).json({ error: "Unauthorized" });

  const { orgId, agentId } = req.body;
  if (!orgId || !agentId) return res.status(400).json({ error: "orgId et agentId requis" });

  try {
    const result = await sendMonthlyROIReport({ orgId, agentId });
    return res.status(200).json({ success: true, data: result });
  } catch (err) {
    console.error("ROI Reporting error:", err);
    return res.status(500).json({ error: err.message });
  }
}
