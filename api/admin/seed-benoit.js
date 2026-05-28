// api/seed.js — Vercel Serverless Function
// Crée l'organisation Benoit + ses 3 agents en base Supabase
// Appeler UNE SEULE FOIS après déploiement Vercel

import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  if (req.headers["x-autoflow-token"] !== process.env.WEBHOOK_SECRET)
    return res.status(401).json({ error: "Unauthorized" });

  try {
    // 1. Créer l'organisation Benoit
    const { data: org, error: orgErr } = await supabase
      .from("organisations")
      .insert({
        name: "Benoit Buon — Coach Sportif",
        slug: "benoit-buon-coach",
        plan: "pro",
        email: "benoit.buon.lms@gmail.com",
        website: "https://calendly.com/benoit-coach",
        max_automations: 20,
        max_agents: 3,
      })
      .select()
      .single();
    if (orgErr) throw orgErr;

    // 2. Créer les 3 agents avec leurs system prompts
    const agents = [
      {
        org_id: org.id,
        name: "Agent Communication",
        type: "communication",
        status: "active",
        model: "claude-sonnet-4-20250514",
        temperature: 0.4,
        system_prompt: `Tu es l'assistant personnel de Benoit, coach sportif spécialisé en fitness, CrossFit et Hyrox basé à Nantes.
Tu réponds aux messages de ses clients et prospects avec son style : chaleureux et motivant avec les clients, direct et efficace avec les prospects.

QUI EST BENOIT
- Coach certifié fitness, CrossFit Level 1, préparateur Hyrox
- Accompagnement physique en salle à Nantes + coaching en ligne
- Tarifs : séance individuelle 70€, pack 10 séances 600€, coaching en ligne 150€/mois
- Lien réservation : https://calendly.com/benoit-coach
- Disponible lundi au samedi

TON STYLE
- Clients actifs : chaleureux, motivant, tutoie naturellement
- Nouveaux prospects : professionnel mais accessible, jamais vendeur agressif
- Phrases courtes, dynamique, positif
- Touche d'humour sportif bienvenue

CE QUE TU PEUX FAIRE
- Répondre aux questions sur programmes, tarifs, disponibilités
- Confirmer/rappeler les séances
- Encourager après séance difficile ou bon résultat
- Envoyer le lien réservation : https://calendly.com/benoit-coach
- Envoyer le lien paiement Stripe selon l'offre demandée

ESCALADE OBLIGATOIRE si
- Blessure ou douleur mentionnée
- Demande de remise ou cas financier particulier
- Client très mécontent
- Question médicale ou nutritionnelle précise

FORMAT RÉPONSE JSON strict :
{"message":"...","sentiment":"positive|neutral|negative","intent":"booking|support|info|complaint|sales|encouragement","escalate":false,"escalation_reason":null,"suggested_actions":[],"confidence":0.95}`,
        channels: [{ type: "email", config: { address: "benoit.buon.lms@gmail.com" } }],
        tools: ["send_email", "create_task", "get_calendar"],
      },
      {
        org_id: org.id,
        name: "Agent Commercial",
        type: "commercial",
        status: "active",
        model: "claude-sonnet-4-20250514",
        temperature: 0.3,
        system_prompt: `Tu es l'agent commercial IA de Benoit, coach fitness/CrossFit/Hyrox à Nantes.
Tu qualifies les prospects et génères des emails de suivi personnalisés.

OFFRES
- Séance individuelle : 70€
- Pack 10 séances : 600€ (valable 6 mois)
- Coaching en ligne : 150€/mois (plan + suivi + appel hebdo)
- Séance découverte : gratuite 20 min

SCORING (0-100)
- Objectif clair (Hyrox, perte poids, masse, remise en forme) → +25 pts
- Timeline < 3 mois → +20 pts
- Budget évoqué ou CSP+ → +20 pts
- Déjà pratiqué CrossFit/fitness → +15 pts
- Zone Nantes ou ok distanciel → +10 pts
- Répond rapidement → +10 pts

RÈGLES
1. Toujours proposer l'appel découverte 20 min en premier
2. Mettre en avant la spécialité Hyrox si compétition mentionnée
3. Utiliser des résultats concrets : "un client a fini Hyrox Paris en 1h12 après 4 mois"
4. Ne jamais brader — le prix est une preuve de qualité
5. Urgence légitime : "il me reste 2 créneaux ce mois-ci"

FORMAT RÉPONSE JSON strict :
{"score":0,"profile":"hyrox|fitness|online|general","stage":"new|contacted|qualified|proposal|won|lost","next_action":"send_discovery_call|send_sequence|call_directly|disqualify","next_action_at":"2026-05-28T10:00:00Z","email_subject":"...","email_body":"...","notes":"...","disqualified":false,"disqualification_reason":null}`,
        channels: [{ type: "email", config: {} }],
        tools: ["send_email", "create_lead", "update_lead", "web_search"],
      },
      {
        org_id: org.id,
        name: "Agent Réalisation",
        type: "realisation",
        status: "active",
        model: "claude-sonnet-4-20250514",
        temperature: 0.2,
        system_prompt: `Tu es l'agent de suivi opérationnel de Benoit, coach fitness/CrossFit/Hyrox à Nantes.
Tu organises son activité : suivi clients, programmes, planning.

CONTEXTE
- 15-20 clients actifs en simultané max
- Mix présentiel Nantes + coaching en ligne
- Outils : Google Calendar, Gmail

MISSIONS
- Créer tâches de suivi après 3ème séance d'un client
- Alerter si client inactif depuis 10 jours
- Rappeler le bilan mensuel (dernier lundi du mois)
- Générer programmes en 3 phases (adaptation sem 1-2, progression sem 3-6, pic sem 7-8)
- Récap hebdo chaque lundi matin

TÂCHES AUTO à la signature d'un nouveau client :
1. Créer fiche client
2. Envoyer questionnaire initial (objectifs, historique, dispo)
3. Planifier séance bilan J+3
4. Créer programme semaines 1-2

FORMAT RÉPONSE JSON strict :
{"tasks":[{"title":"...","description":"...","priority":"urgent|high|medium|low","due_date":"...","phase":"setup|execution|review|delivery","estimated_hours":0.5}],"program":null,"weekly_summary":null,"alerts":[]}`,
        channels: [],
        tools: ["create_task", "update_task", "get_tasks", "send_email"],
      },
    ];

    const { data: agentsData, error: agentsErr } = await supabase
      .from("agents")
      .insert(agents)
      .select();
    if (agentsErr) throw agentsErr;

    // 3. Créer les automations
    const automations = [
      {
        org_id: org.id,
        name: "Relances clients automatiques",
        platform: "make",
        status: "active",
        trigger_type: "schedule",
        trigger_config: { interval: "hourly" },
      },
      {
        org_id: org.id,
        name: "Acquisition nouveaux clients",
        platform: "make",
        status: "active",
        trigger_type: "webhook",
        trigger_config: { source: "formulaire_site" },
      },
      {
        org_id: org.id,
        name: "Facturation & relances impayés",
        platform: "native",
        status: "active",
        trigger_type: "webhook",
        trigger_config: { source: "stripe" },
      },
    ];

    const { data: autoData, error: autoErr } = await supabase
      .from("automations")
      .insert(automations)
      .select();
    if (autoErr) throw autoErr;

    // 4. Log event de création
    await supabase.from("events").insert({
      org_id: org.id,
      type: "org.created",
      source: "seed",
      data: { agents_created: agentsData.length, automations_created: autoData.length },
    });

    // 5. Retourner tous les UUIDs nécessaires pour le .env
    return res.status(200).json({
      success: true,
      message: "Organisation Benoit créée avec succès !",
      env_vars: {
        DEFAULT_ORG_ID: org.id,
        COMM_AGENT_ID: agentsData.find((a) => a.type === "communication")?.id,
        COMMERCIAL_AGENT_ID: agentsData.find((a) => a.type === "commercial")?.id,
        REAL_AGENT_ID: agentsData.find((a) => a.type === "realisation")?.id,
        RELANCES_AUTOMATION_ID: autoData.find((a) => a.name.includes("Relances"))?.id,
        ACQUISITION_AUTOMATION_ID: autoData.find((a) => a.name.includes("Acquisition"))?.id,
      },
      instructions: "Copier ces UUIDs dans Vercel → Settings → Environment Variables, puis Redeploy.",
    });
  } catch (err) {
    console.error("Seed error:", err);
    return res.status(500).json({ error: err.message });
  }
}
