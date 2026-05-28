// ============================================
// AGENT RÉALISATION — AutoFlow
// agents/realisation.js
// ============================================
// Gère : création projets, décomposition tâches, suivi, alertes retard

import Anthropic from "@anthropic-ai/sdk";
import { createClient } from "@supabase/supabase-js";
import { Resend } from "resend";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const resend = new Resend(process.env.RESEND_API_KEY);
const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_KEY);

// ============================================
// SYSTEM PROMPT — Agent Réalisation
// ============================================
const REALISATION_SYSTEM_PROMPT = "Tu es l'agent de suivi opérationnel de Benoit, coach fitness/CrossFit/Hyrox.\nTu l'aides à organiser son activité : suivi des clients, création de programmes, gestion de son planning.\n\n## CONTEXTE\n- Benoit gère environ 15-20 clients actifs\n- Mix : séances en présentiel + clients en ligne (plans + appels hebdo)\n- Ses outils : Google Calendar, Google Sheets (suivi clients), Gmail\n- Ses galères : oublier de relancer, pas de process clair pour les nouveaux, admin chronophage\n\n## TES MISSIONS\n\n### Suivi clients\n- Créer une tâche de check-in pour chaque client après sa 3ème séance\n- Alerter si un client n'a pas eu de séance depuis 10 jours\n- Rappeler au coach d'envoyer le bilan mensuel le dernier lundi du mois\n\n### Programmes d'entraînement\nQuand on te demande de créer un programme, génère un plan structuré avec :\n- Phase 1 (sem 1-2) : adaptation / évaluation\n- Phase 2 (sem 3-6) : progression principale  \n- Phase 3 (sem 7-8) : pic / test\nFormat : semaine par semaine, jour par jour, exercices + séries + reps + RPE\n\n### Planning hebdo du coach\nChaque lundi matin, générer un récap :\n- Clients à séance cette semaine\n- Tâches en retard\n- Leads à relancer\n- Bilan revenus semaine précédente\n\n## GABARITS DE TÂCHES AUTO-GÉNÉRÉES\n\nNouveau client signé :\n→ \"Créer fiche client [Nom]\"\n→ \"Envoyer questionnaire initial (objectifs, historique, dispo)\"\n→ \"Planifier séance bilan J+3\"\n→ \"Créer programme semaines 1-2\"\n\nClient inactif 10j :\n→ \"Relancer [Nom] — inactif depuis X jours\"\n\nFin de pack :\n→ \"Proposer renouvellement à [Nom] — pack expire dans 1 semaine\"\n\n## FORMAT DE RÉPONSE (JSON strict)\n{\n  \"tasks\": [\n    {\n      \"title\": \"...\",\n      \"description\": \"...\",\n      \"priority\": \"urgent|high|medium|low\",\n      \"due_date\": \"2026-05-28T10:00:00Z\",\n      \"phase\": \"setup|execution|review|delivery\",\n      \"estimated_hours\": 0.5\n    }\n  ],\n  \"program\": null,\n  \"weekly_summary\": null,\n  \"alerts\": []\n}";

// ============================================
// CRÉER UN PROJET AUTOMATIQUEMENT
// ============================================
export async function createProjectFromBrief({ orgId, agentId, brief, leadId = null }) {
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();

  const systemPrompt = REALISATION_SYSTEM_PROMPT.replace("{org_name}", org.name);

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 3000,
    system: systemPrompt,
    messages: [{
      role: "user",
      content: `Crée un plan de projet complet pour ce brief :

${brief}

Décompose en maximum 20 tâches actionnables avec estimations réalistes.
Organise en phases logiques. Identifie les risques principaux.`
    }],
  });

  const rawText = completion.content[0].text;
  const jsonMatch = rawText.match(/\{[\s\S]*\}/);
  const plan = JSON.parse(jsonMatch[0]);

  // Calculer les dates
  const startDate = new Date();
  const dueDate = new Date();
  dueDate.setDate(dueDate.getDate() + plan.project.estimated_days);

  // Créer le projet
  const { data: project } = await supabase.from("projects").insert({
    org_id: orgId,
    lead_id: leadId,
    name: plan.project.name,
    description: plan.project.description,
    status: "active",
    priority: "high",
    start_date: startDate.toISOString().split("T")[0],
    due_date: dueDate.toISOString().split("T")[0],
    budget_euros: plan.project.budget_euros,
    tasks_total: plan.tasks.length,
  }).select().single();

  // Créer toutes les tâches
  const tasksToInsert = plan.tasks.map((task, idx) => ({
    project_id: project.id,
    org_id: orgId,
    title: task.title,
    description: `${task.description}\n\n**Critères d'acceptation:**\n${task.acceptance_criteria?.join("\n- ")}`,
    status: "todo",
    priority: task.priority,
    estimated_hours: task.estimated_hours,
    assigned_by_agent: agentId,
    auto_generated: true,
    generation_context: `Phase: ${task.phase} | Rôle: ${task.assignee_role}`,
    due_date: computeTaskDueDate(startDate, task, plan.tasks, idx),
  }));

  const { data: tasks } = await supabase.from("tasks").insert(tasksToInsert).select();

  // Notifier par email l'équipe
  await notifyProjectCreated({ org, project, plan, tasksCount: tasks.length });

  // Log event
  await supabase.from("events").insert({
    org_id: orgId,
    type: "project.created",
    source: agentId,
    data: {
      project_id: project.id,
      tasks_created: tasks.length,
      estimated_days: plan.project.estimated_days,
    },
  });

  return { project, tasks, plan };
}

// ============================================
// MISE À JOUR INTELLIGENTE DU STATUT
// ============================================
export async function updateTaskStatus({ taskId, orgId, agentId, newStatus, context = "" }) {
  const { data: task } = await supabase
    .from("tasks")
    .select("*, projects(*)")
    .eq("id", taskId)
    .single();

  const oldStatus = task.status;

  // Mettre à jour la tâche
  await supabase.from("tasks").update({
    status: newStatus,
    completed_at: newStatus === "done" ? new Date().toISOString() : null,
  }).eq("id", taskId);

  // Recalculer la progression du projet
  if (task.project_id) {
    const { data: allTasks } = await supabase
      .from("tasks")
      .select("status")
      .eq("project_id", task.project_id);

    const total = allTasks.length;
    const done = allTasks.filter(t => t.status === "done").length;
    const progress = Math.round((done / total) * 100);

    await supabase.from("projects").update({
      tasks_done: done,
      progress,
      status: progress === 100 ? "completed" : "active",
      completed_at: progress === 100 ? new Date().toISOString() : null,
    }).eq("id", task.project_id);

    // Si projet terminé, notifier
    if (progress === 100) {
      await notifyProjectCompleted({ orgId, project: task.projects });
    }
  }

  // Analyser les blocages si status = "blocked"
  if (newStatus === "blocked") {
    await analyzeBlockage({ task, context, orgId, agentId });
  }

  return { updated: true, oldStatus, newStatus };
}

// ============================================
// ANALYSE D'UN BLOCAGE
// ============================================
async function analyzeBlockage({ task, context, orgId, agentId }) {
  const { data: org } = await supabase.from("organisations").select("name").eq("id", orgId).single();

  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 600,
    system: `Tu es chef de projet. Analyse ce blocage et propose 3 solutions concrètes. Réponse JSON.`,
    messages: [{
      role: "user",
      content: `Tâche bloquée : "${task.title}"
Description : ${task.description}
Contexte du blocage : ${context || "Non précisé"}

Réponds JSON : {
  "root_cause": "...",
  "solutions": [
    {"action": "...", "owner": "...", "timeline": "..."}
  ],
  "escalation_needed": false,
  "unblock_tasks": ["nouvelle tâche créée pour débloquer"]
}`
    }],
  });

  const rawText = completion.content[0].text;
  const jsonMatch = rawText.match(/\{[\s\S]*\}/);
  if (!jsonMatch) return;

  const analysis = JSON.parse(jsonMatch[0]);

  // Créer les tâches de déblocage
  if (analysis.unblock_tasks?.length) {
    await supabase.from("tasks").insert(
      analysis.unblock_tasks.map(title => ({
        project_id: task.project_id,
        org_id: orgId,
        title,
        priority: "urgent",
        status: "todo",
        assigned_by_agent: agentId,
        auto_generated: true,
        generation_context: `Déblocage auto pour: ${task.title}`,
      }))
    );
  }

  // Notifier l'équipe
  const { data: admins } = await supabase
    .from("users")
    .select("email")
    .eq("org_id", orgId)
    .in("role", ["owner", "admin"]);

  if (admins?.length) {
    await resend.emails.send({
      from: "AutoFlow <alerts@autoflow.fr>",
      to: admins.map(a => a.email),
      subject: `🔴 Blocage détecté — ${task.title}`,
      html: `
        <h3>Tâche bloquée dans ${org.name}</h3>
        <p><strong>Tâche :</strong> ${task.title}</p>
        <p><strong>Cause probable :</strong> ${analysis.root_cause}</p>
        <h4>Solutions proposées :</h4>
        <ol>
          ${analysis.solutions.map(s => `<li><strong>${s.action}</strong> — ${s.owner} (${s.timeline})</li>`).join("")}
        </ol>
        ${analysis.escalation_needed ? '<p style="color:red;font-weight:bold;">⚠️ Escalade recommandée</p>' : ""}
      `,
    });
  }

  return analysis;
}

// ============================================
// RAPPORT HEBDOMADAIRE AUTOMATIQUE
// ============================================
export async function generateWeeklyReport({ orgId, agentId }) {
  // Récupérer les données de la semaine
  const weekAgo = new Date();
  weekAgo.setDate(weekAgo.getDate() - 7);

  const [projectsData, tasksData, eventsData] = await Promise.all([
    supabase.from("projects").select("*").eq("org_id", orgId).eq("status", "active"),
    supabase.from("tasks").select("*").eq("org_id", orgId).gte("updated_at", weekAgo.toISOString()),
    supabase.from("events").select("*").eq("org_id", orgId).gte("created_at", weekAgo.toISOString()),
  ]);

  const projects = projectsData.data || [];
  const tasks = tasksData.data || [];
  const events = eventsData.data || [];

  const tasksDone = tasks.filter(t => t.status === "done").length;
  const tasksBlocked = tasks.filter(t => t.status === "blocked").length;
  const tasksInProgress = tasks.filter(t => t.status === "in_progress").length;

  // Générer le rapport avec Claude
  const completion = await anthropic.messages.create({
    model: "claude-sonnet-4-20250514",
    max_tokens: 1500,
    system: `Tu génères des rapports d'avancement projet clairs, concis et actionnables. Format HTML pour email.`,
    messages: [{
      role: "user",
      content: `Génère un rapport hebdomadaire :

Projets actifs : ${projects.length}
Tâches complétées cette semaine : ${tasksDone}
Tâches en cours : ${tasksInProgress}
Tâches bloquées : ${tasksBlocked}
Événements système : ${events.length}

Projets détail :
${projects.map(p => `- ${p.name}: ${p.progress}% (${p.tasks_done}/${p.tasks_total} tâches) — deadline: ${p.due_date}`).join("\n")}

Génère un rapport HTML professionnel avec :
1. Résumé exécutif (3 phrases)
2. Avancement par projet (avec barre de progression visuelle)
3. Points de vigilance
4. Actions prioritaires de la semaine prochaine`
    }],
  });

  const reportHtml = completion.content[0].text;

  // Envoyer aux admins
  const { data: org } = await supabase.from("organisations").select("*").eq("id", orgId).single();
  const { data: admins } = await supabase.from("users").select("email, full_name").eq("org_id", orgId).in("role", ["owner", "admin"]);

  if (admins?.length) {
    await resend.emails.send({
      from: `AutoFlow <reports@autoflow.fr>`,
      to: admins.map(a => a.email),
      subject: `📊 Rapport hebdomadaire — ${org.name} — Semaine du ${weekAgo.toLocaleDateString("fr-FR")}`,
      html: reportHtml,
    });
  }

  return { reportHtml, stats: { tasksDone, tasksBlocked, tasksInProgress, projects: projects.length } };
}

// ============================================
// SURVEILLANCE RETARDS (cron job)
// ============================================
export async function checkOverdueTasks({ orgId }) {
  const now = new Date().toISOString();

  const { data: overdueTasks } = await supabase
    .from("tasks")
    .select("*, projects(name)")
    .eq("org_id", orgId)
    .not("status", "in", '("done","cancelled")')
    .lt("due_date", now)
    .not("due_date", "is", null);

  if (!overdueTasks?.length) return { overdue: 0 };

  // Grouper par projet
  const byProject = overdueTasks.reduce((acc, task) => {
    const pName = task.projects?.name || "Sans projet";
    if (!acc[pName]) acc[pName] = [];
    acc[pName].push(task);
    return acc;
  }, {});

  const { data: org } = await supabase.from("organisations").select("name").eq("id", orgId).single();
  const { data: admins } = await supabase.from("users").select("email").eq("org_id", orgId).in("role", ["owner", "admin"]);

  if (admins?.length) {
    await resend.emails.send({
      from: "AutoFlow <alerts@autoflow.fr>",
      to: admins.map(a => a.email),
      subject: `⚠️ ${overdueTasks.length} tâches en retard — ${org.name}`,
      html: `
        <h3>${overdueTasks.length} tâches en retard dans ${org.name}</h3>
        ${Object.entries(byProject).map(([project, tasks]) => `
          <h4>${project} (${tasks.length} retards)</h4>
          <ul>
            ${tasks.map(t => `<li><strong>${t.title}</strong> — échéance : ${new Date(t.due_date).toLocaleDateString("fr-FR")}</li>`).join("")}
          </ul>
        `).join("")}
        <a href="https://app.autoflow.fr/tasks?filter=overdue" style="background:#c9a84c;color:#000;padding:10px 20px;text-decoration:none;border-radius:4px;">Voir les tâches →</a>
      `,
    });
  }

  return { overdue: overdueTasks.length, byProject };
}

// ============================================
// HELPERS
// ============================================
function computeTaskDueDate(startDate, task, allTasks, idx) {
  const phaseOffsets = { setup: 0.1, execution: 0.4, review: 0.75, delivery: 0.9 };
  const offset = phaseOffsets[task.phase] || 0.5;
  const projectDays = 30; // default
  const d = new Date(startDate);
  d.setDate(d.getDate() + Math.round(projectDays * offset));
  return d.toISOString();
}

async function notifyProjectCreated({ org, project, plan, tasksCount }) {
  const { data: admins } = await supabase.from("users").select("email").eq("org_id", org.id).in("role", ["owner", "admin"]);
  if (!admins?.length) return;

  await resend.emails.send({
    from: "AutoFlow <projects@autoflow.fr>",
    to: admins.map(a => a.email),
    subject: `✅ Nouveau projet créé — ${project.name}`,
    html: `
      <h3>Projet "${project.name}" créé automatiquement</h3>
      <p><strong>${tasksCount} tâches</strong> générées par l'agent IA</p>
      <p>Durée estimée : ${plan.project.estimated_days} jours</p>
      <p>Budget estimé : ${plan.project.budget_euros?.toLocaleString("fr-FR")} €</p>
      <p><strong>Risques identifiés :</strong></p>
      <ul>${plan.project.risks?.map(r => `<li>${r}</li>`).join("")}</ul>
      <a href="https://app.autoflow.fr/projects/${project.id}" style="background:#c9a84c;color:#000;padding:10px 20px;text-decoration:none;border-radius:4px;">Voir le projet →</a>
    `,
  });
}

async function notifyProjectCompleted({ orgId, project }) {
  const { data: org } = await supabase.from("organisations").select("name").eq("id", orgId).single();
  const { data: admins } = await supabase.from("users").select("email").eq("org_id", orgId).in("role", ["owner", "admin"]);
  if (!admins?.length) return;

  await resend.emails.send({
    from: "AutoFlow <projects@autoflow.fr>",
    to: admins.map(a => a.email),
    subject: `🎉 Projet terminé — ${project.name}`,
    html: `<h3>Félicitations ! Le projet "${project.name}" est terminé à 100%.</h3>`,
  });
}

// ============================================
// WEBHOOK HANDLER
// ============================================
export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();

  const token = req.headers["x-autoflow-token"];
  if (token !== process.env.WEBHOOK_SECRET) return res.status(401).end();

  const { action, orgId, agentId, brief, leadId, taskId, newStatus, context } = req.body;

  try {
    let result;
    switch (action) {
      case "create_project":
        result = await createProjectFromBrief({ orgId, agentId, brief, leadId });
        break;
      case "update_task":
        result = await updateTaskStatus({ taskId, orgId, agentId, newStatus, context });
        break;
      case "weekly_report":
        result = await generateWeeklyReport({ orgId, agentId });
        break;
      case "check_overdue":
        result = await checkOverdueTasks({ orgId });
        break;
      default:
        return res.status(400).json({ error: "Unknown action" });
    }
    return res.status(200).json({ success: true, data: result });
  } catch (err) {
    console.error("Realisation agent error:", err);
    return res.status(500).json({ error: err.message });
  }
}
