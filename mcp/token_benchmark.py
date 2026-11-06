"""Tokens per question: paste the Egypt workbook into the prompt vs. call egypt-market-mcp tools.

Naive = every base sheet of Egypt_Market_Intelligence_2026.xlsx as CSV + the question
        (the derived Knowledge and Feed sheets are left out so the naive side is not double-counted).
MCP   = tool catalog (names, descriptions, JSON schemas) + question + tool call + tool result.
Counts use tiktoken cl100k_base as a model-neutral estimate.
"""
import asyncio
import json
import sys
from pathlib import Path

import pandas as pd
import tiktoken

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import egypt_mcp  # noqa: E402

enc = tiktoken.get_encoding("cl100k_base")
tok = lambda s: len(enc.encode(s))

QUESTIONS = [
    ("Where does Coca-Cola beat its average?", "search_share", {"category": "Soft drinks", "brand": "Coca-Cola"}),
    ("مين أكتر تطبيق توصيل بيدوّروا عليه في القاهرة؟", "search_share", {"category": "Delivery apps", "governorate": "Cairo"}),
    ("Edita revenue in dollars since 2022", "company_financials", {"company": "Edita", "unit": "USD"}),
    ("مين بيكبر ومين بيتراجع في تطبيقات التوصيل؟", "search_trend", {"brands": ["talabat", "Breadfast", "instashop", "elmenus", "Rabbit"], "start": "2021-01", "end": "2026-10", "every": 12}),
    ("Using the forecast trend, which listed food maker grows fastest in 2027?", "forecast", {"company": "all"}),
    ("المشروبات بتتباع فين أكتر؟", "where_sold", {"top_n": 6}),
]


async def main():
    sheets = pd.read_excel(HERE.parent / "data" / "Egypt_Market_Intelligence_2026.xlsx", sheet_name=None, header=None)
    naive_ctx = "\n\n".join(f"## {n}\n" + df.to_csv(index=False, header=False) for n, df in sheets.items() if n not in ("Knowledge", "Feed"))
    naive = tok(naive_ctx)
    tools = await egypt_mcp.mcp.list_tools()
    catalog = json.dumps([{"name": t.name, "description": t.description, "input_schema": getattr(t, "input_schema", None) or getattr(t, "inputSchema", None)} for t in tools],
                         separators=(",", ":"))
    cat_t = tok(catalog)
    rows = []
    for q, name, args in QUESTIONS:
        res = getattr(egypt_mcp, name)(**args)
        call = json.dumps({"name": name, "arguments": args}, ensure_ascii=False, separators=(",", ":"))
        result = json.dumps(res, ensure_ascii=False, separators=(",", ":"))
        m = cat_t + tok(q) + tok(call) + tok(result)
        rows.append({"q": q, "tool": name, "naive": naive + tok(q), "mcp": m, "result_tokens": tok(result)})
    avg = sum(r["mcp"] for r in rows) / len(rows)
    out = {"naive_context_tokens": naive, "catalog_tokens": cat_t, "tools": len(tools), "avg_mcp_tokens": round(avg),
           "saving_pct": round((1 - avg / (naive + 12)) * 100, 1), "questions": rows}
    (HERE / "token_benchmark.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "questions"}))
    for r in rows:
        print(r["tool"], r["mcp"], "result", r["result_tokens"])


asyncio.run(main())
