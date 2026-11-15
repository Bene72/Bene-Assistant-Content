"""Lecture de pages web (la recherche web est assurée côté Anthropic)."""
import html
import re

import httpx

from . import tool

UA = "Mozilla/5.0 (BenFit-Agent)"


def _to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg|head).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</h\d>", "\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
    return re.sub(r"\n\s*\n+", "\n\n", raw).strip()


@tool("fetch_page", "Télécharge une page web et renvoie son texte lisible.",
      {"url": {"type": "string"}}, ["url"])
async def fetch_page(ctx, url: str):
    async with httpx.AsyncClient(follow_redirects=True, timeout=20, headers={"User-Agent": UA}) as c:
        r = await c.get(url)
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    text = _to_text(r.text) if "html" in ctype else r.text
    return text[:20_000]
