"""Gemini tool-calling route for the questions the instant router is not sure about.

The model never sees the tables: it sees the 7 tool declarations, calls them, and gets back the
few rows each DAX query returns. It may also call cannot_answer, which is how an out-of-scope
question ends: with a stated reason, never with the nearest tool's numbers.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx

import guard
import tools

ENV = Path(__file__).resolve().parent / ".env"
for line in ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []:
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

MODELS = list(dict.fromkeys(m for m in (os.getenv("GEMINI_MODEL", "gemini-3.5-flash"), "gemini-3.1-flash-lite", "gemini-3.8-flash") if m))
TIMEOUT = httpx.Timeout(25.0, connect=6.0)
URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
MAX_STEPS = 5

SYSTEM = """You are the analyst inside the "Egypt Market Intelligence" Power BI report.
The data model holds: Google Trends search interest and governorate search share in Egypt (Jan 2021 to Oct 2026) for 5 soft drinks
(Pepsi, Coca-Cola, Spiro Spathis, Big Cola, V7 Cola) and 5 delivery apps (talabat, Breadfast, instashop, elmenus, Rabbit);
27 governorates with population and urban consumers; annual and quarterly revenue (EGP and USD) for 4 EGX-listed food makers
(Juhayna, Edita, Obour Land, Domty) with a 6-model ensemble forecast to 2027 and its backtest error; headline KPIs and sources.

Rules:
1. Every figure you state must come from a tool result in this conversation. Call the tools; never use outside knowledge for numbers.
2. If the tools cannot answer (a metric the model does not hold such as profit, margin or stock price; a brand, company or period
   outside the list; an opinion or prediction about something not modelled), call cannot_answer. Do not answer a nearby question instead.
3. Search share measures attention, not sales. Say so when it matters.
4. Reply in the user's language; Egyptian Arabic if they wrote Arabic. Use Western digits (0-9).
5. Write like an analyst briefing a manager: lead with the answer, then the 1-2 figures that explain it, then one caveat if the data
   has one (backtest error, band coverage, search is not sales). No filler, no generic commentary, no advice the data does not support.
6. Your final reply is one JSON object and nothing else:
   {"title": "<headline, max 12 words>", "text": "<max 70 words>", "chips": [{"label": "...", "value": "...", "dir": "up|down|flat"}],
    "chart_call": <1-based index of the tool call whose rows should be charted, or 0>}
   Use 2 to 4 chips."""

CANNOT = {"name": "cannot_answer", "description": "Use when the data model cannot answer the question. Ends the turn.",
          "parameters": {"type": "object", "properties": {
              "reason": {"type": "string", "description": "what is missing, in the user's language"},
              "try_instead": {"type": "array", "items": {"type": "string"}, "description": "up to 3 questions the model can answer, in the user's language"}},
              "required": ["reason"]}}


class LLMError(Exception):
    pass


def _post(body: dict) -> tuple[dict, str]:
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise LLMError("GEMINI_API_KEY is missing from backend/.env")
    last = ""
    for m in MODELS:
        try:
            r = httpx.post(URL.format(m=m), headers={"x-goog-api-key": key}, json=body, timeout=TIMEOUT)
        except httpx.TransportError as exc:
            last = f"{m}: {type(exc).__name__}"
            continue  # slow or unreachable: the next model is faster than waiting
        if r.status_code == 200:
            return r.json(), m
        last = f"{m}: HTTP {r.status_code} {r.text[:200]}"
        if r.status_code not in (404, 429, 500, 502, 503, 504):
            raise LLMError(last)
    raise LLMError(last)


def _parse(text: str) -> dict:
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        try:
            return json.loads(t[i:j + 1])
        except json.JSONDecodeError:
            pass
    return {"title": "", "text": text.strip(), "chips": [], "chart_call": 0}


def answer(question: str, ar: bool, history: list[dict], context: str = "") -> dict:
    contents = []
    for h in history[-3:]:
        contents.append({"role": "user", "parts": [{"text": h.get("q", "")}]})
        contents.append({"role": "model", "parts": [{"text": json.dumps({"title": h.get("title", ""), "text": h.get("text", ""),
                                                                          "tools": h.get("tools", [])}, ensure_ascii=False)}]})
    note = f"\n\n(Report page in view: {context})" if context else ""
    note += "\n(Reply in Egyptian Arabic.)" if ar else "\n(Reply in English.)"   # this question's language, not the earlier turns'
    contents.append({"role": "user", "parts": [{"text": question + note}]})
    body = {"systemInstruction": {"parts": [{"text": SYSTEM}]},
            "tools": [{"functionDeclarations": tools.DECLARATIONS + [CANNOT]}],
            "generationConfig": {"temperature": 0, "thinkingConfig": {"thinkingLevel": "low"}}}
    calls: list[tools.Call] = []
    usage = {"prompt": 0, "output": 0, "total": 0}
    model_used, guard_rounds = "", 0
    final: dict | None = None
    for _ in range(MAX_STEPS + 2):
        resp, model_used = _post({**body, "contents": contents})
        u = resp.get("usageMetadata", {})
        usage["prompt"] += u.get("promptTokenCount", 0)
        usage["output"] += u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
        usage["total"] += u.get("totalTokenCount", 0)
        cand = (resp.get("candidates") or [{}])[0]
        content = cand.get("content") or {"role": "model", "parts": []}
        parts = content.get("parts", [])
        fcs = [p["functionCall"] for p in parts if "functionCall" in p]
        if fcs:
            contents.append(content)  # kept verbatim: Gemini 3 needs its thought signatures back
            replies = []
            for fc in fcs:
                if fc["name"] == "cannot_answer":
                    a = fc.get("args", {})
                    return {"route": "out_of_scope", "model": model_used, "calls": calls, "usage": usage,
                            "title": "مش موجود في الموديل" if ar else "Not in this data model", "text": a.get("reason", ""),
                            "chips": [], "chart_call": 0, "try_instead": a.get("try_instead", [])[:3], "checked": 0, "untraced": []}
                c = tools.run(fc["name"], fc.get("args", {}))
                calls.append(c)
                resp_part = {"name": fc["name"], "response": {"error": c.error} if c.error else {"result": c.result}}
                if fc.get("id"):
                    resp_part["id"] = fc["id"]
                replies.append({"functionResponse": resp_part})
            contents.append({"role": "user", "parts": replies})
            continue
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        final = _parse(text)
        checked, bad = guard.check([final.get("title", ""), final.get("text", "")] + [str(c.get("value", "")) for c in final.get("chips", [])],
                                   [c.result for c in calls if c.result], question)
        final["checked"], final["untraced"] = checked, bad
        if bad and guard_rounds == 0 and calls:
            guard_rounds += 1
            contents.append(content)
            contents.append({"role": "user", "parts": [{"text": "These figures do not appear in any tool result: " + ", ".join(bad)
                                                         + ". Rewrite the JSON using only returned figures, or call a tool to get them."}]})
            continue
        break
    if final is None:
        raise LLMError("the model did not finish within the step limit")
    return {"route": "llm", "model": model_used, "calls": calls, "usage": usage, **final}
