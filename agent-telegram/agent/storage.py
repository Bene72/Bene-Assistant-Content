"""Petite base SQLite : historique des conversations, notes, tâches planifiées."""
import sqlite3
import time
from contextlib import contextmanager

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id, id);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    content TEXT NOT NULL,
    ts REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    due TEXT,
    done INTEGER NOT NULL DEFAULT 0,
    created REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS birthdays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    day INTEGER NOT NULL,
    month INTEGER NOT NULL,
    year INTEGER
);

CREATE TABLE IF NOT EXISTS journal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT NOT NULL,
    content TEXT NOT NULL,
    ts REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cron TEXT NOT NULL,
    prompt TEXT NOT NULL,
    chat_id INTEGER NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created REAL NOT NULL
);
"""


@contextmanager
def db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init():
    with db() as c:
        c.executescript(SCHEMA)


# --- Historique ----------------------------------------------------------------
def add_message(chat_id: int, role: str, content: str):
    with db() as c:
        c.execute(
            "INSERT INTO messages(chat_id, role, content, ts) VALUES (?,?,?,?)",
            (chat_id, role, content, time.time()),
        )


def history(chat_id: int, limit: int) -> list[dict]:
    with db() as c:
        rows = c.execute(
            "SELECT role, content FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
    msgs = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    # L'API exige que la conversation commence par un message utilisateur.
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    return msgs


def clear_history(chat_id: int):
    with db() as c:
        c.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))


# --- Notes -----------------------------------------------------------------------
def add_note(topic: str, content: str) -> int:
    with db() as c:
        cur = c.execute(
            "INSERT INTO notes(topic, content, ts) VALUES (?,?,?)",
            (topic.strip().lower(), content, time.time()),
        )
        return cur.lastrowid


def get_notes(topic: str | None = None) -> list[dict]:
    with db() as c:
        if topic:
            rows = c.execute(
                "SELECT * FROM notes WHERE topic LIKE ? ORDER BY id",
                (f"%{topic.strip().lower()}%",),
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM notes ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def delete_note(note_id: int) -> bool:
    with db() as c:
        return c.execute("DELETE FROM notes WHERE id=?", (note_id,)).rowcount > 0


# --- Tâches planifiées -----------------------------------------------------------
def add_task(name: str, cron: str, prompt: str, chat_id: int) -> int:
    with db() as c:
        cur = c.execute(
            "INSERT INTO tasks(name, cron, prompt, chat_id, created) VALUES (?,?,?,?,?)",
            (name, cron, prompt, chat_id, time.time()),
        )
        return cur.lastrowid


def list_tasks(enabled_only: bool = False) -> list[dict]:
    with db() as c:
        q = "SELECT * FROM tasks" + (" WHERE enabled=1" if enabled_only else "") + " ORDER BY id"
        return [dict(r) for r in c.execute(q).fetchall()]


def delete_task(task_id: int) -> bool:
    with db() as c:
        return c.execute("DELETE FROM tasks WHERE id=?", (task_id,)).rowcount > 0


# --- To-do -------------------------------------------------------------------------
def add_todo(text: str, due: str | None) -> int:
    with db() as c:
        return c.execute("INSERT INTO todos(text, due, created) VALUES (?,?,?)",
                         (text, due, time.time())).lastrowid


def list_todos(until: str | None = None) -> list[dict]:
    with db() as c:
        if until:
            rows = c.execute("SELECT id, text, due FROM todos WHERE done=0 AND (due IS NULL OR due<=?) "
                             "ORDER BY due IS NULL, due, id", (until,)).fetchall()
        else:
            rows = c.execute("SELECT id, text, due FROM todos WHERE done=0 "
                             "ORDER BY due IS NULL, due, id").fetchall()
    return [dict(r) for r in rows]


def done_todo(todo_id: int) -> bool:
    with db() as c:
        return c.execute("UPDATE todos SET done=1 WHERE id=? AND done=0", (todo_id,)).rowcount > 0


def delete_todo(todo_id: int) -> bool:
    with db() as c:
        return c.execute("DELETE FROM todos WHERE id=?", (todo_id,)).rowcount > 0


# --- Anniversaires -----------------------------------------------------------------
def add_birthday(name: str, day: int, month: int, year: int | None) -> int:
    with db() as c:
        return c.execute("INSERT INTO birthdays(name, day, month, year) VALUES (?,?,?,?)",
                         (name, day, month, year)).lastrowid


def list_birthdays() -> list[dict]:
    with db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM birthdays ORDER BY month, day").fetchall()]


def delete_birthday(bid: int) -> bool:
    with db() as c:
        return c.execute("DELETE FROM birthdays WHERE id=?", (bid,)).rowcount > 0


# --- Journal -----------------------------------------------------------------------
def add_journal(day: str, content: str):
    with db() as c:
        c.execute("INSERT INTO journal(day, content, ts) VALUES (?,?,?)", (day, content, time.time()))


def read_journal(start: str, end: str) -> list[dict]:
    with db() as c:
        rows = c.execute("SELECT day, content FROM journal WHERE day BETWEEN ? AND ? ORDER BY day, id",
                         (start, end)).fetchall()
    return [dict(r) for r in rows]


# --- Méta & sauvegarde ---------------------------------------------------------------
def get_meta(key: str) -> str | None:
    with db() as c:
        r = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return r["value"] if r else None


def set_meta(key: str, value: str):
    with db() as c:
        c.execute("INSERT INTO meta(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, value))


def backup(keep: int = 7):
    """Une copie de la base par jour dans data/backups (journal, to-do, notes…), 7 jours gardés."""
    folder = config.DATA_DIR / "backups"
    folder.mkdir(exist_ok=True)
    target = folder / f"agent-{time.strftime('%Y-%m-%d')}.db"
    if not target.exists() and config.DB_PATH.exists():
        src, dst = sqlite3.connect(config.DB_PATH), sqlite3.connect(target)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
    for old in sorted(folder.glob("agent-*.db"))[:-keep]:
        old.unlink()
