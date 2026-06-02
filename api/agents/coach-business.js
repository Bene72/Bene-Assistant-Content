// ============================================
// AGENT COACH BUSINESS — AutoFlow
// api/agents/coach-business.js
// ============================================
// Chaque lundi matin, le client reçoit :
// → Ce qui s'est passé cette semaine
// → Les chiffres clés
// → L'action prioritaire de la semaine
// → Les alertes à traiter
// → Les opportunités à saisir

import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const resend = new Resend(process.env.RESEND_API_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

// ============================================
// SYSTEM PROMPT
// ============================================
const COACH_BUSINESS_PROMPT = `Tu es le copilote business IA de {org_name}.
Chaque lundi matin tu envoies un récap hebdomadaire court, actionnable, sans bullshit.

PHILOSOPHIE
- Maximum 200 mots — le client lit ça en 90 secondes avec son café
- Toujours terminer par UNE seule action prioritaire
- Donner des chiffres précis, pas des approximations
- Si tout va bien → le dire clairement
- Si un problème se pointe → le nommer sans dramatiser
- Ton : direct, comme un bon associé qui parle vrai

STRUCTURE OBLIGATOIRE
1. Accroche (1 phrase — la stat la plus marquante de la semaine)
2. Ce qui s'est passé (3-5 bullets max, chiffrés)
3. Ce qui nécessite ton attention (0-2 alertes max)
4. Action prioritaire de la semaine (1 seule, concrète)
5. Opportunité à saisir (1 seule)

FORMAT RÉPONSE JSON :
{
  "subject": "...",
  "accroche": "...",
  "bullets": ["...", "..."],
  "alertes": [{"titre":"...","detail":"...","urgence":"low|medium|high"}],
  "action_prioritaire": "...",
  "action_detail": "...",
  "opportunite": "...",
  "score_semaine": 8,
  "score_label": "Bonne semaine",
  "conseil_bonus": "..."
}`;

// ============================================
// COLLECTER LES DONNÉES DE LA SEMAINE
// ============================================
async function collectWeekData(orgId) {
  const weekAgo = new Date(Date.now() - 7 * 86400000).toISOString();
  const twoWeeksAgo = new Date(Date.now() - 14 * 86400000).toISOString();

  const [
    newLeads, hotLeads, wonLeads,
    tasksDone, tasksOverdue, tasksBlocked,
    conversations, escalations,
    eventsWeek, eventsPrevWeek,
    inactifClients, packLeads
  ] = await Promise.all([
    // Leads semaine courante
    supabase.from("leads").select("id,score,stage,source", { count: "exact" })
      .eq("org_id", orgId).gte("created_at", weekAgo),
    supabase.from("leads").select("id,full_name,score,stage", { count: "exact" })
      .eq("org_id", orgId).gte("score", 70).neq("stage", "won").neq("stage", "lost"),
    supabase.from("leads").select("id,full_name", { count: "exact" })
      .eq("org_id", orgId).eq("stage", "won").gte("updated_at", weekAgo),

    // Tâches
    supabase.from("tasks").select("id", { count: "exact" })
      .eq("org_id", orgId).eq("status", "done").gte("updated_at", weekAgo),
    supabase.from("tasks").select("id,title", { count: "exact" })
      .eq("org_id", orgId).not("status", "in", '("done","cancelled")')
      .lt("due_date", new Date().toISOString()),
    supabase.from("tasks").select("id,title")
      .eq("org_id", orgId).eq("status", "blocked").limit(3),

    // Conversations
    supabase.from("conversations").select("id", { count: "exact" })
      .eq("org_id", orgId).eq("status", "open"),
    supabase.from("conversations").select("id,contact_name", { count: "exact" })
      .eq("org_id", orgId).eq("status", "escalated"),

    // Events pour calcul volume
    supabase.from("events").select("type", { count: "exact" })
      .eq("org_id", orgId).gte("created_at", weekAgo),
    supabase.from("events").select("type", { count: "exact" })
      .eq("org_id", orgId).gte("created_at", twoWeeksAgo).lt("created_at", weekAgo),

    // Clients inactifs
    supabase.from("leads").select("id,full_name")
      .eq("org_id", orgId).eq("stage", "won")
      .lt("last_contact_at", new Date(Date.now() - 14 * 86400000).toISOString())
      .limit(3),

    // Packs expirés
    supabase.from("leads").select("id,full_name,enriched_data")
      .eq("org_id", orgId).eq("stage", "won")
      .not("enriched_data->pack_sessions_total", "is", null),
  ]);

  const automationsCount = eventsWeek.count || 0;
  const prevAutomationsCount = eventsPrevWeek.count || 0;
  const automationsDelta = automationsCount - prevAutomationsCount;
  const hoursaved = Math.round(automationsCount * 0.18 * 10) / 10;

  // Chiffre potentiel récupérable
  const proposalLeads = (await supabase.from("leads").select("id", { count: "exact" })
    .eq("org_id", orgId).eq("stage", "proposal")).count || 0;
  const totalAtStake = proposalLeads * 490 + (inactifClients.data?.length || 0) * 150;

  return {
    newLeads: newLeads.count || 0,
    hotLeads: hotLeads.data || [],
    wonLeads: wonLeads.data || [],
    tasksDone: tasksDone.count || 0,
    tasksOverdue: tasksOverdue.count || 0,
    tasksBlocked: tasksBlocked.data || [],
    openConversations: conversations.count || 0,
    escalations: escalations.data || [],
    automationsCount,
    automationsDelta,
    hoursaved,
    inactifClients: inactifClients.data || [],
    totalAtStake,
    proposalLeads,
  };
}

// ============================================
// GÉNÉRER ET ENVOYER LE RAPPORT
// ============================================
export async function sendWeeklyCoachReport({ orgId, agentId }) {
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  const data = await collectWeekData(orgId);

  const systemPrompt = COACH_BUSINESS_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  const prompt = `Génère le récap hebdomadaire du lundi pour ${org.name}.

DONNÉES DE LA SEMAINE :
- Nouveaux prospects : ${data.newLeads}
- Prospects chauds (score ≥70) : ${data.hotLeads.length} — ${data.hotLeads.map(l => `${l.full_name} (${l.score}/100)`).join(", ") || "aucun"}
- Nouveaux clients signés : ${data.wonLeads.length} — ${data.wonLeads.map(l => l.full_name).join(", ") || "aucun"}
- Tâches complétées : ${data.tasksDone}
- Tâches en retard : ${data.tasksOverdue}
- Tâches bloquées : ${data.tasksBlocked.map(t => t.title).join(", ") || "aucune"}
- Conversations ouvertes : ${data.openConversations}
- Escalades en attente : ${data.escalations.length} — ${data.escalations.map(e => e.contact_name).join(", ") || "aucune"}
- Actions automatisées : ${data.automationsCount} (${data.automationsDelta >= 0 ? "+" : ""}${data.automationsDelta} vs semaine dernière)
- Heures économisées : ${data.hoursaved}h
- Clients inactifs : ${data.inactifClients.map(c => c.full_name).join(", ") || "aucun"}
- Argent récupérable : ${data.totalAtStake.toLocaleString("fr-FR")}€ (${data.proposalLeads} devis + ${data.inactifClients.length} inactifs)

Génère le rapport selon la structure. Score la semaine sur 10.
Réponds JSON strict.`;

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1000,
    system: systemPrompt,
    messages: [{ role: "user", content: prompt }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const report = json ? JSON.parse(json[0]) : null;
  if (!report) throw new Error("Génération rapport échouée");

  // Envoyer l'email
  const { data: admins } = await supabase
    .from("users").select("email").eq("org_id", orgId).in("role", ["owner", "admin"]);

  if (admins?.length) {
    await resend.emails.send({
      from: "AutoFlow <lundi@autoflow.fr>",
      to: admins.map(a => a.email),
      subject: report.subject || `☕ Ton lundi business — ${new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "long" })}`,
      html: buildWeeklyEmail(report, data, org),
    });
  }

  // Logger
  await supabase.from("events").insert({
    org_id: orgId,
    type: "report.weekly",
    source: agentId,
    data: {
      score: report.score_semaine,
      new_leads: data.newLeads,
      won: data.wonLeads.length,
      automations: data.automationsCount,
    },
  });

  return { sent: true, score: report.score_semaine, report };
}

// ============================================
// EMAIL HTML
// ============================================
function buildWeeklyEmail(report, data, org) {
  const scoreColor = report.score_semaine >= 8 ? "#3B6D11"
    : report.score_semaine >= 6 ? "#f26419" : "#e24b4a";
  const scoreEmoji = report.score_semaine >= 8 ? "🔥" : report.score_semaine >= 6 ? "👍" : "⚠️";
  const today = new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });

  return `
<!DOCTYPE html>
<html><body style="font-family:'Helvetica Neue',sans-serif;max-width:560px;margin:0 auto;color:#333;padding:0;background:#f6f5f2">

  <!-- HEADER -->
  <div style="background:#1a1a1a;padding:24px 32px;border-radius:12px 12px 0 0;display:flex;justify-content:space-between;align-items:center">
    <div>
      <div style="color:#fff;font-size:16px;font-weight:600">${org.name}</div>
      <div style="color:rgba(255,255,255,0.5);font-size:12px;margin-top:3px">Récap · ${today}</div>
    </div>
    <div style="text-align:right">
      <div style="font-size:28px;font-weight:700;color:${scoreColor}">${scoreEmoji} ${report.score_semaine}/10</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.5);margin-top:2px">${report.score_label}</div>
    </div>
  </div>

  <!-- BODY -->
  <div style="background:#fff;padding:28px 32px;border:1px solid #eee;border-top:none;border-radius:0 0 12px 12px">

    <!-- ACCROCHE -->
    <div style="background:#fff8f3;border-left:3px solid #f26419;padding:14px 18px;border-radius:4px;margin-bottom:24px">
      <p style="margin:0;font-size:15px;font-weight:500;color:#333;line-height:1.5">${report.accroche}</p>
    </div>

    <!-- MÉTRIQUES RAPIDES -->
    <div style="display:flex;gap:10px;margin-bottom:24px;flex-wrap:wrap">
      <div style="flex:1;min-width:100px;background:#f9f8f6;border-radius:8px;padding:12px;text-align:center">
        <div style="font-size:22px;font-weight:700;color:#333">${data.newLeads}</div>
        <div style="font-size:11px;color:#888;margin-top:2px">prospects</div>
      </div>
      <div style="flex:1;min-width:100px;background:#f9f8f6;border-radius:8px;padding:12px;text-align:center">
        <div style="font-size:22px;font-weight:700;color:#3B6D11">${data.wonLeads.length}</div>
        <div style="font-size:11px;color:#888;margin-top:2px">signés</div>
      </div>
      <div style="flex:1;min-width:100px;background:#f9f8f6;border-radius:8px;padding:12px;text-align:center">
        <div style="font-size:22px;font-weight:700;color:#f26419">${data.hoursaved}h</div>
        <div style="font-size:11px;color:#888;margin-top:2px">économisées</div>
      </div>
      <div style="flex:1;min-width:100px;background:#f9f8f6;border-radius:8px;padding:12px;text-align:center">
        <div style="font-size:22px;font-weight:700;color:#185FA5">${data.automationsCount}</div>
        <div style="font-size:11px;color:#888;margin-top:2px">automatisations</div>
      </div>
    </div>

    <!-- BULLETS -->
    <div style="margin-bottom:24px">
      <p style="font-size:12px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:0.8px;margin:0 0 12px">Cette semaine</p>
      ${(report.bullets || []).map(b => `
        <div style="display:flex;gap:10px;margin-bottom:8px;align-items:flex-start">
          <span style="color:#f26419;font-weight:700;flex-shrink:0">→</span>
          <span style="font-size:14px;color:#333;line-height:1.5">${b}</span>
        </div>`).join("")}
    </div>

    <!-- ALERTES -->
    ${report.alertes?.length ? `
    <div style="margin-bottom:24px">
      <p style="font-size:12px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:0.8px;margin:0 0 12px">⚠️ À traiter</p>
      ${report.alertes.map(a => `
        <div style="background:${a.urgence === "high" ? "#fdf0f0" : "#fffbf0"};border-left:3px solid ${a.urgence === "high" ? "#e24b4a" : "#BA7517"};padding:12px 16px;border-radius:4px;margin-bottom:8px">
          <div style="font-size:13px;font-weight:600;color:#333">${a.titre}</div>
          <div style="font-size:12px;color:#666;margin-top:4px">${a.detail}</div>
        </div>`).join("")}
    </div>` : ""}

    <!-- ACTION PRIORITAIRE -->
    <div style="background:#1a1a1a;border-radius:8px;padding:20px 24px;margin-bottom:16px">
      <p style="color:rgba(255,255,255,0.6);font-size:11px;text-transform:uppercase;letter-spacing:1px;margin:0 0 8px">Action prioritaire cette semaine</p>
      <p style="color:#fff;font-size:15px;font-weight:600;margin:0 0 6px">${report.action_prioritaire}</p>
      <p style="color:rgba(255,255,255,0.6);font-size:13px;margin:0">${report.action_detail}</p>
    </div>

    <!-- OPPORTUNITÉ -->
    <div style="background:#edfaf4;border-radius:8px;padding:16px 20px;margin-bottom:24px">
      <p style="color:#3B6D11;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;margin:0 0 6px">💡 Opportunité</p>
      <p style="color:#333;font-size:14px;margin:0;line-height:1.5">${report.opportunite}</p>
    </div>

    ${report.conseil_bonus ? `
    <div style="border-top:1px solid #f0ede8;padding-top:16px">
      <p style="font-size:13px;color:#888;font-style:italic;margin:0">${report.conseil_bonus}</p>
    </div>` : ""}

    <p style="color:#ccc;font-size:11px;margin-top:20px;text-align:center">
      AutoFlow Copilote · ${org.name} · Prochain récap lundi ${new Date(Date.now() + 7 * 86400000).toLocaleDateString("fr-FR", { day: "numeric", month: "long" })}
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
    const result = await sendWeeklyCoachReport({ orgId, agentId });
    return res.status(200).json({ success: true, data: result });
  } catch (err) {
    console.error("Coach Business error:", err);
    return res.status(500).json({ error: err.message });
  }
}
