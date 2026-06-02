// ============================================
// AGENT CONTENU RÉSEAUX — AutoFlow
// api/agents/contenu-reseaux.js
// ============================================
// Génère : posts Instagram, stories, scripts Reels,
//          carrousels, témoignages → contenu,
//          calendrier éditorial mensuel

import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const resend = new Resend(process.env.RESEND_API_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

// ============================================
// SYSTEM PROMPT — Agent Contenu
// ============================================
const CONTENU_SYSTEM_PROMPT = `Tu es le directeur créatif IA de {org_name}.
Tu génères du contenu Instagram qui convertit : éducatif, inspirant, authentique.

IDENTITÉ DE MARQUE
{org_context}

TON & STYLE INSTAGRAM
- Voix : directe, motivante, experte mais accessible
- Pas de jargon inutile — parler comme un ami coach
- Emojis : oui mais avec parcimonie (1-2 max par post)
- Hashtags : pertinents et spécifiques, pas de spam
- Stories : courtes, visuelles, interactives (sondages, questions)
- Carrousels : valeur dense, slide 1 = hook fort, dernière slide = CTA

PILIERS DE CONTENU (rotation équilibrée)
1. ÉDUCATION (40%) — conseils techniques, erreurs courantes, "comment faire"
2. INSPIRATION (25%) — transformations, before/after, résultats clients
3. COULISSES (20%) — ta vie de coach, tes entraînements, ton quotidien
4. VENTE DOUCE (15%) — tes offres, témoignages, appels à l'action

FORMATS
- Post simple : 150-220 mots, hook fort en ligne 1, valeur, CTA, 10-15 hashtags
- Carrousel : 5-8 slides, chaque slide = 1 idée forte
- Script Reel : 30-60 secondes, structure hook/valeur/CTA
- Story : 3-5 écrans, interactif si possible

FORMAT RÉPONSE JSON strict :
{
  "type": "post|carrousel|reel|story",
  "pilier": "education|inspiration|coulisses|vente",
  "hook": "...",
  "caption": "...",
  "hashtags": ["#crossfit", "#hyrox", ...],
  "slides": null,
  "script": null,
  "story_screens": null,
  "best_time_to_post": "07:00|12:00|18:00|20:00",
  "expected_engagement": "low|medium|high|viral",
  "notes_visuels": "..."
}`;

// ============================================
// GÉNÉRER UN POST UNIQUE
// ============================================
export async function generatePost({ orgId, agentId, postType, topic, clientInfo }) {
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  const systemPrompt = CONTENU_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  const typeInstructions = {
    post: "Génère un post Instagram classique avec un hook percutant, du contenu valeur, un CTA et les hashtags.",
    carrousel: "Génère un carrousel 6 slides. Chaque slide a un titre court + 2-3 lignes de texte. Slide 1 = hook fort. Slide 6 = CTA avec lien Calendly.",
    reel: "Génère un script Reel 30-45 secondes. Structure: hook 3s / problème 5s / solution 15s / preuve 10s / CTA 5s. Inclure les directions visuelles.",
    story: "Génère une séquence 4 stories. Screen 1 = question ou teaser. Screen 2-3 = valeur. Screen 4 = CTA avec lien en bio.",
    avant_apres: "Génère un post témoignage avant/après. Raconter la transformation du client (anonymisé si besoin). Empathique, concret, chiffres si possible.",
  };

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1200,
    system: systemPrompt,
    messages: [{
      role: "user",
      content: `Format demandé : ${postType || "post"}
Sujet / Angle : ${topic || "conseil fitness ou crossfit"}
${clientInfo ? `Info client pour témoignage : ${clientInfo}` : ""}

${typeInstructions[postType] || typeInstructions.post}

Adapte le contenu à la cible : sportifs 25-45 ans, Nantes et en ligne, intéressés CrossFit/Hyrox/fitness.
Réponds uniquement JSON.`
    }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const result = json ? JSON.parse(json[0]) : null;
  if (!result) throw new Error("Génération contenu échouée");

  // Sauvegarder en base
  await supabase.from("events").insert({
    org_id: orgId,
    type: "contenu.generated",
    source: agentId,
    data: { type: postType, topic, pilier: result.pilier, engagement: result.expected_engagement },
  });

  return result;
}

// ============================================
// CALENDRIER ÉDITORIAL MENSUEL COMPLET
// ============================================
export async function generateMonthlyCalendar({ orgId, agentId, month }) {
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  const systemPrompt = CONTENU_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  // Générer 12 posts (3 par semaine × 4 semaines)
  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 4000,
    system: systemPrompt,
    messages: [{
      role: "user",
      content: `Génère le calendrier éditorial complet pour ${month || "le mois prochain"}.
      
3 posts par semaine (lundi, mercredi, vendredi) = 12 posts total.

Répartition :
- 5 posts éducatifs (CrossFit, Hyrox, fitness, nutrition, récupération)
- 3 posts inspiration / résultats
- 2 posts coulisses (quotidien coach)
- 2 posts vente douce (offres, témoignages)

Varier les formats : post classique, carrousel, reel, story.

Réponds JSON avec cette structure :
{
  "month": "Juin 2026",
  "posts": [
    {
      "week": 1,
      "day": "Lundi 2 juin",
      "format": "post|carrousel|reel|story",
      "pilier": "education|inspiration|coulisses|vente",
      "topic": "...",
      "hook": "...",
      "caption_preview": "... (100 mots max)",
      "hashtags": ["#crossfit", ...],
      "best_time": "07:00",
      "notes_visuels": "Photo/vidéo recommandée",
      "expected_engagement": "medium"
    }
  ],
  "tips_du_mois": ["conseil 1", "conseil 2"],
  "sujets_tendance": ["tendance 1", "tendance 2"]
}`
    }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const calendar = json ? JSON.parse(json[0]) : null;
  if (!calendar) throw new Error("Génération calendrier échouée");

  // Envoyer le calendrier par email
  const { data: admins } = await supabase.from("users").select("email").eq("org_id", orgId).in("role", ["owner", "admin"]);

  if (admins?.length) {
    await resend.emails.send({
      from: "AutoFlow <content@autoflow.fr>",
      to: admins.map(a => a.email),
      subject: `📅 Calendrier éditorial Instagram — ${calendar.month}`,
      html: buildCalendarEmail(calendar, org),
    });
  }

  // Sauvegarder
  await supabase.from("events").insert({
    org_id: orgId,
    type: "contenu.calendar_generated",
    source: agentId,
    data: { month: calendar.month, posts_count: calendar.posts?.length },
  });

  return calendar;
}

// ============================================
// GÉNÉRER UNE SEMAINE DE CONTENU COMPLÈTE
// ============================================
export async function generateWeekContent({ orgId, agentId, weekTheme }) {
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  const systemPrompt = CONTENU_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 3000,
    system: systemPrompt,
    messages: [{
      role: "user",
      content: `Génère le contenu complet pour cette semaine.
Thème de la semaine : ${weekTheme || "préparation Hyrox"}

Produire exactement 3 contenus :
1. LUNDI — Post éducatif (carrousel 5 slides complet avec tout le texte)
2. MERCREDI — Script Reel 45 secondes (complet, avec directions visuelles)
3. VENDREDI — Post inspiration/résultat + Story 3 écrans

Pour chaque contenu, générer le texte COMPLET (pas juste un aperçu).

Format JSON :
{
  "theme": "...",
  "lundi": { "type": "carrousel", "slides": [{"titre":"...","texte":"..."}], "caption": "...", "hashtags": [], "notes_visuels": "..." },
  "mercredi": { "type": "reel", "script": "...", "structure": [...], "caption": "...", "hashtags": [], "notes_visuels": "..." },
  "vendredi": { "type": "post", "caption": "...", "hashtags": [], "story_screens": [...], "notes_visuels": "..." }
}`
    }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  const weekContent = json ? JSON.parse(json[0]) : null;
  if (!weekContent) throw new Error("Génération semaine échouée");

  // Notifier
  const { data: admins } = await supabase.from("users").select("email").eq("org_id", orgId).in("role", ["owner", "admin"]);

  if (admins?.length) {
    await resend.emails.send({
      from: "AutoFlow <content@autoflow.fr>",
      to: admins.map(a => a.email),
      subject: `📱 Contenu Instagram de la semaine — ${weekTheme || "prêt à publier"}`,
      html: buildWeekEmail(weekContent, org),
    });
  }

  return weekContent;
}

// ============================================
// TRANSFORMER UN TÉMOIGNAGE EN CONTENU
// ============================================
export async function testimonialToContent({ orgId, agentId, testimonial, clientName, clientGoal }) {
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: agentConfig } = await supabase.from("agents").select("*").eq("id", agentId).single();

  const systemPrompt = CONTENU_SYSTEM_PROMPT
    .replace("{org_name}", org.name)
    .replace("{org_context}", agentConfig?.system_prompt || "");

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1000,
    system: systemPrompt,
    messages: [{
      role: "user",
      content: `Transforme ce témoignage client en contenu Instagram percutant.

Témoignage brut : "${testimonial}"
Prénom client : ${clientName || "un client"} (utiliser le prénom seulement)
Objectif atteint : ${clientGoal || "non précisé"}

Générer 3 formats différents à partir du même témoignage :
1. Post classique storytelling (avec le témoignage reformulé de façon impactante)
2. Slide 1 d'un carrousel "Transformation de [prénom]"  
3. Idée de Reel 30 secondes (interview fictive ou voix off)

Format JSON :
{
  "post": { "caption": "...", "hashtags": [], "hook": "..." },
  "carrousel_slide1": { "titre": "...", "sous_titre": "...", "texte_hook": "..." },
  "reel_concept": { "concept": "...", "script_30s": "...", "notes_visuels": "..." }
}`
    }],
  });

  const raw = completion.content[0].text;
  const json = raw.match(/\{[\s\S]*\}/);
  return json ? JSON.parse(json[0]) : null;
}

// ============================================
// HELPERS EMAIL
// ============================================
function buildCalendarEmail(calendar, org) {
  const postsHtml = (calendar.posts || []).map(p => `
    <tr style="border-bottom:1px solid #eee">
      <td style="padding:10px 12px;font-size:13px;color:#666;white-space:nowrap">${p.day}</td>
      <td style="padding:10px 12px">
        <div style="font-size:11px;font-weight:600;color:${p.pilier==='education'?'#185FA5':p.pilier==='inspiration'?'#3B6D11':p.pilier==='vente'?'#BA7517':'#666'};text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px">${p.format} · ${p.pilier}</div>
        <div style="font-size:13px;font-weight:500;color:#333">${p.hook}</div>
        <div style="font-size:12px;color:#888;margin-top:3px">${p.notes_visuels}</div>
      </td>
      <td style="padding:10px 12px;font-size:12px;color:#888;text-align:center">${p.best_time}</td>
    </tr>
  `).join('');

  return `
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',sans-serif;max-width:680px;margin:0 auto;color:#333;padding:20px">
  <div style="border-bottom:3px solid #f26419;padding-bottom:12px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center">
    <strong style="font-size:18px">${org.name}</strong>
    <span style="font-size:14px;color:#888">📅 ${calendar.month}</span>
  </div>
  <h2 style="font-size:18px;margin:0 0 20px">Calendrier éditorial Instagram</h2>
  <table style="width:100%;border-collapse:collapse;border:1px solid #eee;border-radius:8px;overflow:hidden">
    <thead style="background:#f9f9f9">
      <tr>
        <th style="padding:10px 12px;text-align:left;font-size:12px;color:#888">DATE</th>
        <th style="padding:10px 12px;text-align:left;font-size:12px;color:#888">CONTENU</th>
        <th style="padding:10px 12px;text-align:center;font-size:12px;color:#888">HEURE</th>
      </tr>
    </thead>
    <tbody>${postsHtml}</tbody>
  </table>
  ${calendar.tips_du_mois?.length ? `
  <div style="background:#fff3ec;border-radius:8px;padding:16px;margin-top:20px">
    <strong style="font-size:13px;color:#f26419">💡 Tips du mois</strong>
    <ul style="margin:8px 0 0;padding-left:20px">
      ${calendar.tips_du_mois.map(t => `<li style="font-size:13px;color:#555;margin-bottom:6px">${t}</li>`).join('')}
    </ul>
  </div>` : ''}
  <p style="color:#999;font-size:12px;margin-top:24px">Généré par AutoFlow · ${org.name}</p>
</body></html>`;
}

function buildWeekEmail(weekContent, org) {
  return `
<!DOCTYPE html><html><body style="font-family:'Helvetica Neue',sans-serif;max-width:600px;margin:0 auto;color:#333;padding:20px">
  <div style="border-bottom:3px solid #f26419;padding-bottom:12px;margin-bottom:24px">
    <strong>${org.name}</strong> · Contenu Instagram de la semaine
  </div>
  
  <div style="background:#e6f1fb;border-radius:8px;padding:16px;margin-bottom:16px">
    <div style="font-size:11px;font-weight:600;color:#185FA5;text-transform:uppercase;margin-bottom:8px">📌 LUNDI — Carrousel</div>
    <strong>${weekContent.lundi?.slides?.[0]?.titre || 'Slide 1'}</strong>
    <p style="font-size:13px;color:#555;margin:8px 0 0">${weekContent.lundi?.caption?.slice(0,200)}...</p>
    <div style="font-size:12px;color:#888;margin-top:8px">📸 ${weekContent.lundi?.notes_visuels}</div>
  </div>

  <div style="background:#edfaf4;border-radius:8px;padding:16px;margin-bottom:16px">
    <div style="font-size:11px;font-weight:600;color:#3B6D11;text-transform:uppercase;margin-bottom:8px">🎬 MERCREDI — Reel 45s</div>
    <p style="font-size:13px;color:#555;font-style:italic">"${weekContent.mercredi?.script?.slice(0,250)}..."</p>
    <div style="font-size:12px;color:#888;margin-top:8px">📸 ${weekContent.mercredi?.notes_visuels}</div>
  </div>

  <div style="background:#fff3ec;border-radius:8px;padding:16px;margin-bottom:16px">
    <div style="font-size:11px;font-weight:600;color:#f26419;text-transform:uppercase;margin-bottom:8px">✨ VENDREDI — Post + Stories</div>
    <p style="font-size:13px;color:#555">${weekContent.vendredi?.caption?.slice(0,200)}...</p>
    <div style="font-size:12px;color:#888;margin-top:8px">📸 ${weekContent.vendredi?.notes_visuels}</div>
  </div>
  
  <p style="color:#999;font-size:12px;margin-top:24px">Généré par AutoFlow · Réponds à cet email pour des ajustements</p>
</body></html>`;
}

// ============================================
// WEBHOOK HANDLER
// ============================================
export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (req.headers["x-autoflow-token"] !== process.env.WEBHOOK_SECRET)
    return res.status(401).json({ error: "Unauthorized" });

  const { action, orgId, agentId, postType, topic, clientInfo, month, weekTheme, testimonial, clientName, clientGoal } = req.body;

  try {
    let result;
    switch (action) {
      case "generate_post":
        result = await generatePost({ orgId, agentId, postType, topic, clientInfo });
        break;
      case "monthly_calendar":
        result = await generateMonthlyCalendar({ orgId, agentId, month });
        break;
      case "week_content":
        result = await generateWeekContent({ orgId, agentId, weekTheme });
        break;
      case "testimonial_to_content":
        result = await testimonialToContent({ orgId, agentId, testimonial, clientName, clientGoal });
        break;
      default:
        return res.status(400).json({ error: `Action inconnue: ${action}` });
    }
    return res.status(200).json({ success: true, data: result });
  } catch (err) {
    console.error("Contenu réseaux error:", err);
    return res.status(500).json({ error: err.message });
  }
}
