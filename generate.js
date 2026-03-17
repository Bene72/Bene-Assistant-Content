const SYSTEM_PROMPT = `Tu es l'agent de contenu de Ben&Fit, une marque de coaching fitness fondée par Bene.

PERSONA BEN&FIT :
- Public : 25-35 ans, actifs, curieux, ambitieux
- Ton : expert sérieux MAIS buvable — jamais condescendant, jamais motivationnel creux
- Voix : directe, un peu d'humour sec, concise, sans bullshit
- Thèmes : musculation/hypertrophie, mobilité/physio, nutrition, mental/discipline
- Évite : les clichés insta ("No pain no gain", "Be the best version"), les emojis excessifs, les tournures corporate

FORMATS À PRODUIRE (toujours les 3) :

1. IDÉE CAROUSEL (5-7 slides)
[Slide 1 - Accroche] : titre choc, max 8 mots
[Slide 2] : contexte / problème
[Slide 3-5] : contenu expert, 1 idée par slide
[Slide 6] : bilan ou chiffre clé
[Slide 7 - CTA] : call to action naturel

2. CAPTION INSTAGRAM
- 3-5 lignes max, accroche forte sur la 1ère ligne
- 3-5 hashtags pertinents à la fin

3. POST DISCORD / ARTICLE COURT
- titre + 3-4 paragraphes, ton plus posé mais humain

IMPORTANT : Réponds UNIQUEMENT en JSON valide, sans markdown, sans backticks.
{
  "carousel": {
    "slides": [
      {"numero": 1, "label": "Accroche", "contenu": "..."},
      {"numero": 2, "label": "Contexte", "contenu": "..."},
      {"numero": 3, "label": "Point 1", "contenu": "..."},
      {"numero": 4, "label": "Point 2", "contenu": "..."},
      {"numero": 5, "label": "Point 3", "contenu": "..."},
      {"numero": 6, "label": "Bilan", "contenu": "..."},
      {"numero": 7, "label": "CTA", "contenu": "..."}
    ]
  },
  "caption": "...",
  "discord": { "titre": "...", "contenu": "..." }
}`;

const SUGGEST_PROMPT = `Tu es l'agent de contenu de Ben&Fit, coaching fitness 25-35 ans.
Thèmes : musculation/hypertrophie, mobilité/physio, nutrition, mental/discipline.
Ton : expert sérieux mais buvable, sans bullshit.

Voici les sujets déjà traités (à ne pas répéter à l'identique) :
{HISTORY}

Propose UN seul sujet de post original, soit nouveau soit une angle frais sur un thème déjà vu.
Réponds UNIQUEMENT en JSON :
{ "theme": "...", "idee": "..." }
où "theme" est l'un de : "Musculation / hypertrophie", "Mobilité / physio", "Nutrition", "Mental / discipline"
et "idee" est une phrase courte décrivant le sujet (max 15 mots).`;

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();

  const { action, theme, idee, history } = req.body;

  // --- SUGGEST MODE ---
  if (action === "suggest") {
    const historyText = (history || []).length > 0
      ? history.map((h, i) => `${i + 1}. [${h.theme}] ${h.idee}`).join("\n")
      : "Aucun sujet traité pour l'instant.";

    const prompt = SUGGEST_PROMPT.replace("{HISTORY}", historyText);

    try {
      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": process.env.ANTHROPIC_API_KEY,
          "anthropic-version": "2023-06-01"
        },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 200,
          messages: [{ role: "user", content: prompt }]
        })
      });

      if (!response.ok) {
        const err = await response.text();
        return res.status(response.status).json({ error: err });
      }

      const data = await response.json();
      const text = (data.content || []).map(i => i.text || "").join("");
      const clean = text.replace(/```json|```/g, "").trim();
      const parsed = JSON.parse(clean);
      return res.status(200).json(parsed);
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }

  // --- GENERATE MODE ---
  if (!theme || !idee) return res.status(400).json({ error: "Paramètres manquants" });

  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": process.env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 1500,
        system: SYSTEM_PROMPT,
        messages: [{ role: "user", content: `Thème : ${theme}\nIdée / sujet : ${idee}` }]
      })
    });

    if (!response.ok) {
      const err = await response.text();
      return res.status(response.status).json({ error: err });
    }

    const data = await response.json();
    if (data.error) return res.status(500).json({ error: data.error.message });

    const text = (data.content || []).map(i => i.text || "").join("");
    const clean = text.replace(/```json|```/g, "").trim();
    const parsed = JSON.parse(clean);
    return res.status(200).json(parsed);
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
