// ============================================
// AGENT COMMUNICATION — AutoFlow
// apps/api/agents/communication.js
// ============================================
// Gère : emails entrants, chat widget, escalade humaine
// Déployé sur : Vercel Serverless Functions

import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const resend = new Resend(process.env.RESEND_API_KEY);
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

// ============================================
// SYSTEM PROMPT — Agent Communication
// ============================================
const COMMUNICATION_SYSTEM_PROMPT = "Tu es l'assistant personnel de Benoit, coach sportif spécialisé en fitness, CrossFit et Hyrox.\nTu réponds aux messages de ses clients et prospects avec son style : chaleureux et motivant avec les clients, direct et efficace avec les prospects.\n\n## QUI EST Benoit\n- Coach certifié fitness, CrossFit Level 1, préparateur Hyrox\n- Accompagnement physique en salle + coaching en ligne (plans d'entraînement, suivi vidéo, appels hebdo)\n- Tarifs : séance individuelle 70€, pack 10 séances 600€, coaching en ligne 150€/mois\n- Basé à Nantes — disponible du lundi au samedi\n\n## TON STYLE DE RÉPONSE\n- Avec les clients actifs : chaleureux, motivant, comme un ami coach. Tutoie naturellement.\n- Avec les nouveaux prospects : professionnel mais accessible, jamais vendeur agressif.\n- Jamais de jargon trop technique sauf si le client l'utilise lui-même.\n- Phrases courtes. Dynamique. Positif.\n- Ajoute parfois une petite touche d'humour sportif, mais garde le cap sur l'utilité.\n\n## CE QUE TU PEUX FAIRE\n- Répondre aux questions sur les programmes, tarifs, disponibilités\n- Confirmer/rappeler les séances à venir\n- Encourager après une séance difficile ou un bon résultat\n- Envoyer le lien de réservation : https://calendly.com/benoit-coach\n- Envoyer le lien de paiement : https://dashboard.stripe.com/payment-links (à créer — voir guide)\n- Rediriger vers Benoit pour les questions de santé, blessures, nutrition médicale\n\n## CE QUE TU NE FAIS PAS\n- Tu ne donnes JAMAIS de conseils médicaux ou nutritionnels précis (macros, suppléments médicaux)\n- Tu ne fais pas de remise sans accord explicite du coach\n- Tu n'inventes pas des disponibilités — si tu ne sais pas, tu proposes de vérifier\n\n## ESCALADE VERS LE COACH si :\n- Blessure ou douleur mentionnée par le client\n- Demande de remise ou cas particulier financier\n- Client très mécontent ou situation tendue\n- Question sur un programme très spécifique Hyrox/compétition\n\n## FORMAT DE RÉPONSE (JSON strict)\n{\n  \"message\": \"ta réponse au client\",\n  \"sentiment\": \"positive|neutral|negative\",\n  \"intent\": \"booking|support|info|complaint|sales|encouragement\",\n  \"escalate\": false,\n  \"escalation_reason\": null,\n  \"suggested_actions\": [\n    {\"type\": \"create_task\", \"title\": \"...\", \"priority\": \"low|medium|high|urgent\"},\n    {\"type\": \"send_link\", \"link_type\": \"calendar|payment|program\"},\n    {\"type\": \"schedule_callback\", \"delay_hours\": 24}\n  ],\n  \"confidence\": 0.95\n}\n\n## EXEMPLES DE RÉPONSES\n\nClient : \"C'était dur aujourd'hui, j'ai failli abandonner\"\n→ \"Haha mais t'as pas abandonné — c'est ça qui compte ! 💪 Les séances les plus dures sont celles qui font le plus avancer. Benoit va être content de voir tes stats. À très vite !\"\n\nProspect : \"Bonjour, je veux me préparer pour Hyrox Paris en novembre, vous faites ça ?\"\n→ \"Bonjour ! Oui, la préparation Hyrox c'est exactement ce que fait Benoit — il a déjà accompagné plusieurs athlètes sur cette course. Pour novembre, vous êtes dans les temps pour une prépa sérieuse. Je vous propose un appel découverte gratuit de 20 min pour qu'il évalue votre niveau et construise votre plan. Ça vous va si je vous envoie le lien pour réserver ?\"\n\nClient inactif depuis 2 semaines :\n→ \"Hé [Prénom] ! Ça fait un moment qu'on t'a pas vu 😄 Tout va bien ? Benoit pense à toi — si t'as besoin d'un coup de boost ou si tu veux ajuster ton programme, dis-le moi. La reprise c'est souvent la séance la plus importante.\"";

// ============================================
// HANDLER PRINCIPAL
// ============================================
export async function handleIncomingMessage({
  orgId,
  agentId,
  conversationId,
  contactEmail,
  contactName,
  message,
  channel = "email",
}) {
  // 1. Récupérer la config agent + historique
  const [agentData, historyData, orgData] = await Promise.all([
    supabase.from("agents").select("*").eq("id", agentId).single(),
    supabase
      .from("messages")
      .select("role, content")
      .eq("conversation_id", conversationId)
      .order("created_at", { ascending: true })
      .limit(20),
    supabase.from("organisations").select("*").eq("id", orgId).single(),
  ]);

  const agent = agentData.data;
  const history = historyData.data || [];
  const org = orgData.data;

  // 2. Sauvegarder le message entrant
  await supabase.from("messages").insert({
    conversation_id: conversationId,
    role: "user",
    content: message,
    metadata: { channel, contact_email: contactEmail },
  });

  // 3. Construire le system prompt personnalisé
  const systemPrompt = (agent?.system_prompt || COMMUNICATION_SYSTEM_PROMPT)
    .replace("{org_name}", org.name)
    .replace("{org_domain}", org.website || "services aux entreprises");

  // 4. Appel Claude
  const claudeMessages = [
    ...history.map((m) => ({ role: m.role, content: m.content })),
    { role: "user", content: message },
  ];

  let response;
  try {
    const completion = await anthropic.messages.create({
      model: agent?.model || "claude-sonnet-4-20250514",
      max_tokens: 1024,
      system: systemPrompt,
      messages: claudeMessages,
    });

    const rawText = completion.content[0].text;
    // Extraire le JSON proprement
    const jsonMatch = rawText.match(/\{[\s\S]*\}/);
    response = jsonMatch ? JSON.parse(jsonMatch[0]) : null;

    if (!response) throw new Error("Réponse non parseable");
  } catch (err) {
    // Fallback gracieux
    response = {
      message:
        "Merci pour votre message. Notre équipe va traiter votre demande et vous recontacter très prochainement.",
      sentiment: "neutral",
      intent: "other",
      escalate: true,
      escalation_reason: "Erreur agent IA — traitement manuel requis",
      suggested_actions: [],
      confidence: 0,
    };
    console.error("Agent communication error:", err);
  }

  // 5. Sauvegarder la réponse
  await supabase.from("messages").insert({
    conversation_id: conversationId,
    role: "assistant",
    content: response.message,
    metadata: {
      sentiment: response.sentiment,
      intent: response.intent,
      confidence: response.confidence,
      escalate: response.escalate,
    },
  });

  // 6. Mettre à jour la conversation
  const convUpdate = {
    sentiment: response.sentiment,
    message_count: history.length + 2,
    updated_at: new Date().toISOString(),
  };
  if (response.escalate) {
    convUpdate.status = "escalated";
    convUpdate.escalated_at = new Date().toISOString();
    convUpdate.escalation_reason = response.escalation_reason;
  }
  await supabase
    .from("conversations")
    .update(convUpdate)
    .eq("id", conversationId);

  // 7. Exécuter les actions suggérées
  await executeActions(response.suggested_actions, orgId, agentId, conversationId);

  // 8. Envoyer la réponse par email si channel = email
  if (channel === "email" && contactEmail) {
    await resend.emails.send({
      from: `${org.name} <noreply@autoflow.fr>`,
      to: contactEmail,
      subject: `Re: Votre message — ${org.name}`,
      html: formatEmailResponse(response.message, org, contactName),
    });
  }

  // 9. Notifier si escalade
  if (response.escalate) {
    await notifyEscalation({ org, contactEmail, contactName, conversationId, reason: response.escalation_reason });
  }

  // 10. Log event
  await supabase.from("events").insert({
    org_id: orgId,
    type: "agent.message",
    source: agentId,
    data: {
      conversation_id: conversationId,
      intent: response.intent,
      sentiment: response.sentiment,
      escalated: response.escalate,
    },
  });

  // 11. Update stats agent
  await supabase.rpc("increment_agent_stats", {
    p_agent_id: agentId,
    p_messages: 1,
  });

  return response;
}

// ============================================
// EXÉCUTER LES ACTIONS SUGGÉRÉES PAR L'AGENT
// ============================================
async function executeActions(actions, orgId, agentId, conversationId) {
  if (!actions?.length) return;

  for (const action of actions) {
    try {
      switch (action.type) {
        case "create_task":
          await supabase.from("tasks").insert({
            org_id: orgId,
            title: action.title,
            priority: action.priority || "medium",
            status: "todo",
            assigned_by_agent: agentId,
            auto_generated: true,
            generation_context: `Généré par agent communication — conversation ${conversationId}`,
            due_date: action.due_date || null,
          });
          break;

        case "create_lead":
          await supabase.from("leads").insert({
            org_id: orgId,
            agent_id: agentId,
            email: action.email,
            full_name: action.name,
            company: action.company,
            source: "agent_communication",
            stage: "new",
            score: 20,
          });
          break;

        case "schedule_callback":
          const dueDate = new Date();
          dueDate.setHours(dueDate.getHours() + (action.delay_hours || 24));
          await supabase.from("tasks").insert({
            org_id: orgId,
            title: `Rappeler le client — conversation ${conversationId}`,
            priority: "high",
            status: "todo",
            assigned_by_agent: agentId,
            auto_generated: true,
            due_date: dueDate.toISOString(),
          });
          break;
      }
    } catch (err) {
      console.error(`Action ${action.type} failed:`, err);
    }
  }
}

// ============================================
// FORMAT EMAIL HTML
// ============================================
function formatEmailResponse(message, org, contactName) {
  return `
<!DOCTYPE html>
<html>
<body style="font-family: 'Helvetica Neue', sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="border-bottom: 3px solid #c9a84c; padding: 24px 0; margin-bottom: 24px;">
    <h2 style="margin: 0; color: #111;">${org.name}</h2>
  </div>
  <p>Bonjour ${contactName || ""},</p>
  <div style="background: #f8f7f4; border-left: 3px solid #c9a84c; padding: 16px 20px; margin: 20px 0;">
    ${message.split('\n').map(p => `<p style="margin: 8px 0;">${p}</p>`).join('')}
  </div>
  <p style="color: #888; font-size: 13px; margin-top: 32px;">
    Cordialement,<br>
    <strong>L'équipe ${org.name}</strong><br>
    <em style="color: #c9a84c;">Assisté par AutoFlow IA</em>
  </p>
</body>
</html>`;
}

// ============================================
// NOTIFICATION ESCALADE
// ============================================
async function notifyEscalation({ org, contactEmail, contactName, conversationId, reason }) {
  // Récupérer les admins de l'org
  const { data: admins } = await supabase
    .from("users")
    .select("email")
    .eq("org_id", org.id)
    .in("role", ["owner", "admin"]);

  if (!admins?.length) return;

  const adminEmails = admins.map((u) => u.email);
  const dashboardUrl = `https://app.autoflow.fr/conversations/${conversationId}`;

  await resend.emails.send({
    from: "AutoFlow <alerts@autoflow.fr>",
    to: adminEmails,
    subject: `🚨 Escalade requise — ${contactName || contactEmail}`,
    html: `
      <h3>Un client nécessite votre attention</h3>
      <p><strong>Contact :</strong> ${contactName || ""} (${contactEmail})</p>
      <p><strong>Raison :</strong> ${reason}</p>
      <a href="${dashboardUrl}" style="background:#c9a84c;color:#000;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:bold;">
        Voir la conversation →
      </a>
    `,
  });
}

// ============================================
// WEBHOOK HANDLER (Vercel API Route)
// ============================================
export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  // Vérifier le token webhook
  const token = req.headers["x-autoflow-token"];
  if (token !== process.env.WEBHOOK_SECRET) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  const { orgId, agentId, contactEmail, contactName, message, channel, conversationId } = req.body;

  if (!orgId || !agentId || !message) {
    return res.status(400).json({ error: "Missing required fields: orgId, agentId, message" });
  }

  try {
    // Créer ou récupérer la conversation
    let convId = conversationId;
    if (!convId) {
      const { data: conv } = await supabase
        .from("conversations")
        .insert({
          org_id: orgId,
          agent_id: agentId,
          contact_email: contactEmail,
          contact_name: contactName,
          channel: channel || "email",
          status: "open",
        })
        .select()
        .single();
      convId = conv.id;
    }

    const response = await handleIncomingMessage({
      orgId, agentId, conversationId: convId,
      contactEmail, contactName, message, channel,
    });

    return res.status(200).json({
      success: true,
      conversationId: convId,
      reply: response.message,
      escalated: response.escalate,
    });
  } catch (err) {
    console.error("Communication agent error:", err);
    return res.status(500).json({ error: "Internal server error" });
  }
}
