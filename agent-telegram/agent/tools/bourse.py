"""Bourse & PEA : suivi du portefeuille, cours des marchés, stratégie de Bene.

Cours : API publique de Yahoo Finance (gratuite, sans clé, différé ~15 min).
Le portefeuille et la stratégie restent dans la base locale (data/agent.db).
Ce module ne passe JAMAIS d'ordre : il informe, Bene décide.
"""
import asyncio
import datetime as dt
import time

import httpx

from .. import storage
from . import tool

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
SEARCH = "https://query1.finance.yahoo.com/v1/finance/search"

# Repères du marché pour le brief (symbole Yahoo → nom lisible)
MARKETS = {
    "^FCHI": "CAC 40",
    "^STOXX": "Stoxx Europe 600",
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "URTH": "MSCI World (ETF iShares, en $)",
    "EURUSD=X": "Euro / Dollar",
    "GC=F": "Or ($/once)",
    "BZ=F": "Pétrole Brent ($)",
    "BTC-EUR": "Bitcoin (€)",
}

_cache: dict[str, tuple[float, dict]] = {}
CACHE_S = 300


def _init_table():
    with storage.db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS portfolio (
            symbol TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            quantity REAL NOT NULL DEFAULT 0,
            cost REAL,
            target REAL,
            account TEXT NOT NULL DEFAULT 'PEA',
            updated REAL NOT NULL)""")


def holdings() -> list[dict]:
    _init_table()
    with storage.db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM portfolio ORDER BY account, symbol")]


async def quote(symbol: str) -> dict:
    """Dernier cours + variations jour / 5 jours / 1 mois / début d'année."""
    symbol = symbol.strip().upper()
    hit = _cache.get(symbol)
    if hit and time.time() - hit[0] < CACHE_S:
        return hit[1]
    async with httpx.AsyncClient(timeout=15, headers=UA) as cl:
        r = await cl.get(CHART.format(symbol), params={"range": "ytd" if dt.date.today().month > 1 else "3mo",
                                                       "interval": "1d"})
    r.raise_for_status()
    res = (r.json().get("chart") or {}).get("result")
    if not res:
        raise ValueError(f"symbole inconnu : {symbol}")
    res = res[0]
    meta = res["meta"]
    q0 = (res.get("indicators", {}).get("quote") or [{}])[0]
    bars = [(t, c) for t, c in zip(res.get("timestamp") or [], q0.get("close") or []) if c is not None]
    closes = [c for _, c in bars]
    price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
    if price is None:
        raise ValueError(f"pas de cours pour {symbol}")
    # La dernière barre est-elle celle du jour du dernier cours ? Alors la veille est l'avant-dernière.
    last_day = dt.date.fromtimestamp(meta.get("regularMarketTime") or 0)
    if bars and dt.date.fromtimestamp(bars[-1][0]) == last_day:
        prev = closes[-2] if len(closes) >= 2 else meta.get("chartPreviousClose")
    else:
        prev = closes[-1] if closes else meta.get("chartPreviousClose")

    def pct(ref):
        return round((price / ref - 1) * 100, 2) if ref else None

    out = {
        "symbole": symbol,
        "nom": meta.get("longName") or meta.get("shortName") or symbol,
        "devise": meta.get("currency"),
        "cours": round(price, 4),
        "var_jour_pct": pct(prev),
        "var_5j_pct": pct(closes[-6]) if len(closes) >= 6 else None,
        "var_1mois_pct": pct(closes[-22]) if len(closes) >= 22 else None,
        "var_annee_pct": pct(closes[0]) if closes and dt.date.today().month > 1 else None,
        "plus_haut_52s": meta.get("fiftyTwoWeekHigh"),
        "heure_cours": dt.datetime.fromtimestamp(meta.get("regularMarketTime", 0)).strftime("%d/%m %H:%M"),
    }
    _cache[symbol] = (time.time(), out)
    return out


async def _quotes(symbols: list[str]) -> dict[str, dict | str]:
    res = await asyncio.gather(*(quote(s) for s in symbols), return_exceptions=True)
    return {s: (r if isinstance(r, dict) else f"indisponible ({type(r).__name__})") for s, r in zip(symbols, res)}


async def _to_eur(currency: str | None) -> float:
    if not currency or currency.upper() == "EUR":
        return 1.0
    if currency == "GBp":  # pence
        return (await quote("GBPEUR=X"))["cours"] / 100
    return (await quote(f"{currency.upper()}EUR=X"))["cours"]


async def portfolio_snapshot(amounts: bool = True) -> dict:
    """Valeur du portefeuille, perf, poids réel vs cible. amounts=False : seulement des %."""
    rows = holdings()
    if not rows:
        return {"vide": True, "info": "Aucune ligne enregistrée. Dis par ex. « ajoute à mon PEA 10 parts "
                                      "de CW8 à 450 € de prix de revient, cible 60 % »."}
    quotes = await _quotes([r["symbol"] for r in rows])
    lines, total, invested, day_gain = [], 0.0, 0.0, 0.0
    for r in rows:
        q = quotes[r["symbol"]]
        line = {"symbole": r["symbol"], "nom": r["name"], "compte": r["account"], "cible_pct": r["target"]}
        if isinstance(q, str):
            line["cours"] = q
            lines.append(line)
            continue
        fx = await _to_eur(q["devise"])
        value = q["cours"] * fx * r["quantity"]
        total += value
        if r["cost"]:
            invested += r["cost"] * r["quantity"]
            line["plus_value_pct"] = round((q["cours"] * fx / r["cost"] - 1) * 100, 2)
        if q["var_jour_pct"] is not None:
            day_gain += value - value / (1 + q["var_jour_pct"] / 100)
        line.update({k: q[k] for k in ("cours", "devise", "var_jour_pct", "var_1mois_pct", "var_annee_pct")})
        line["_valeur"] = value
        if amounts:
            line.update({"quantite": r["quantity"], "valeur_eur": round(value, 2)})
        lines.append(line)
    for line in lines:
        v = line.pop("_valeur", None)
        if v is not None and total:
            line["poids_reel_pct"] = round(v / total * 100, 1)
            if line["cible_pct"] is not None:
                line["ecart_cible_pts"] = round(line["poids_reel_pct"] - line["cible_pct"], 1)
    out: dict = {"lignes": lines,
                 "var_jour_pct": round(day_gain / (total - day_gain) * 100, 2) if total - day_gain else None}
    if invested:
        out["plus_value_totale_pct"] = round((total / invested - 1) * 100, 2)
    if amounts:
        out.update({"valeur_totale_eur": round(total, 2), "gain_jour_eur": round(day_gain, 2)})
        if invested:
            out.update({"investi_eur": round(invested, 2), "plus_value_eur": round(total - invested, 2)})
    return out


async def brief_data(oral: bool = False) -> dict:
    """Bloc « bourse » du brief du matin. En vocal : pas de montants en euros."""
    markets = await _quotes(list(MARKETS))
    data = {
        "marches": {MARKETS[s]: ({k: q[k] for k in ("cours", "var_jour_pct", "var_5j_pct", "var_annee_pct")}
                                 if isinstance(q, dict) else q) for s, q in markets.items()},
        "portefeuille": await portfolio_snapshot(amounts=not oral),
        "strategie": storage.get_meta("pea_strategie") or "non renseignée",
    }
    if dt.date.today().weekday() == 0:
        data["note"] = "lundi : les variations « jour » sont celles de vendredi"
    return data


# --- Outils pour Claude ---------------------------------------------------------------

@tool("market_overview", "Situation des marchés : CAC 40, Stoxx 600, S&P 500, Nasdaq, MSCI World, euro/dollar, "
      "or, pétrole, bitcoin (cours et variations jour / 5 jours / année).")
async def market_overview(ctx):
    return (await brief_data())["marches"]


@tool("market_quote", "Cours et variations d'un titre, ETF ou indice. Symbole au format Yahoo Finance "
      "(Euronext Paris : suffixe .PA, ex. CW8.PA, ESE.PA, MC.PA ; indices : ^FCHI). Utilise market_search "
      "si tu n'as que le nom ou l'ISIN.", {"symbole": {"type": "string"}}, ["symbole"])
async def market_quote(ctx, symbole: str):
    return await quote(symbole)


@tool("market_search", "Trouve le symbole Yahoo Finance d'un ETF, d'une action ou d'un indice à partir d'un "
      "nom, d'un code mnémonique ou d'un ISIN.", {"recherche": {"type": "string"}}, ["recherche"])
async def market_search(ctx, recherche: str):
    async with httpx.AsyncClient(timeout=15, headers=UA) as cl:
        r = await cl.get(SEARCH, params={"q": recherche, "quotesCount": 8, "newsCount": 0, "lang": "fr-FR"})
    r.raise_for_status()
    return [{"symbole": q.get("symbol"), "nom": q.get("longname") or q.get("shortname"),
             "type": q.get("quoteType"), "place": q.get("exchDisp")} for q in r.json().get("quotes", [])]


@tool("portfolio_status", "État du portefeuille de Bene (PEA…) : valeur, plus-value, variation du jour, poids "
      "réel de chaque ligne et écart à sa cible.")
async def portfolio_status(ctx):
    return await portfolio_snapshot()


@tool("portfolio_set", "Ajoute ou met à jour une ligne du portefeuille (à faire seulement quand Bene le "
      "demande). quantite = nombre total de parts détenues ; prix_revient = PRU en € par part ; "
      "cible_pct = part visée dans le portefeuille.",
      {"symbole": {"type": "string", "description": "symbole Yahoo, ex. CW8.PA"},
       "nom": {"type": "string"}, "quantite": {"type": "number"},
       "prix_revient": {"type": "number"}, "cible_pct": {"type": "number"},
       "compte": {"type": "string", "description": "PEA par défaut (ou CTO, assurance-vie…)"}},
      ["symbole"])
async def portfolio_set(ctx, symbole: str, nom: str | None = None, quantite: float | None = None,
                        prix_revient: float | None = None, cible_pct: float | None = None,
                        compte: str | None = None):
    symbole = symbole.strip().upper()
    q = await quote(symbole)  # vérifie que le symbole existe
    _init_table()
    with storage.db() as c:
        old = c.execute("SELECT * FROM portfolio WHERE symbol=?", (symbole,)).fetchone()
        old = dict(old) if old else {"name": q["nom"], "quantity": 0, "cost": None, "target": None, "account": "PEA"}
        row = (symbole, nom or old["name"], quantite if quantite is not None else old["quantity"],
               prix_revient if prix_revient is not None else old["cost"],
               cible_pct if cible_pct is not None else old["target"], compte or old["account"], time.time())
        c.execute("INSERT OR REPLACE INTO portfolio(symbol,name,quantity,cost,target,account,updated) "
                  "VALUES (?,?,?,?,?,?,?)", row)
    return {"ok": True, "ligne": dict(zip(("symbole", "nom", "quantite", "prix_revient", "cible_pct", "compte"), row)),
            "cours_actuel": q["cours"]}


@tool("portfolio_remove", "Retire une ligne du portefeuille (seulement si Bene le demande).",
      {"symbole": {"type": "string"}}, ["symbole"])
async def portfolio_remove(ctx, symbole: str):
    _init_table()
    with storage.db() as c:
        n = c.execute("DELETE FROM portfolio WHERE symbol=?", (symbole.strip().upper(),)).rowcount
    return {"ok": n > 0}


@tool("investment_strategy_get", "Relit la stratégie d'investissement de Bene (allocation cible, versements, "
      "horizon, règles qu'il s'est fixées). À lire avant toute piste de réflexion.")
async def investment_strategy_get(ctx):
    return storage.get_meta("pea_strategie") or "Aucune stratégie enregistrée."


@tool("investment_strategy_set", "Enregistre sa stratégie d'investissement (texte complet qui remplace "
      "l'ancien), seulement quand Bene la donne ou la modifie.", {"texte": {"type": "string"}}, ["texte"])
async def investment_strategy_set(ctx, texte: str):
    storage.set_meta("pea_strategie", texte.strip()[:6000])
    return {"ok": True}
