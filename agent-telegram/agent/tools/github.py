"""Dev : accès aux repos GitHub. Les modifications passent toujours par une Pull Request."""
import base64
import re
import time

import httpx

from .. import config, confirm
from . import tool

API = "https://api.github.com"
_enabled = lambda: bool(config.GITHUB_TOKEN)  # noqa: E731


_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")


def _repo(repo: str) -> str:
    full = repo if "/" in repo else f"{config.GITHUB_OWNER}/{repo}"
    parts = full.split("/")
    if len(parts) != 2 or not all(_NAME.match(x) and x not in (".", "..") for x in parts):
        raise ValueError(f"nom de repo invalide : {repo!r}")
    return full


def _path(path: str) -> str:
    path = path.strip("/")
    if any(seg in ("..", ".") for seg in path.split("/")) or "?" in path or "#" in path:
        raise ValueError(f"chemin invalide : {path!r}")
    return path


async def _call(method: str, path: str, **kw):
    headers = {"Authorization": f"Bearer {config.GITHUB_TOKEN}",
               "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.request(method, f"{API}{path}", headers=headers, **kw)
    if r.status_code >= 400:
        raise RuntimeError(f"GitHub {r.status_code} : {r.text[:400]}")
    return r.json() if r.content else {}


@tool("github_list_repos", "Liste les repos GitHub de l'utilisateur (les plus récemment modifiés d'abord).",
      enabled=_enabled)
async def github_list_repos(ctx):
    data = await _call("GET", "/user/repos", params={"sort": "pushed", "per_page": 50})
    return [{"repo": r["full_name"], "private": r["private"], "pushed": r["pushed_at"],
             "description": r["description"]} for r in data]


@tool("github_list_files", "Liste le contenu d'un dossier d'un repo.",
      {"repo": {"type": "string", "description": "ex. 'Ben-Fit' ou 'Bene72/Ben-Fit'"},
       "path": {"type": "string", "description": "Dossier, vide = racine"},
       "ref": {"type": "string", "description": "Branche (optionnel)"}},
      ["repo"], enabled=_enabled)
async def github_list_files(ctx, repo: str, path: str = "", ref: str | None = None):
    data = await _call("GET", f"/repos/{_repo(repo)}/contents/{_path(path)}",
                       params={"ref": ref} if ref else None)
    if isinstance(data, dict):
        data = [data]
    return [{"name": d["name"], "type": d["type"], "path": d["path"], "size": d.get("size")} for d in data]


@tool("github_read_file", "Lit un fichier d'un repo.",
      {"repo": {"type": "string"}, "path": {"type": "string"}, "ref": {"type": "string"}},
      ["repo", "path"], enabled=_enabled)
async def github_read_file(ctx, repo: str, path: str, ref: str | None = None):
    d = await _call("GET", f"/repos/{_repo(repo)}/contents/{_path(path)}",
                    params={"ref": ref} if ref else None)
    return base64.b64decode(d["content"]).decode("utf-8", errors="replace")


@tool("github_search_code", "Cherche du texte dans le code d'un repo.",
      {"repo": {"type": "string"}, "query": {"type": "string"}}, ["repo", "query"], enabled=_enabled)
async def github_search_code(ctx, repo: str, query: str):
    d = await _call("GET", "/search/code", params={"q": f"{query} repo:{_repo(repo)}", "per_page": 20})
    return [i["path"] for i in d.get("items", [])]


@tool("github_recent_activity", "Derniers commits, issues et pull requests ouvertes d'un repo.",
      {"repo": {"type": "string"}}, ["repo"], enabled=_enabled)
async def github_recent_activity(ctx, repo: str):
    r = _repo(repo)
    commits = await _call("GET", f"/repos/{r}/commits", params={"per_page": 10})
    issues = await _call("GET", f"/repos/{r}/issues", params={"state": "open", "per_page": 20})
    return {
        "commits": [{"sha": c["sha"][:7], "msg": c["commit"]["message"].split("\n")[0],
                     "date": c["commit"]["author"]["date"]} for c in commits],
        "issues_et_prs_ouvertes": [{"num": i["number"], "titre": i["title"],
                                    "pr": "pull_request" in i} for i in issues],
    }


@tool("github_create_issue", "Crée une issue (ticket) dans un repo : bug, idée, tâche.",
      {"repo": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}},
      ["repo", "title"], enabled=_enabled)
async def github_create_issue(ctx, repo: str, title: str, body: str = ""):
    r = _repo(repo)

    async def do():
        d = await _call("POST", f"/repos/{r}/issues", json={"title": title, "body": body})
        return f"Issue #{d['number']} créée : {d['html_url']}"

    return confirm.request(ctx["chat_id"], f"Créer une issue dans {r}\nTitre : {title}\n\n{body[:600]}", do)


@tool("github_propose_change",
      "Propose une modification de code : crée une branche, y écrit les fichiers (contenu complet de "
      "chaque fichier) et ouvre une Pull Request. Ne touche jamais directement la branche principale. "
      "Lis toujours le fichier existant avant de le réécrire.",
      {"repo": {"type": "string"},
       "title": {"type": "string", "description": "Titre de la PR"},
       "description": {"type": "string"},
       "files": {"type": "array", "items": {"type": "object", "properties": {
           "path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
      ["repo", "title", "files"], enabled=_enabled)
async def github_propose_change(ctx, repo: str, title: str, files: list, description: str = ""):
    r = _repo(repo)
    for f in files:
        _path(f["path"])
    listing = "\n".join(f"- {f['path']} ({len(f['content'])} caractères)" for f in files)
    return confirm.request(ctx["chat_id"], f"Ouvrir une Pull Request dans {r}\nTitre : {title}\nFichiers :\n{listing}",
                           lambda: _propose_change(r, title, files, description))


async def _propose_change(r: str, title: str, files: list, description: str):
    info = await _call("GET", f"/repos/{r}")
    base = info["default_branch"]
    base_sha = (await _call("GET", f"/repos/{r}/git/ref/heads/{base}"))["object"]["sha"]
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "change"
    branch = f"agent/{slug}-{int(time.time()) % 100000}"
    await _call("POST", f"/repos/{r}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": base_sha})

    for f in files:
        path = _path(f["path"])
        sha = None
        try:
            sha = (await _call("GET", f"/repos/{r}/contents/{path}", params={"ref": branch}))["sha"]
        except RuntimeError:
            pass  # nouveau fichier
        payload = {"message": f"{title} ({path})", "branch": branch,
                   "content": base64.b64encode(f["content"].encode()).decode()}
        if sha:
            payload["sha"] = sha
        await _call("PUT", f"/repos/{r}/contents/{path}", json=payload)

    pr = await _call("POST", f"/repos/{r}/pulls", json={
        "title": title, "head": branch, "base": base,
        "body": (description + "\n\n_Proposé par l'agent Ben&Fit._").strip()})
    return f"Pull Request #{pr['number']} ouverte : {pr['html_url']}"
