"""Import d'anniversaires depuis un fichier .csv / .txt envoyé au bot (sans appel à Claude).

Formats acceptés, une personne par ligne (séparateur « ; », « , » ou tabulation) :
    Nom;12;3            (jour;mois)
    Nom;12;3;1990       (jour;mois;année)
    Nom;12/03           (JJ/MM ou JJ/MM/AAAA)
    Nom;12 mars         (mois en toutes lettres)
Les lignes vides, les lignes qui commencent par « # » et l'en-tête (nom/name) sont ignorées.
"""
import datetime as dt
import re
import unicodedata

from . import storage

MAX_BYTES = 500_000

MONTHS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
          "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower().strip())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _valid(day: int, month: int, year: int | None) -> tuple[int, int, int | None] | None:
    try:
        dt.date(2000, month, day)  # 2000 est bissextile : le 29/02 est accepté
    except ValueError:
        return None
    if year is not None and not (1900 <= year <= dt.date.today().year):
        year = None
    return day, month, year


def parse_date(fields: list[str]) -> tuple[int, int, int | None] | None:
    fields = [f.strip() for f in fields if f.strip()]
    if not fields:
        return None
    if all(f.isdigit() for f in fields) and len(fields) in (2, 3):
        year = int(fields[2]) if len(fields) == 3 else None
        return _valid(int(fields[0]), int(fields[1]), year)
    if len(fields) != 1:
        return None
    text = fields[0]
    m = re.fullmatch(r"(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{4}))?", text)
    if m:
        return _valid(int(m[1]), int(m[2]), int(m[3]) if m[3] else None)
    m = re.fullmatch(r"(\d{1,2})(?:er)?\s+([^\d\s]+)(?:\s+(\d{4}))?", _plain(text))
    if m and m[2] in MONTHS:
        return _valid(int(m[1]), MONTHS[m[2]], int(m[3]) if m[3] else None)
    return None


def parse(text: str) -> tuple[list[tuple[str, int, int, int | None]], list[str]]:
    """Renvoie (entrées valides, lignes ignorées)."""
    entries, bad = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        sep = ";" if ";" in line else ("\t" if "\t" in line else ",")
        name, *rest = [p.strip() for p in line.split(sep)]
        if _plain(name) in ("nom", "name", "prenom"):
            continue
        date = parse_date(rest)
        if not name or date is None:
            bad.append(line[:80])
            continue
        entries.append((name[:120], *date))
    return entries, bad


def import_text(text: str) -> dict:
    entries, bad = parse(text)
    known = {(b["name"].strip().lower(), b["day"], b["month"]) for b in storage.list_birthdays()}
    added = dup = 0
    for name, day, month, year in entries:
        key = (name.lower(), day, month)
        if key in known:
            dup += 1
            continue
        storage.add_birthday(name, day, month, year)
        known.add(key)
        added += 1
    return {"added": added, "duplicates": dup, "ignored": bad}


def summary(res: dict) -> str:
    lines = [f"🎂 {res['added']} anniversaire(s) ajouté(s)"]
    if res["duplicates"]:
        lines.append(f"{res['duplicates']} déjà connu(s), pas de doublon créé")
    if res["ignored"]:
        lines.append(f"{len(res['ignored'])} ligne(s) ignorée(s) (date illisible) :")
        lines += [f"• {line}" for line in res["ignored"][:10]]
    lines.append(f"Total enregistré : {len(storage.list_birthdays())}")
    return "\n".join(lines)
