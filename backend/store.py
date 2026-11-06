"""Trace log, answer cache and feedback, in one SQLite file.

Every question gets a trace id shown on its answer card. The trace keeps the route, confidence,
model, tokens, latency, the guard result, and each tool call with its arguments, the exact DAX it
ran, row count, time and result, so any number can be checked without replaying the conversation.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

DB = Path(__file__).resolve().parent / "traces.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
  trace_id TEXT PRIMARY KEY, ts TEXT, question TEXT, lang TEXT, page TEXT, route TEXT, intent TEXT, confidence REAL,
  reasons TEXT, model TEXT, tokens_prompt INT, tokens_output INT, tokens_total INT, latency_ms REAL,
  checked INT, untraced TEXT, answer TEXT, cached_from TEXT, rating INT, comment TEXT);
CREATE TABLE IF NOT EXISTS tool_calls (
  trace_id TEXT, seq INT, tool TEXT, args TEXT, dax TEXT, rows INT, ms REAL, error TEXT, result TEXT);
CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, day TEXT, trace_id TEXT, answer TEXT);
"""


_migrated = False


def _db():
    global _migrated
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    if not _migrated:   # conversation id + the full reply, so a chat can be redrawn after the popup closes
        have = {r[1] for r in c.execute("PRAGMA table_info(requests)")}
        for col in ("conv", "reply"):
            if col not in have:
                c.execute(f"ALTER TABLE requests ADD COLUMN {col} TEXT")
        c.execute("CREATE INDEX IF NOT EXISTS ix_requests_conv ON requests (conv, ts)")
        _migrated = True
    return c


def log(rec: dict, calls: list):
    with _db() as c:
        c.execute("""INSERT INTO requests (trace_id, ts, question, lang, page, route, intent, confidence, reasons, model, tokens_prompt,
                     tokens_output, tokens_total, latency_ms, checked, untraced, answer, cached_from)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (rec["trace_id"], datetime.now().isoformat(timespec="seconds"), rec["question"], rec["lang"], rec.get("page", ""),
                   rec["route"], rec.get("intent", ""), rec.get("confidence"), json.dumps(rec.get("reasons", []), ensure_ascii=False),
                   rec.get("model", ""), rec["tokens"]["prompt"], rec["tokens"]["output"], rec["tokens"]["total"], rec["latency_ms"],
                   rec.get("checked", 0), json.dumps(rec.get("untraced", []), ensure_ascii=False),
                   json.dumps({k: rec.get(k) for k in ("title", "text", "chips", "chart", "try_instead")}, ensure_ascii=False), rec.get("cached_from")))
        for i, k in enumerate(calls, 1):
            c.execute("INSERT INTO tool_calls VALUES (?,?,?,?,?,?,?,?,?)",
                      (rec["trace_id"], i, k.tool, json.dumps(k.args, ensure_ascii=False), "\n\n".join(k.dax), k.rows, k.ms, k.error,
                       json.dumps(k.result, ensure_ascii=False)))


def trace(tid: str) -> dict | None:
    with _db() as c:
        r = c.execute("SELECT * FROM requests WHERE trace_id = ?", (tid,)).fetchone()
        if not r:
            return None
        calls = [dict(x) for x in c.execute("SELECT * FROM tool_calls WHERE trace_id = ? ORDER BY seq", (tid,))]
    out = dict(r)
    for k in ("reasons", "untraced", "answer"):
        out[k] = json.loads(out[k]) if out[k] else None
    for x in calls:
        x["args"] = json.loads(x["args"])
        x["result"] = json.loads(x["result"]) if x["result"] else None
    out["calls"] = calls
    return out


def recent(limit: int = 50) -> list[dict]:
    with _db() as c:
        rows = c.execute("""SELECT r.trace_id, r.ts, r.question, r.route, r.intent, r.confidence, r.model, r.tokens_total, r.latency_ms,
                            r.checked, r.untraced, r.rating, (SELECT COUNT(*) FROM tool_calls t WHERE t.trace_id = r.trace_id) AS calls,
                            (SELECT GROUP_CONCAT(tool, ', ') FROM tool_calls t WHERE t.trace_id = r.trace_id) AS tools
                            FROM requests r ORDER BY r.ts DESC LIMIT ?""", (limit,)).fetchall()
    return [dict(x) for x in rows]


def stats() -> dict:
    with _db() as c:
        r = c.execute("""SELECT COUNT(*) n, SUM(route='instant') instant, SUM(route='llm') llm, SUM(route='cache') cache,
                         SUM(route IN ('out_of_scope','security')) refused, SUM(tokens_total) tokens, AVG(latency_ms) avg_ms,
                         SUM(rating=1) up, SUM(rating=-1) down FROM requests""").fetchone()
    return dict(r)


def cache_get(key: str):
    with _db() as c:
        r = c.execute("SELECT trace_id, answer FROM cache WHERE key = ? AND day = ?", (key, date.today().isoformat())).fetchone()
    return (r["trace_id"], json.loads(r["answer"])) if r else None


def cache_put(key: str, tid: str, answer: dict):
    with _db() as c:
        c.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?,?)", (key, date.today().isoformat(), tid, json.dumps(answer, ensure_ascii=False)))


def save_reply(tid: str, conv: str, reply: dict):
    with _db() as c:
        c.execute("UPDATE requests SET conv = ?, reply = ? WHERE trace_id = ?", (conv, json.dumps(reply, ensure_ascii=False), tid))


def latest_conv(prefix: str = "") -> str | None:
    with _db() as c:
        r = c.execute("SELECT conv FROM requests WHERE conv LIKE ? ORDER BY ts DESC, rowid DESC LIMIT 1", (prefix + "%",)).fetchone()
    return r["conv"] if r else None


def turns(conv: str, limit: int = 40) -> list[dict]:
    """Every answer of one conversation, oldest first, exactly as the visual received it."""
    with _db() as c:
        rows = c.execute("""SELECT reply, rating FROM (SELECT reply, rating, ts, rowid AS rid FROM requests WHERE conv = ? AND reply IS NOT NULL
                            ORDER BY ts DESC, rowid DESC LIMIT ?) ORDER BY ts, rid""", (conv, limit)).fetchall()
    out = []
    for r in rows:
        x = json.loads(r["reply"])
        x["rating"] = r["rating"]
        out.append(x)
    return out


def context(conv: str, n: int = 3) -> list[dict]:
    """The last n turns, trimmed to what the model needs to resolve a follow-up question."""
    out = []
    for x in turns(conv, n):
        out.append({"q": x.get("question", ""), "title": x.get("title", ""), "text": (x.get("text") or "")[:400],
                    "tools": [f"{k['tool']}({json.dumps(k['args'], ensure_ascii=False)})" for k in x.get("calls", [])]})
    return out


def conversations(limit: int = 12, prefix: str = "") -> list[dict]:
    with _db() as c:
        rows = c.execute("""SELECT conv, MIN(ts) started, MAX(ts) last, COUNT(*) n,
                            (SELECT question FROM requests q WHERE q.conv = r.conv ORDER BY ts, rowid LIMIT 1) first
                            FROM requests r WHERE conv LIKE ? GROUP BY conv ORDER BY last DESC LIMIT ?""", (prefix + "%", limit)).fetchall()
    return [dict(x) for x in rows]


def feedback(tid: str, rating: int, comment: str = "") -> bool:
    with _db() as c:
        n = c.execute("UPDATE requests SET rating = ?, comment = ? WHERE trace_id = ?", (rating, comment, tid)).rowcount
    return n > 0
