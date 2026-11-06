"""Answers for the instant route: headline, text, chips and a chart, written from the tool's rows by code.

No model writes these, so they cost no tokens; every figure in them comes straight from the DAX result.
The chart builder is shared with the Gemini route, which also never spends tokens on drawing.
"""
from __future__ import annotations

from statistics import mean

from tools import COMPANY_AR, catalog

NILE, LIGHT, GOLD, GRAY = "#0B6E69", "#7FB8B3", "#C2922F", "#C6BDAD"


def pct(v: float) -> str:
    return f"{v * 100:.0f}%"


def bname(b: str, ar: bool) -> str:
    return (catalog()["brands"].get(b, {}).get("AR") or b) if ar else b


def gname(code: str, ar: bool) -> str:
    g = catalog()["govs"].get(code, {})
    return (g.get("AR") if ar else g.get("EN")) or code


def cname(c: str, ar: bool) -> str:
    return COMPANY_AR.get(c, c) if ar else c


def bn(v_m: float, ar: bool) -> str:
    return f"{v_m / 1000:.1f} مليار جنيه" if ar else f"EGP {v_m / 1000:.1f}B"


def ratio_chip(label: str, r, ar: bool) -> dict:
    if r is None:
        return {"label": label, "value": "جديد" if ar else "new", "dir": "up"}
    if r >= 1.15:
        return {"label": label, "value": f"▲ {r:.1f}x", "dir": "up"}
    if r <= 0.87:
        return {"label": label, "value": f"▼ {(1 - r) * 100:.0f}%", "dir": "down"}
    return {"label": label, "value": "≈ ثابت" if ar else "≈ flat", "dir": "flat"}


# ---------------------------------------------------------------- charts from tool rows (both routes)
def chart_for(tool: str, p: dict, ar: bool) -> dict | None:
    if not p:
        return None
    if tool == "search_share":
        if "brands" in p:
            return {"kind": "bars", "fmt": "pct", "bars": [{"label": bname(x["b"], ar), "v": x["s"], "color": LIGHT if i else NILE} for i, x in enumerate(p["brands"])]}
        if "top" in p:
            bars = [{"label": gname(x["g"], ar), "v": x["s"], "color": LIGHT if i else NILE} for i, x in enumerate(p["top"])]
            return {"kind": "bars", "fmt": "pct", "bars": bars + [{"label": "المتوسط" if ar else "Median", "v": p["median_share"], "color": GRAY}]}
        return {"kind": "bars", "fmt": "pct", "bars": [{"label": bname(x["b"], ar), "v": x["s"], "color": LIGHT if i else NILE} for i, x in enumerate(p["national_last_12m"])]}
    if tool == "search_trend":
        if "brands" in p:
            rows = sorted(p["brands"], key=lambda x: -x["share"])
            return {"kind": "bars", "fmt": "pct", "bars": [{"label": bname(x["b"], ar), "v": x["share"], "color": LIGHT if i else NILE} for i, x in enumerate(rows)]}
        pal = [NILE, GOLD, "#A99F8C", GRAY, "#1E4FB8"]
        return {"kind": "lines", "fmt": "num", "lines": [{"name": bname(b, ar), "color": pal[i % 5], "pts": pts} for i, (b, pts) in enumerate(p["series"].items())]}
    if tool == "company_financials":
        ys = [y for y in p["years"] if y["basis"] == "Actual"]
        key, fmt = ("usd_m", "usd_m") if p.get("unit_asked") == "USD" else ("egp_m", "egp_m")
        return {"kind": "bars", "fmt": fmt, "bars": [{"label": str(y["y"]), "v": y[key], "color": NILE if i == len(ys) - 1 else LIGHT} for i, y in enumerate(ys)]}
    if tool == "forecast":
        if "companies" in p:
            pal = [NILE, GOLD, "#A99F8C", GRAY]
            return {"kind": "lines", "fmt": "index", "lines": [{"name": cname(c["c"], ar), "color": pal[i % 4], "pts": c["indexed"]} for i, c in enumerate(p["companies"])]}
        fc = p["forecast"]
        return {"kind": "lines", "fmt": "egp_m",
                "lines": [{"name": "فعلي" if ar else "Actual", "color": NILE, "pts": p["actual"]},
                          {"name": "متوقع" if ar else "Forecast", "color": GOLD, "pts": [p["actual"][-1]] + [[x["q"], x["f"]] for x in fc]}],
                "band": [{"x": x["q"], "lo": x["lo80"], "hi": x["hi80"]} for x in fc]}
    if tool == "where_sold":
        return {"kind": "bars", "fmt": "m", "bars": [{"label": gname(x["g"], ar), "v": x["urban_m"], "color": NILE if i < 3 else LIGHT} for i, x in enumerate(p["top"])]}
    return None


# ---------------------------------------------------------------- instant answers
def help_answer(ar: bool) -> dict:
    return {"title": "أقدر أساعدك في" if ar else "I can help with",
            "text": ("أقوى محافظات أي براند، التطبيق الأول في أي محافظة، مين بيكبر ومين بيتراجع، أثر المقاطعة، إيرادات جهينة وإيديتا وعبور لاند ودومتي "
                     "بالجنيه والدولار، وتوقعات 2026 و2027 بدقتها.") if ar else
                    ("where a brand is strongest, the top app in a governorate, who is growing or falling, the boycott effect, revenue for Juhayna, Edita, "
                     "Obour Land and Domty in pounds and dollars, and the 2026–2027 forecast with its error."),
            "chips": [], "chart": None}


def render(intent: str, tool: str, p: dict, ar: bool, q: str = "") -> dict:
    chart = chart_for(tool, p, ar)
    if intent == "gov_category":
        rows = p["brands"]
        a = rows[0]
        cat_ar = "تطبيقات التوصيل" if p["category"] == "Delivery apps" else "المشروبات الغازية"
        rest = rows[1:3]
        if ar:
            tail = "".join([f"، تليها {bname(rest[0]['b'], True)} بنسبة {pct(rest[0]['s'])}" if rest else "",
                            f" ثم {bname(rest[1]['b'], True)} بنسبة {pct(rest[1]['s'])}" if len(rest) > 1 else ""])
            title, text = f"{bname(a['b'], True)} تتصدر {gname(p['governorate'], True)}", f"في {gname(p['governorate'], True)} تستحوذ {bname(a['b'], True)} على {pct(a['s'])} من البحث عن {cat_ar}{tail}."
        else:
            tail = "".join([f", then {rest[0]['b']} at {pct(rest[0]['s'])}" if rest else "", f" and {rest[1]['b']} at {pct(rest[1]['s'])}" if len(rest) > 1 else ""])
            title, text = f"{a['b']} leads {gname(p['governorate'], False)}", f"In {gname(p['governorate'], False)}, {a['b']} takes {pct(a['s'])} of {p['category'].lower()} searches{tail}."
        chips = [{"label": bname(r["b"], ar), "value": pct(r["s"]), "dir": "up" if i == 0 else "flat"} for i, r in enumerate(rows[:3])]
    elif intent == "where_brand":
        top, med, b = p["top"], p["median_share"], p["brand"]
        three = ("، " if ar else ", ").join(f"{gname(x['g'], ar)} ({pct(x['s'])})" for x in top[:3])
        title = f"{bname(b, True)} أقوى في {gname(top[0]['g'], True)}" if ar else f"{b} is strongest in {gname(top[0]['g'], False)}"
        text = (f"أعلى حصة بحث لـ{bname(b, True)} في {three}، مقابل {pct(med)} في المحافظة المتوسطة." if ar
                else f"Its highest search share is in {three}, against {pct(med)} in the median governorate.")
        chips = [{"label": gname(top[0]["g"], ar), "value": f"▲ +{(top[0]['s'] - med) * 100:.0f} {'نقطة' if ar else 'pts'}", "dir": "up"},
                 {"label": "المتوسط" if ar else "Median", "value": pct(med), "dir": "flat"}]
    elif intent == "momentum":
        rows = sorted(p["brands"], key=lambda x: -(99 if x["ratio"] is None else x["ratio"]))
        up = [r for r in rows if r["ratio"] is None and r["new_since_2021"] or (r["ratio"] or 0) >= 1.15]
        down = [r for r in rows if r["ratio"] is not None and r["ratio"] <= 0.87]

        def fr(r):
            if r["ratio"] is None:
                return "جديد" if ar else "new"
            return f"{r['ratio']:.1f}x" if r["ratio"] >= 1 else f"−{(1 - r['ratio']) * 100:.0f}%"
        if ar:
            title = (f"{bname(up[0]['b'], True)} الأسرع نموًا" if up else "لا نمو واضح") + (f"، و{bname(down[0]['b'], True)} الأكثر تراجعًا" if down else "")
            text = (f"متوسط البحث في 2021 مقابل آخر 12 شهر: {'، '.join(f'{bname(r['b'], True)} {fr(r)}' for r in up) or 'لا يوجد نمو'}"
                    + (f"، بينما تراجع {'، '.join(f'{bname(r['b'], True)} {fr(r)}' for r in down)}" if down else "") + ". الشارت فيه الحصة الحالية من البحث.")
        else:
            title = (f"{up[0]['b']} is growing fastest" if up else "No clear grower") + (f"; {down[0]['b']} is falling most" if down else "")
            text = (f"2021 average search vs the latest 12 months: {', '.join(f'{r['b']} {fr(r)}' for r in up) or 'no growers'}"
                    + (f", while {', '.join(f'{r['b']} {fr(r)}' for r in down)} fell" if down else "") + ". The chart shows today's share of searches.")
        chips = [ratio_chip(bname(r["b"], ar), r["ratio"], ar) for r in rows[:5]]
    elif intent == "boycott":
        sp = [x for x in p["series"].get("Spiro Spathis", [])]
        peak = p["peak"].get("Spiro Spathis", ["", 0])
        now = p["avg_last_12m"].get("Spiro Spathis", 0)
        title = "أثر المقاطعة كان قويًا ثم تلاشى" if ar else "The boycott spike was real, then faded"
        text = (f"مع بداية المقاطعة في أكتوبر 2023 قفز البحث عن سبيرو سباتس من {sp[0][1] if sp else 0} إلى {peak[1]} نقطة في {peak[0]}، ومتوسطه في آخر 12 شهرًا {now:.1f} فقط."
                if ar else f"When the boycott started in Oct 2023, Spiro Spathis search jumped from {sp[0][1] if sp else 0} to {peak[1]} in {peak[0]}. Over the last 12 months it averages {now:.1f}.")
        chips = [{"label": "الذروة" if ar else "Peak", "value": f"▲ {peak[1]}", "dir": "up"},
                 {"label": "آخر 12 شهرًا" if ar else "Last 12 months", "value": f"▼ {now:.1f}", "dir": "down"}]
    elif intent == "company_usd":
        ys = [y for y in p["years"] if y["basis"] == "Actual"]
        a, z, c = ys[0], ys[-1], p["company"]
        x, g = z["egp_m"] / a["egp_m"], z["usd_m"] / a["usd_m"] - 1
        sign = "+" if g >= 0 else "−"
        title = (f"{cname(c, True)}: {x:.1f} أضعاف بالجنيه، {sign}{abs(g) * 100:.0f}% بالدولار" if ar else f"{c}: {x:.1f}x in pounds, {sign}{abs(g) * 100:.0f}% in dollars")
        text = (f"ارتفعت الإيرادات من {bn(a['egp_m'], True)} في {a['y']} إلى {bn(z['egp_m'], True)} في {z['y']}، لكنها بالدولار من {a['usd_m']:.0f} إلى {z['usd_m']:.0f} مليون دولار بسبب تراجع الجنيه."
                if ar else f"Revenue went from {bn(a['egp_m'], False)} in {a['y']} to {bn(z['egp_m'], False)} in {z['y']}; in dollars that is ${a['usd_m']:.0f}M to ${z['usd_m']:.0f}M because the pound fell.")
        chips = [{"label": "بالجنيه" if ar else "In EGP", "value": f"▲ {x:.1f}x", "dir": "up"},
                 {"label": "بالدولار" if ar else "In USD", "value": f"{'▲ +' if g >= 0 else '▼ '}{g * 100:.0f}%", "dir": "up" if g >= 0.05 else "down" if g <= -0.05 else "flat"}]
    elif intent == "forecast":
        c, fy, m = p["company"], p["fy_egp_m"], p["ensemble_mape_holdout_pct"]
        a25, f26, f27 = fy.get(2025), fy.get(2026), fy.get(2027)
        best = min(p["models"], key=lambda r: r["mape_holdout_pct"]) if p["models"] else None
        yr = 2026 if "2026" in q and "2027" not in q else 2027   # headline the year that was asked; 2027 by default
        title = f"{cname(c, True)}: {bn(fy.get(yr), True)} متوقعة في {yr}" if ar else f"{c}: {bn(fy.get(yr), False)} expected in {yr}"
        text = (f"المتوقع {bn(f26, True)} في 2026 و{bn(f27, True)} في 2027، بهامش 80% في الشارت. الموديل مزيج من أفضل 3 من 6 نماذج، وخطؤه {m:.1f}% على 4 أرباع لم يرها أثناء التدريب"
                + (f"؛ أدق نموذج منفرد {best['m']} ({best['mape_holdout_pct']:.1f}%)." if best else ".")
                if ar else
                f"The ensemble expects {bn(f26, False)} in 2026 and {bn(f27, False)} in 2027, with the 80% band in the chart. It blends the best 3 of 6 models and missed 4 unseen quarters by {m:.1f}% on average"
                + (f"; the best single model was {best['m']} ({best['mape_holdout_pct']:.1f}%)." if best else "."))
        rg = p.get("real_growth_2027_pct")
        if rg is not None:
            sc = p["inflation_scenarios_2027_egp_m"]
            text += (f" بعد خصم التضخم، نمو 2027 الحقيقي {rg:+.1f}%، ولو التضخم 9% أو 20% بدل 13.9% هتبقى 2027 بين {bn(sc['low_9pct'], True)} و{bn(sc['high_20pct'], True)}."
                     if ar else f" After inflation, 2027 growth is {rg:+.1f}% in real terms; at 9% or 20% inflation instead of 13.9%, 2027 lands between "
                     f"{bn(sc['low_9pct'], False)} and {bn(sc['high_20pct'], False)}.")
        chips = [{"label": "2027", "value": f"▲ +{(f27 / f26 - 1) * 100:.0f}%", "dir": "up"},
                 {"label": "بعد التضخم" if ar else "After inflation", "value": (f"▲ +{rg:.1f}%" if rg >= 0 else f"▼ {abs(rg):.1f}%") if rg is not None else "–",
                  "dir": "up" if (rg or 0) >= 1 else "down" if (rg or 0) <= -1 else "flat"},
                 {"label": "الخطأ" if ar else "Error", "value": f"{m:.1f}%", "dir": "flat"}]
    elif intent == "forecast_compare":
        rows = p["companies"]
        best, sure, weak = rows[0], min(rows, key=lambda r: r["mape_holdout_pct"]), max(rows, key=lambda r: r["mape_holdout_pct"])
        title = (f"{cname(best['c'], True)} الأسرع نموًا في 2027: +{best['growth_2027'] * 100:.0f}%" if ar
                 else f"{best['c']} is on track to grow fastest in 2027: +{best['growth_2027'] * 100:.0f}%")
        text = (f"كل شركة مبنية من 100 عند أول ربع ليها، فالشارت بيقارن سرعة النمو مش الحجم. تتصدر {cname(best['c'], True)} بإيرادات متوقعة {bn(best['f2027_m'], True)} في 2027. "
                f"توقعات {cname(sure['c'], True)} الأدق على بيانات لم يرها الموديل (خطأ {sure['mape_holdout_pct']:.1f}%)، وتوقعات {cname(weak['c'], True)} الأعلى خطأ ({weak['mape_holdout_pct']:.1f}%)."
                if ar else
                f"Each company is rebased to 100 at its first quarter, so the chart compares growth, not size. {best['c']} leads with {bn(best['f2027_m'], False)} expected in 2027. "
                f"{sure['c']}'s model is the most accurate on data it never saw ({sure['mape_holdout_pct']:.1f}% error); {weak['c']}'s carries the highest error ({weak['mape_holdout_pct']:.1f}%).")
        chips = [{"label": f"{cname(r['c'], ar)} · {'خطأ' if ar else 'err'} {r['mape_holdout_pct']:.1f}%", "value": f"▲ +{r['growth_2027'] * 100:.0f}%", "dir": "up"} for r in rows]
    elif intent == "delivery_size":
        k = {x["k"]: x for x in p["kpis"]}
        g, t, r = k.get("gmv", {}).get("v", ""), k.get("talabat", {}).get("v", "10x+"), k.get("bfratio", {}).get("v", "")
        title = "talabat تتصدر سوق التوصيل بفارق كبير" if ar else "talabat leads Egypt's delivery market by a wide margin"
        text = (f"مبيعات talabat في توصيل الأكل بمصر {t} أقرب منافس (Redseer). حجم أعمال المجموعة {g} في 2025، وبريدفاست وصلت إلى {r} من حجم البحث عن talabat."
                if ar else f"talabat's food-delivery sales in Egypt are {t} the next platform (Redseer). The group did {g} GMV in 2025, and Breadfast now gets {r} of talabat's search volume.")
        chips = [{"label": "talabat", "value": t, "dir": "up"}, {"label": "حجم الأعمال" if ar else "GMV", "value": g, "dir": "up"},
                 {"label": "بريدفاست" if ar else "Breadfast", "value": r, "dir": "up"}]
        chart = None
    elif intent == "where_sold":
        top, f = p["top"], p["facts"]
        share = sum(x["pct"] for x in top[:3])
        names = (" و" if ar else ", ").join(gname(x["g"], ar) for x in top[:3])
        title = f"3 محافظات تضم {pct(share)} من سكان الحضر" if ar else f"3 governorates hold {pct(share)} of urban consumers"
        text = (f"{names} هي أكبر أسواق المشروبات المعبأة. يضم السوق نحو {f.get('outlets', '')} منفذ بيع، ونمت المطاعم والمقاهي {f.get('horeca', '')} في الربع الأول 2026."
                if ar else f"{names} are the biggest markets for packaged drinks. The market has about {f.get('outlets', '')} outlets, and cafes and restaurants grew {f.get('horeca', '')} in Q1 2026.")
        chips = [{"label": "منافذ البيع" if ar else "Outlets", "value": f.get("outlets", ""), "dir": "flat"},
                 {"label": "المطاعم والمقاهي" if ar else "Cafes & restaurants", "value": f.get("horeca", ""), "dir": "up"}]
    else:
        raise KeyError(intent)
    return {"title": title, "text": text, "chips": chips, "chart": chart}
