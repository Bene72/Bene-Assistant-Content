import { useState } from "react";

const THEMES = ["Musculation / hypertrophie", "Mobilité / physio", "Nutrition", "Mental / discipline"];
const THEME_COLORS = {
  "Musculation / hypertrophie": "#3B82F6",
  "Mobilité / physio": "#10B981",
  "Nutrition": "#F59E0B",
  "Mental / discipline": "#8B5CF6"
};

function CopyBox({ label, value }) {
  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ fontSize: 11, color: "#555", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 5 }}>
        {label} — appui long pour sélectionner
      </div>
      <textarea
        readOnly
        value={value}
        rows={Math.min(value.split("\n").length + 2, 12)}
        onFocus={e => e.target.select()}
        style={{ width: "100%", background: "#0d0d14", border: "1px solid #2a2a35", borderRadius: 9, padding: "11px 13px", color: "#D0D0E0", fontSize: 13, resize: "none", outline: "none", fontFamily: "DM Sans, sans-serif", lineHeight: 1.65 }}
      />
    </div>
  );
}

export default function BenFitAgent() {
  const [theme, setTheme] = useState("");
  const [idee, setIdee] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("carousel");
  const [history, setHistory] = useState([]);

  const suggest = async () => {
    setSuggesting(true);
    setError("");
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "suggest", history })
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "Erreur serveur");
      setTheme(data.theme);
      setIdee(data.idee);
    } catch (e) {
      setError(String(e.message));
    } finally {
      setSuggesting(false);
    }
  };

  const generate = async () => {
    if (!theme || !idee.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme, idee })
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || "Erreur serveur");
      setResult(data);
      setActiveTab("carousel");
      // Mémorise le sujet pour éviter les répétitions
      setHistory(prev => [...prev.slice(-19), { theme, idee }]);
    } catch (e) {
      setError(String(e.message));
    } finally {
      setLoading(false);
    }
  };

  const getCarouselText = () =>
    result?.carousel?.slides?.map(s => `[${s.label}]\n${s.contenu}`).join("\n\n") || "";
  const getCaptionText = () => result?.caption || "";
  const getDiscordText = () =>
    result ? `${result.discord.titre}\n\n${result.discord.contenu}` : "";

  return (
    <div style={{ minHeight: "100vh", background: "#0A0A0F", fontFamily: "'DM Sans', sans-serif", color: "#F0F0F0" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Syne:wght@700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        .pill { cursor: pointer; transition: all 0.15s; }
        .pill:hover { transform: scale(1.03); }
        .gen-btn { transition: all 0.2s; }
        .gen-btn:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(59,130,246,0.35); }
        .suggest-btn { transition: all 0.2s; }
        .suggest-btn:hover:not(:disabled) { background: #1e1e2e !important; border-color: #3B82F6 !important; color: #3B82F6 !important; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeUp { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
        .fade-up { animation: fadeUp 0.35s ease forwards; }
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.5; } }
        .pulsing { animation: pulse 1.2s ease-in-out infinite; }
      `}</style>

      {/* Header */}
      <div style={{ borderBottom: "1px solid #1a1a22", padding: "18px 24px", display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ width: 34, height: 34, borderRadius: 9, background: "linear-gradient(135deg,#3B82F6,#1D4ED8)", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 13 }}>B</div>
        <div>
          <div style={{ fontFamily: "Syne, sans-serif", fontWeight: 800, fontSize: 15 }}>Ben&Fit</div>
          <div style={{ fontSize: 11, color: "#555" }}>Agent Contenu</div>
        </div>
        {history.length > 0 && (
          <div style={{ marginLeft: "auto", fontSize: 11, color: "#444", background: "#1a1a22", padding: "4px 10px", borderRadius: 20 }}>
            {history.length} sujet{history.length > 1 ? "s" : ""} traité{history.length > 1 ? "s" : ""}
          </div>
        )}
      </div>

      <div style={{ maxWidth: 720, margin: "0 auto", padding: "28px 20px" }}>

        {/* Input */}
        <div style={{ background: "#111118", border: "1px solid #1e1e28", borderRadius: 14, padding: 22, marginBottom: 20 }}>

          {/* Suggest button */}
          <button
            className="suggest-btn"
            onClick={suggest}
            disabled={suggesting || loading}
            style={{ width: "100%", padding: "11px", borderRadius: 9, border: "1px solid #2a2a35", background: "transparent", color: "#888", fontSize: 13, fontWeight: 500, cursor: suggesting ? "not-allowed" : "pointer", marginBottom: 22, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
          >
            {suggesting ? (
              <>
                <span style={{ width: 12, height: 12, border: "2px solid #444", borderTopColor: "#888", borderRadius: "50%", display: "inline-block", animation: "spin 0.7s linear infinite" }} />
                <span className="pulsing">Recherche d'un sujet...</span>
              </>
            ) : (
              <>🎲 Je ne sais pas quoi poster</>
            )}
          </button>

          <div style={{ fontSize: 12, color: "#666", marginBottom: 10, fontWeight: 700, letterSpacing: "0.5px" }}>THÈME</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 22 }}>
            {THEMES.map(t => (
              <button key={t} className="pill" onClick={() => setTheme(t === theme ? "" : t)}
                style={{ padding: "7px 13px", borderRadius: 20, border: `1px solid ${theme === t ? THEME_COLORS[t] : "#2a2a35"}`, background: theme === t ? `${THEME_COLORS[t]}20` : "transparent", color: theme === t ? THEME_COLORS[t] : "#777", fontSize: 13, fontWeight: theme === t ? 600 : 400 }}>
                {t}
              </button>
            ))}
          </div>

          <div style={{ fontSize: 12, color: "#666", marginBottom: 8, fontWeight: 700, letterSpacing: "0.5px" }}>IDÉE / SUJET</div>
          <textarea value={idee} onChange={e => setIdee(e.target.value)}
            placeholder="Ex : quoi manger la veille d'une course Hyrox..." rows={3}
            style={{ width: "100%", background: "#0d0d14", border: "1px solid #2a2a35", borderRadius: 9, padding: "11px 13px", color: "#F0F0F0", fontSize: 14, resize: "vertical", outline: "none", fontFamily: "DM Sans, sans-serif", lineHeight: 1.6 }} />

          <button className="gen-btn" onClick={generate} disabled={loading || !theme || !idee.trim()}
            style={{ marginTop: 14, width: "100%", padding: "13px", borderRadius: 9, border: "none", background: (loading || !theme || !idee.trim()) ? "#1e1e28" : "linear-gradient(135deg,#3B82F6,#1D4ED8)", color: (loading || !theme || !idee.trim()) ? "#444" : "#fff", fontSize: 14, fontWeight: 600, cursor: (loading || !theme || !idee.trim()) ? "not-allowed" : "pointer" }}>
            {loading
              ? <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                  <span style={{ width: 13, height: 13, border: "2px solid #555", borderTopColor: "#aaa", borderRadius: "50%", display: "inline-block", animation: "spin 0.7s linear infinite" }} />
                  Génération en cours...
                </span>
              : "Générer le contenu →"}
          </button>
        </div>

        {error && (
          <div style={{ background: "#1a0a0a", border: "1px solid #3a1515", borderRadius: 9, padding: "12px 14px", marginBottom: 18 }}>
            <div style={{ color: "#f87171", fontSize: 12, fontWeight: 700, marginBottom: 3 }}>Erreur</div>
            <div style={{ color: "#f87171", fontSize: 11, opacity: 0.8, wordBreak: "break-all" }}>{error}</div>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="fade-up">
            <div style={{ display: "flex", gap: 4, marginBottom: 16, background: "#111118", border: "1px solid #1e1e28", borderRadius: 11, padding: 4 }}>
              {[{ key: "carousel", label: "🎠 Carousel" }, { key: "caption", label: "📸 Caption" }, { key: "discord", label: "💬 Discord" }].map(tab => (
                <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                  style={{ flex: 1, padding: "9px 6px", borderRadius: 7, border: "none", background: activeTab === tab.key ? "#1e1e2e" : "transparent", color: activeTab === tab.key ? "#F0F0F0" : "#555", fontSize: 13, fontWeight: activeTab === tab.key ? 600 : 400, cursor: "pointer" }}>
                  {tab.label}
                </button>
              ))}
            </div>

            {activeTab === "carousel" && (
              <div style={{ background: "#111118", border: "1px solid #1e1e28", borderRadius: 11, padding: 18 }}>
                {result.carousel.slides.map((slide, i) => (
                  <div key={i} style={{ display: "flex", gap: 12, marginBottom: 12 }}>
                    <div style={{ minWidth: 26, height: 26, borderRadius: 6, background: i === 0 ? "#3B82F620" : "#1a1a22", border: `1px solid ${i === 0 ? "#3B82F6" : "#2a2a35"}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: i === 0 ? "#3B82F6" : "#444", flexShrink: 0 }}>{i + 1}</div>
                    <div>
                      <div style={{ fontSize: 10, color: "#444", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 2 }}>{slide.label}</div>
                      <div style={{ fontSize: 13, color: "#CCC", lineHeight: 1.55 }}>{slide.contenu}</div>
                    </div>
                  </div>
                ))}
                <CopyBox label="Copier le carousel" value={getCarouselText()} />
              </div>
            )}

            {activeTab === "caption" && (
              <div style={{ background: "#111118", border: "1px solid #1e1e28", borderRadius: 11, padding: 18 }}>
                <div style={{ fontSize: 14, color: "#CCC", lineHeight: 1.8, whiteSpace: "pre-wrap" }}>{result.caption}</div>
                <CopyBox label="Copier la caption" value={getCaptionText()} />
              </div>
            )}

            {activeTab === "discord" && (
              <div style={{ background: "#111118", border: "1px solid #1e1e28", borderRadius: 11, padding: 18 }}>
                <div style={{ fontSize: 15, fontFamily: "Syne, sans-serif", fontWeight: 700, color: "#F0F0F0", marginBottom: 10 }}>{result.discord.titre}</div>
                <div style={{ fontSize: 13, color: "#BBB", lineHeight: 1.85, whiteSpace: "pre-wrap" }}>{result.discord.contenu}</div>
                <CopyBox label="Copier l'article" value={getDiscordText()} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
