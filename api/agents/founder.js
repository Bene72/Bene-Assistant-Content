import Anthropic from "@anthropic-ai/sdk";

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const FOUNDER_SYSTEM_PROMPT = "Tu es l'assistant fondateur d'AutoFlow, l'agence SaaS de Benedetto.\nTa mission : aider Benedetto à développer son site, son offre, ses scripts de vente, ses automatisations, ses propositions commerciales et ses livrables clients.\n\nPositionnement AutoFlow :\n- AutoFlow vend des assistants IA et automatisations métiers pour indépendants, coachs, professions libérales et PME locales.\n- Offre de départ validée : Pro Coach à 490€/mois.\n- Premier client : Benoit, coach fitness, CrossFit et Hyrox à Nantes.\n- Promesse : gagner du temps, mieux suivre les clients, répondre plus vite aux prospects, structurer l'acquisition.\n\nTu dois toujours produire des réponses actionnables : pages de site, offres commerciales, scripts d'appel, emails, workflows Make, checklists de déploiement, idées de produits réplicables.\nStyle : direct, clair, business, sans jargon inutile, orienté exécution et vente.\nQuand Benedetto demande une stratégie, donne aussi les prochaines actions concrètes.\nQuand il demande du contenu, écris le contenu final prêt à utiliser.\nQuand il demande une offre, structure : cible, problème, promesse, livrables, prix, onboarding, objections, upsell.";

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });
  if (req.headers["x-autoflow-token"] !== process.env.WEBHOOK_SECRET) return res.status(401).json({ error: "Unauthorized" });

  const { message, context = "", mode = "strategy" } = req.body || {};
  if (!message) return res.status(400).json({ error: "Missing required field: message" });

  try {
    const completion = await anthropic.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1800,
      temperature: 0.35,
      system: FOUNDER_SYSTEM_PROMPT,
      messages: [{ role: "user", content: `Mode: ${mode}\n\nContexte disponible:\n${context}\n\nDemande:\n${message}` }],
    });

    return res.status(200).json({ success: true, mode, reply: completion.content[0]?.text || "" });
  } catch (error) {
    console.error("Founder agent error:", error);
    return res.status(500).json({ error: error.message });
  }
}
