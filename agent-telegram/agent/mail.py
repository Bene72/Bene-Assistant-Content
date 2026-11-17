"""Gmail par IMAP (lecture) et SMTP (envoi), avec un mot de passe d'application Google.

Lecture : rien n'est marqué comme lu (BODY.PEEK, dossier ouvert en lecture seule).
Envoi : uniquement appelé après la confirmation /ok de Bene (voir tools/gmail.py).
"""
import asyncio
import datetime as dt
import email
import html
import imaplib
import re
import smtplib
import ssl
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import formataddr, formatdate, getaddresses, make_msgid, parseaddr, parsedate_to_datetime
from zoneinfo import ZoneInfo

from . import config

IMAP_HOST, SMTP_HOST = "imap.gmail.com", "smtp.gmail.com"
EMAIL_RE = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$")
MAX_FULL = 5_000_000


def _pwd() -> str:
    return config.GMAIL_APP_PASSWORD.replace(" ", "")


def _dec(v) -> str:
    if not v:
        return ""
    try:
        return str(make_header(decode_header(str(v)))).strip()
    except Exception:
        return str(v).strip()


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|head).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>", "\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
    return re.sub(r"\n\s*\n+", "\n\n", raw).strip()


def _payload(part) -> str:
    raw = part.get_payload(decode=True) or b""
    cs = part.get_content_charset() or "utf-8"
    try:
        return raw.decode(cs, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def body_text(msg) -> tuple[str, list[str]]:
    """Texte lisible d'un mail (text/plain sinon html converti) + noms des pièces jointes."""
    plain = html_part = None
    files = []
    for part in (msg.walk() if msg.is_multipart() else [msg]):
        if part.get_content_maintype() == "multipart":
            continue
        name = part.get_filename()
        if name:
            files.append(_dec(name))
            continue
        ct = part.get_content_type()
        if ct == "text/plain" and plain is None:
            plain = _payload(part)
        elif ct == "text/html" and html_part is None:
            html_part = _payload(part)
    text = plain if plain and plain.strip() else (html_to_text(html_part) if html_part else "")
    text = re.sub(r"\n{3,}", "\n\n", text.replace("\r\n", "\n")).strip()
    return text, files


def _date(v) -> str:
    try:
        d = parsedate_to_datetime(v)
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(ZoneInfo(config.TIMEZONE)).strftime("%d/%m %H:%M")
    except Exception:
        return _dec(v)


def _sender(v) -> str:
    name, addr = parseaddr(_dec(v))
    return f"{name} <{addr}>" if name and addr else (addr or name)


# --- IMAP (bloquant : appelé via asyncio.to_thread) -------------------------------------
def _connect() -> imaplib.IMAP4_SSL:
    M = imaplib.IMAP4_SSL(IMAP_HOST, 993, ssl_context=ssl.create_default_context(), timeout=30)
    M.login(config.GMAIL_ADDRESS, _pwd())
    return M


def _all_mail_folder(M) -> str:
    """Dossier « Tous les messages » (nom qui dépend de la langue du compte), sinon INBOX."""
    _typ, data = M.list()
    for raw in data or []:
        line = raw.decode(errors="replace") if isinstance(raw, bytes) else str(raw)
        if "\\All" in line:
            m = re.search(r'"([^"]+)"\s*$', line) or re.search(r"(\S+)\s*$", line)
            if m:
                return m.group(1)
    return "INBOX"


def _open(M):
    folder = _all_mail_folder(M)
    typ, _ = M.select(f'"{folder}"', readonly=True)
    if typ != "OK":
        M.select("INBOX", readonly=True)


def _search(M, query: str) -> list[bytes]:
    q = re.sub(r'["\\\r\n]', " ", query).strip() or "in:inbox"
    try:
        q.encode("ascii")
        _typ, data = M.uid("SEARCH", "X-GM-RAW", f'"{q}"')
    except UnicodeEncodeError:
        M.literal = q.encode("utf-8")
        _typ, data = M.uid("SEARCH", "CHARSET", "UTF-8", "X-GM-RAW")
    return data[0].split() if data and data[0] else []


def _fetch(M, uid: bytes | str, spec: str) -> tuple[bytes, bytes]:
    _typ, data = M.uid("FETCH", uid, spec)
    meta, body = b"", b""
    for item in data or []:
        if isinstance(item, tuple):
            meta += item[0]
            body = body or item[1]
        elif isinstance(item, bytes):
            meta += item
    return meta, body


def _list_sync(query: str, limit: int, snippet: bool) -> dict:
    M = _connect()
    try:
        _open(M)
        uids = _search(M, query)
        out = []
        for uid in reversed(uids[-limit:]):  # du plus récent au plus ancien
            spec = "(FLAGS BODY.PEEK[]<0.40000>)" if snippet else \
                "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
            meta, raw = _fetch(M, uid, spec)
            msg = email.message_from_bytes(raw)
            item = {"id": uid.decode(), "de": _sender(msg.get("From")), "objet": _dec(msg.get("Subject")) or "(sans objet)",
                    "date": _date(msg.get("Date")), "non_lu": b"\\Seen" not in meta}
            if snippet:
                text, files = body_text(msg)
                item["extrait"] = re.sub(r"\s+", " ", text)[:220]
                if files:
                    item["pieces_jointes"] = files
            out.append(item)
        return {"total": len(uids), "messages": out}
    finally:
        try:
            M.logout()
        except Exception:
            pass


def _read_sync(uid: str) -> dict:
    if not uid.isdigit():
        raise ValueError("identifiant de mail invalide")
    M = _connect()
    try:
        _open(M)
        meta, _ = _fetch(M, uid, "(RFC822.SIZE)")
        size = int(re.search(rb"RFC822\.SIZE (\d+)", meta).group(1)) if b"RFC822.SIZE" in meta else 0
        spec = "(FLAGS BODY.PEEK[])" if size <= MAX_FULL else "(FLAGS BODY.PEEK[]<0.300000>)"
        meta, raw = _fetch(M, uid, spec)
        if not raw:
            raise ValueError("mail introuvable")
        msg = email.message_from_bytes(raw)
        text, files = body_text(msg)
        return {"id": uid, "de": _sender(msg.get("From")),
                "a": [a for _, a in getaddresses([_dec(msg.get("To", ""))]) if a],
                "cc": [a for _, a in getaddresses([_dec(msg.get("Cc", ""))]) if a],
                "repondre_a": parseaddr(_dec(msg.get("Reply-To") or msg.get("From")))[1],
                "objet": _dec(msg.get("Subject")), "date": _date(msg.get("Date")),
                "message_id": (msg.get("Message-ID") or "").strip(),
                "references": (msg.get("References") or "").strip(),
                "texte": text[:15000] + ("\n…[tronqué]" if len(text) > 15000 else ""),
                "pieces_jointes": files}
    finally:
        try:
            M.logout()
        except Exception:
            pass


def _send_sync(to: list[str], cc: list[str], subject: str, body: str, reply: dict | None) -> str:
    msg = EmailMessage()
    msg["From"] = formataddr((config.MAIL_FROM_NAME, config.GMAIL_ADDRESS))
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=config.GMAIL_ADDRESS.split("@")[-1])
    if reply and reply.get("message_id"):
        msg["In-Reply-To"] = reply["message_id"]
        msg["References"] = (reply.get("references", "") + " " + reply["message_id"]).strip()
    msg.set_content(body)
    with smtplib.SMTP_SSL(SMTP_HOST, 465, context=ssl.create_default_context(), timeout=30) as s:
        s.login(config.GMAIL_ADDRESS, _pwd())
        s.send_message(msg)
    return msg["Message-ID"]


# --- API async ------------------------------------------------------------------------
async def search(query: str, limit: int = 10, snippet: bool = True) -> dict:
    return await asyncio.to_thread(_list_sync, query, max(1, min(int(limit), 25)), snippet)


async def read(uid: str) -> dict:
    return await asyncio.to_thread(_read_sync, str(uid).strip())


async def send(to: list[str], cc: list[str], subject: str, body: str, reply: dict | None) -> str:
    return await asyncio.to_thread(_send_sync, to, cc, subject, body, reply)


async def unread_summary() -> dict:
    """Pour le brief : non lus des dernières 24 h dans la boîte principale (sans le contenu)."""
    r = await search("in:inbox is:unread newer_than:1d -category:promotions -category:social", 8, snippet=False)
    return {"nombre": r["total"], "derniers": [{"de": m["de"], "objet": m["objet"]} for m in r["messages"]]}


async def check() -> str:
    def _c():
        M = _connect()
        try:
            folder = _all_mail_folder(M)
            M.select("INBOX", readonly=True)
            n = len(_search(M, "in:inbox is:unread"))
            return f"{config.GMAIL_ADDRESS}, {n} non lu(s) (dossier : {folder})"
        finally:
            M.logout()
    return await asyncio.to_thread(_c)


def clean_addresses(raw) -> list[str]:
    if not raw:
        return []
    items = raw if isinstance(raw, list) else re.split(r"[,;]", str(raw))
    out = []
    for it in items:
        addr = parseaddr(str(it).strip())[1]
        if not EMAIL_RE.match(addr):
            raise ValueError(f"adresse mail invalide : {it!r}")
        out.append(addr)
    return out
