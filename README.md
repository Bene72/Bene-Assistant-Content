# Ben&Fit — Site officiel

Coach CrossFit & Hyrox · Benoît · Nantes

---

## 🚀 Déploiement sur Vercel (5 minutes)

### Méthode 1 — Via GitHub (recommandée)

1. **Crée un repo GitHub**
   - Va sur [github.com/new](https://github.com/new)
   - Nomme-le `benfit` (ou ce que tu veux)
   - Laisse tout par défaut, clique **Create repository**

2. **Pousse le projet**
   ```bash
   git init
   git add .
   git commit -m "🚀 Initial commit — Ben&Fit website"
   git branch -M main
   git remote add origin https://github.com/TON_USERNAME/benfit.git
   git push -u origin main
   ```

3. **Connecte Vercel**
   - Va sur [vercel.com](https://vercel.com) → **Add New Project**
   - Importe ton repo GitHub `benfit`
   - Vercel détecte automatiquement `vercel.json`
   - Clique **Deploy** ✅

4. **Ton site est en ligne** sur `benfit.vercel.app` (ou ton domaine custom)

---

### Méthode 2 — CLI Vercel (sans GitHub)

```bash
# Installe la CLI Vercel
npm install -g vercel

# Dans le dossier du projet
vercel

# Suis les étapes (login, nom du projet, etc.)
# Répondre "public" si demande le output directory
```

---

## 🌐 Domaine personnalisé (optionnel)

Dans le dashboard Vercel → ton projet → **Settings → Domains**
- Ajoute `benfit-nantes.fr` ou `coach-bene.fr` etc.
- Suis les instructions DNS (généralement un CNAME ou A record)

---

## 📁 Structure du projet

```
benfit/
├── public/
│   ├── index.html          ← Le site complet
│   └── images/
│       ├── BenAnd_Fit.png
│       ├── ChatGPT_Image_22_avr__2026__22_24_41.png
│       ├── DSC02698.jpg
│       ├── Le_Mans_Contest_wod1-254.jpg
│       └── LRSY_Throwdown_Crossfit_2k24__46_.jpg
├── vercel.json             ← Config Vercel (routing + cache)
├── package.json
└── .gitignore
```

---

## 🛠 Développement local

```bash
npm install
npm run dev
# → Ouvre http://localhost:3000
```

---

## ✏️ Modifier le contenu

Tout est dans `public/index.html` — cherche les sections :
- **Texte** : modifie directement le HTML
- **Images** : remplace les fichiers dans `public/images/` (garde les mêmes noms)
- **Couleurs** : modifie les variables CSS en haut du fichier (`:root { --accent: #e8c84a; ... }`)
- **Tarifs** : section `id="services"`
- **Contact** : section `id="contact"`

Après chaque modif → `git add . && git commit -m "update" && git push`
Vercel redéploie automatiquement en ~30 secondes ⚡
