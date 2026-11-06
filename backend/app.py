"""Assistant gateway for the Egypt Market Intelligence report.

    python app.py            (serves http://localhost:8765)

POST /api/ask runs: scope gate -> answer cache -> instant router (confidence >= 0.8, no tokens)
-> otherwise Gemini with the 7 DAX tools -> response guard -> trace log.
"""
from __future__ import annotations

import html
import re
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import llm
import router
import store
import templates
import tools
from model import MODEL, DaxError, ModelOffline

NAIVE_TOKENS = 32190  # the whole workbook pasted as CSV, counted with tiktoken (mcp/token_benchmark.py)
app = FastAPI(title="Egypt Market Intelligence assistant")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_private_network=True)


class Ask(BaseModel):
    question: str
    history: list[dict] = []
    page: str = ""
    conv: str = ""          # conversation id; empty = start a new conversation
    source: str = ""        # "pbi" = asked from the report; evals, MCP and scripts leave it empty


# "and Juhayna?", "طب و2026؟": a question that only makes sense with the previous turn
FOLLOW = re.compile(r"^\s*(و\S|طب\b|طيب\b|وكمان|نفس\b|and\b|what about\b|how about\b|same\b|also\b)", re.I)


def is_followup(q: str) -> bool:
    return bool(FOLLOW.match(q)) or len(q.split()) <= 2


class Feedback(BaseModel):
    trace_id: str
    rating: int
    comment: str = ""


REFUSE = {
    "out_of_scope": ("ده برة الموديل", "Outside this data model",
                     "أنا بجاوب من موديل التقرير بس: البحث على جوجل للمشروبات الغازية وتطبيقات التوصيل في 27 محافظة، وإيرادات وتوقعات جهينة وإيديتا وعبور لاند ودومتي.",
                     "I only answer from this report's model: Google search for soft drinks and delivery apps across 27 governorates, and revenue and forecasts for Juhayna, Edita, Obour Land and Domty."),
    "not_covered": ("البراند ده مش في الموديل", "That brand is not in the model",
                    "الموديل بيغطي 5 مشروبات غازية (بيبسي، كوكاكولا، سبيرو سباتس، بيج كولا، V7) و5 تطبيقات توصيل (طلبات، بريدفاست، انستاشوب، المنيوز، رابيت)، "
                    "و4 شركات أغذية في البورصة. مش هرد بأرقام براند تاني مكانه.",
                    "The model covers 5 soft drinks (Pepsi, Coca-Cola, Spiro Spathis, Big Cola, V7), 5 delivery apps (talabat, Breadfast, instashop, "
                    "elmenus, Rabbit) and 4 EGX food makers. I won't answer with another brand's numbers instead."),
    "not_held": ("الرقم ده مش في الموديل", "That figure is not in the model",
                 "الموديل فيه إيرادات الشركات الأربعة بالجنيه والدولار وتوقعاتها، لكن مفيهوش أرباح ولا هوامش ولا سعر السهم. مش هقرّب لأقرب رقم وأقولك إنه هو.",
                 "The model holds revenue for the four companies in EGP and USD with forecasts, but no profit, margins or share prices. I won't substitute the nearest figure for the one you asked about."),
    "security": ("مش هقدر أنفذ ده", "I can't do that",
                 "السؤال بيحاول يغيّر تعليمات المساعد. اسأل عن السوق أو الشركات أو التوقعات.",
                 "The question tries to change the assistant's instructions. Ask about the market, the companies or the forecasts."),
}
TRY = (["مين بيكسب في التوصيل في اسكندرية؟", "إيديتا هتعمل كام في 2027؟", "جهينة كبرت قد إيه بالدولار؟"],
       ["Which delivery app leads Alexandria?", "What will Edita make in 2027?", "How much did Juhayna grow in dollars?"])


def _calls_out(calls):
    return [{"tool": c.tool, "args": c.args, "dax": c.dax, "rows": c.rows, "ms": c.ms, "error": c.error} for c in calls]


@app.post("/api/ask")
def ask(req: Ask):
    t0 = time.perf_counter()
    q = req.question.strip()
    ar = router.is_arabic(q)
    tid = uuid.uuid4().hex[:8]
    conv = req.conv or ("pbi-" if req.source == "pbi" else "api-") + uuid.uuid4().hex[:10]
    history = (store.context(conv) if req.conv else []) or req.history
    follow = bool(history) and is_followup(q)
    rec = {"trace_id": tid, "question": q, "lang": "ar" if ar else "en", "page": req.page, "tokens": {"prompt": 0, "output": 0, "total": 0},
           "chips": [], "chart": None, "try_instead": [], "checked": 0, "untraced": [], "reasons": []}
    calls: list = []
    try:
        g = router.gate(q)
        if not g.ok and g.kind == "out_of_scope" and follow:
            # "and after inflation?" names no brand, but the previous turn does: let the model resolve it (security refusals still stand)
            g = router.Gate(True)
            rec["reasons"] = ["follow-up: scope taken from the previous turn"]
        cache_key = router.norm(q) + "|" + req.page
        hit = None if not g.ok or follow else store.cache_get(cache_key)
        if not g.ok:
            t_ar, t_en, x_ar, x_en = REFUSE[g.kind]
            rec.update(route=g.kind, intent="gate", reasons=[g.reason], title=t_ar if ar else t_en, text=x_ar if ar else x_en,
                       try_instead=TRY[0] if ar else TRY[1])
        elif hit:
            src_tid, a = hit
            rec.update(a, route="cache", cached_from=src_tid, tokens={"prompt": 0, "output": 0, "total": 0})
        else:
            plan = router.route(q)
            done = False
            if plan and plan.confidence >= router.THRESHOLD and not follow:
                rec.update(intent=plan.intent, confidence=plan.confidence, reasons=plan.reasons)
                if plan.intent == "help":
                    rec.update(templates.help_answer(ar), route="instant", try_instead=TRY[0] if ar else TRY[1])
                    done = True
                else:
                    c = tools.run(plan.tool, plan.args)
                    calls.append(c)
                    if not c.error:
                        rec.update(templates.render(plan.intent, plan.tool, c.result, ar, q), route="instant")
                        done = True
            if not done:
                if follow:
                    rec.update(intent=plan.intent if plan else "follow-up", confidence=plan.confidence if plan else 0.0,
                               reasons=(plan.reasons if plan else []) + [f"follow-up: sent to Gemini with the last {len(history)} turn(s)"])
                elif plan:
                    rec.update(intent=plan.intent, confidence=plan.confidence, reasons=plan.reasons + ["below threshold: sent to Gemini"])
                else:
                    rec.update(intent="none", confidence=0.0, reasons=["no question shape matched: sent to Gemini"])
                res = llm.answer(q, ar, history, req.page)
                calls += res["calls"]
                chart = None
                idx = int(res.get("chart_call") or 0)
                ok_calls = [c for c in res["calls"] if c.result]
                pick = res["calls"][idx - 1] if 0 < idx <= len(res["calls"]) else (ok_calls[0] if ok_calls else None)
                if pick and pick.result and res["route"] == "llm":
                    chart = templates.chart_for(pick.tool, pick.result, ar)
                rec.update(route=res["route"], model=res["model"], tokens=res["usage"], title=res.get("title", ""), text=res.get("text", ""),
                           chips=res.get("chips", [])[:4], chart=chart, try_instead=res.get("try_instead", []),
                           checked=res.get("checked", 0), untraced=res.get("untraced", []))
                if res["route"] == "llm" and not rec["untraced"] and not follow:
                    store.cache_put(cache_key, tid, {k: rec[k] for k in ("title", "text", "chips", "chart", "try_instead", "checked", "untraced", "model", "intent")})
    except ModelOffline as exc:
        rec.update(route="error", title="الموديل مش مفتوح" if ar else "The model is not open", text=str(exc))
    except (DaxError, llm.LLMError) as exc:
        rec.update(route="error", title="حصلت مشكلة" if ar else "Something failed", text=str(exc)[:300])
    rec["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    store.log(rec, calls)
    used = list(dict.fromkeys(c.tool for c in calls))
    out = {**rec, "conv": conv, "calls": _calls_out(calls), "naive_tokens": NAIVE_TOKENS,
           "sources": [tools.SOURCE[t] for t in used if t in tools.SOURCE]}
    store.save_reply(tid, conv, out)
    return out


@app.get("/api/history")
def history(conv: str = "", limit: int = 40, source: str = "pbi"):
    """One conversation (the latest from the report when no id is given) plus the report's recent conversations."""
    prefix = "pbi-" if source == "pbi" else ""
    conv = conv or store.latest_conv(prefix) or ""
    return {"conv": conv, "turns": store.turns(conv, min(limit, 100)) if conv else [], "conversations": store.conversations(12, prefix)}


@app.get("/api/trace/{tid}")
def get_trace(tid: str):
    t = store.trace(tid)
    if not t:
        raise HTTPException(404, f"trace {tid} not found")
    return t


@app.get("/api/traces")
def traces(limit: int = 50):
    return {"stats": store.stats(), "traces": store.recent(min(limit, 500))}


@app.post("/api/feedback")
def feedback(f: Feedback):
    if not store.feedback(f.trace_id, 1 if f.rating > 0 else -1, f.comment):
        raise HTTPException(404, f"trace {f.trace_id} not found")
    return {"ok": True}


@app.get("/api/health")
def health():
    try:
        MODEL.query("EVALUATE ROW ( \"ok\", 1 )")
        model_ok = True
    except Exception:
        model_ok = False
    return {"model_open": model_ok, "port": MODEL.port, "llm_models": llm.MODELS, "threshold": router.THRESHOLD}


@app.get("/logs", response_class=HTMLResponse)
def logs_page(limit: int = 80):
    s, rows = store.stats(), store.recent(limit)
    e = html.escape
    body = "".join(
        f"<tr><td><a href='/logs/{e(r['trace_id'])}'>{e(r['trace_id'])}</a></td><td>{e(r['ts'][11:])}</td><td dir='auto'>{e(r['question'])}</td>"
        f"<td><b class='r {e(r['route'])}'>{e(r['route'])}</b></td><td>{'' if r['confidence'] is None else r['confidence']}</td><td>{e(r['tools'] or '')}</td>"
        f"<td>{r['tokens_total'] or 0}</td><td>{r['latency_ms']:.0f}</td><td>{r['checked'] or 0}{' ⚠ ' + e(r['untraced']) if r['untraced'] not in (None, '[]') else ''}</td></tr>"
        for r in rows)
    return f"""<!doctype html><meta charset=utf-8><title>Assistant traces</title>
<style>body{{font:13px Segoe UI,sans-serif;margin:24px;color:#1C2928;background:#F5F0E7}}table{{border-collapse:collapse;width:100%;background:#fff}}
td,th{{padding:7px 9px;border-bottom:1px solid #EFE8DC;text-align:left}}th{{background:#FBF7F0;color:#4F5F5C}}.r{{padding:2px 8px;border-radius:99px;background:#E3F1EF}}
.llm{{background:#F6EBD3}}.out_of_scope,.security{{background:#F6DDD5}}.error{{background:#F2C9C0}}.k{{display:flex;gap:18px;margin:8px 0 16px}}.k b{{font-size:20px;display:block}}</style>
<h2>Assistant trace log</h2><div class=k><div><b>{s['n'] or 0}</b>questions</div><div><b>{s['instant'] or 0}</b>instant (0 tokens)</div>
<div><b>{s['llm'] or 0}</b>Gemini</div><div><b>{s['cache'] or 0}</b>cache</div><div><b>{s['refused'] or 0}</b>refused</div><div><b>{s['tokens'] or 0:,}</b>tokens total</div></div>
<table><tr><th>trace</th><th>time</th><th>question</th><th>route</th><th>conf.</th><th>tools</th><th>tokens</th><th>ms</th><th>figures traced</th></tr>{body}</table>"""


@app.get("/logs/{tid}", response_class=HTMLResponse)
def log_detail(tid: str):
    t = store.trace(tid)
    if not t:
        raise HTTPException(404)
    e = html.escape
    calls = "".join(f"<h3>{c['seq']}. {e(c['tool'])}({e(str(c['args']))}) · {c['rows']} rows · {c['ms']:.0f} ms</h3><pre>{e(c['dax'] or '')}</pre>"
                    f"{'<p class=err>' + e(c['error']) + '</p>' if c['error'] else ''}" for c in t["calls"])
    a = t["answer"] or {}
    return f"""<!doctype html><meta charset=utf-8><title>Trace {e(tid)}</title>
<style>body{{font:13px Segoe UI,sans-serif;margin:24px;max-width:980px;color:#1C2928;background:#F5F0E7}}pre{{background:#13312F;color:#E8F3F1;padding:12px;border-radius:10px;white-space:pre-wrap}}
.c{{background:#fff;padding:14px 16px;border-radius:12px;margin:10px 0}}.err{{color:#C0412C}}</style>
<p><a href='/logs'>← all traces</a></p><h2>Trace {e(tid)}</h2>
<div class=c dir=auto><b>{e(t['question'])}</b><br>route <b>{e(t['route'])}</b> · intent {e(t['intent'] or '')} · confidence {t['confidence']} · model {e(t['model'] or '-')}
 · {t['tokens_total'] or 0} tokens · {t['latency_ms']:.0f} ms · figures checked {t['checked'] or 0}, untraced {e(str(t['untraced'] or []))}<br>
reasons: {e('; '.join(t['reasons'] or []))}</div>
<div class=c dir=auto><b>{e(a.get('title') or '')}</b><p>{e(a.get('text') or '')}</p></div>{calls}"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
