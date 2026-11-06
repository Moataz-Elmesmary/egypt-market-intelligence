"""The 7 tools. Each one runs DAX against the open Power BI model and returns a few compact rows.

The same functions serve the instant router, the Gemini tool-calling loop and the MCP server, so
every route reads the model the same way. Every DAX statement a call runs is recorded on the call.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable

from model import MODEL

COMPANY_AR = {"Juhayna": "جهينة", "Edita": "إيديتا", "Obour Land": "عبور لاند", "Domty": "دومتي"}
CATEGORIES = ("Soft drinks", "Delivery apps")
SOURCE = {
    "search_share": "Google Trends, Egypt 2021–2026",
    "search_trend": "Google Trends, Egypt 2021–2026",
    "company_financials": "EGX filings via StockAnalysis; USD/EGP yearly averages",
    "forecast": "EGX filings; 6-model statsmodels ensemble, rolling-origin backtest",
    "get_kpis": "KPI table (talabat, Coca-Cola HBC, CAPMAS)",
    "where_sold": "CAPMAS via Wikipedia; Coca-Cola HBC Egypt",
    "sources": "Sources table",
}


@dataclass
class Call:
    tool: str
    args: dict
    dax: list[str] = field(default_factory=list)
    rows: int = 0
    ms: float = 0.0
    result: Any = None
    error: str | None = None


def s(v: str) -> str:
    return '"' + str(v).replace('"', '""') + '"'


def lst(vals) -> str:
    return "{ " + ", ".join(s(v) for v in vals) + " }"


class Runner:
    def __init__(self, call: Call):
        self.call = call

    def q(self, dax: str) -> list[dict]:
        rows, ms = MODEL.query(dax)
        self.call.dax.append(dax.strip())
        self.call.rows += len(rows)
        self.call.ms += ms
        return rows


# ---------------------------------------------------------------- catalog (names the router and tools accept)
@lru_cache(maxsize=1)
def catalog() -> dict:
    c = Call("catalog", {})
    r = Runner(c)
    brands = r.q("EVALUATE SELECTCOLUMNS ( 'Brand', \"Brand\", 'Brand'[Brand], \"AR\", 'Brand'[BrandAR], \"Category\", 'Brand'[Category], \"Color\", 'Brand'[Color] )")
    govs = r.q("EVALUATE SELECTCOLUMNS ( 'Governorate', \"Code\", 'Governorate'[GovCode], \"EN\", 'Governorate'[Governorate], \"AR\", 'Governorate'[GovernorateAR] )")
    comps = r.q("EVALUATE DISTINCT ( SELECTCOLUMNS ( 'Revenue_FY', \"Company\", 'Revenue_FY'[Company] ) )")
    return {
        "brands": {b["Brand"]: b for b in brands},
        "govs": {g["Code"]: g for g in govs},
        "companies": sorted(x["Company"] for x in comps),
    }


def gov_code(name: str) -> str:
    n = str(name).strip().lower()
    for code, g in catalog()["govs"].items():
        if n in (code.lower(), str(g["EN"]).lower(), str(g["AR"])):
            return code
    raise ValueError(f"unknown governorate {name!r}; use an English name like 'Alexandria' or a code like 'EG-ALX'")


def check_brand(b: str) -> str:
    for k in catalog()["brands"]:
        if k.lower() == str(b).strip().lower():
            return k
    raise ValueError(f"unknown brand {b!r}; known: {', '.join(catalog()['brands'])}")


def check_company(c: str) -> str:
    for k in catalog()["companies"]:
        if k.lower() == str(c).strip().lower():
            return k
    raise ValueError(f"unknown company {c!r}; known: {', '.join(catalog()['companies'])}")


def check_category(c: str) -> str:
    for k in CATEGORIES:
        if k.lower() == str(c).strip().lower():
            return k
    raise ValueError(f"unknown category {c!r}; use 'Soft drinks' or 'Delivery apps'")


# ---------------------------------------------------------------- tools
def search_share(r: Runner, category: str = "", governorate: str = "", brand: str = "", top_n: int = 5) -> dict:
    if governorate:
        code = gov_code(governorate)
        cat = check_category(category or "Soft drinks")
        rows = r.q(f"""EVALUATE
SUMMARIZECOLUMNS ( 'Brand'[Brand], TREATAS ( {{ {s(code)} }}, 'Governorate'[GovCode] ), TREATAS ( {{ {s(cat)} }}, 'Brand'[Category] ), "Share", [Geo Share] )
ORDER BY [Share] DESC""")
        rows = [x for x in rows if (x["Share"] or 0) > 0][:max(1, int(top_n))]
        return {"governorate": code, "category": cat, "brands": [{"b": x["Brand"], "s": round(x["Share"], 4)} for x in rows]}
    if brand:
        b = check_brand(brand)
        rows = r.q(f"""EVALUATE
SUMMARIZECOLUMNS ( 'Governorate'[GovCode], TREATAS ( {{ {s(b)} }}, 'Brand'[Brand] ), "Share", [Geo Share] )
ORDER BY [Share] DESC""")
        vals = sorted(x["Share"] or 0 for x in rows)
        med = vals[len(vals) // 2] if len(vals) % 2 else (vals[len(vals) // 2 - 1] + vals[len(vals) // 2]) / 2
        return {"brand": b, "median_share": round(med, 4), "governorates": len(rows),
                "top": [{"g": x["GovCode"], "s": round(x["Share"], 4)} for x in rows[:max(1, int(top_n))]]}
    cat = check_category(category or "Soft drinks")
    rows = r.q(f"""EVALUATE
SUMMARIZECOLUMNS ( 'Brand'[Brand], TREATAS ( {{ {s(cat)} }}, 'Brand'[Category] ), "Share", [Share of Search] )
ORDER BY [Share] DESC""")
    return {"category": cat, "national_last_12m": [{"b": x["Brand"], "s": round(x["Share"], 4)} for x in rows[:max(1, int(top_n))]]}


def search_trend(r: Runner, brands: list[str] | None = None, category: str = "", start: str = "2021-01", end: str = "2026-12",
                 every: int = 1, compare: bool = False) -> dict:
    if compare:
        cat = check_category(category or "Soft drinks")
        rows = r.q(f"""EVALUATE
SUMMARIZECOLUMNS ( 'Brand'[Brand], TREATAS ( {{ {s(cat)} }}, 'Brand'[Category] ),
    "First12", [Interest 2021], "Last12", [Interest Last 12M], "Share", [Share of Search] )
ORDER BY [Share] DESC""")
        out = []
        for x in rows:
            a, z = x["First12"] or 0, x["Last12"] or 0
            ratio = None if a <= 0.05 else round(z / a, 3)
            out.append({"b": x["Brand"], "avg_2021": round(a, 2), "avg_last_12m": round(z, 2), "ratio": ratio,
                        "new_since_2021": a <= 0.05 and z > 0.05, "share": round(x["Share"] or 0, 4)})
        return {"category": cat, "compare": "2021 average vs last 12 months average", "brands": out}
    bs = [check_brand(b) for b in (brands or [])[:5]]
    if not bs:
        raise ValueError("pass up to 5 brands, or compare=true with a category")
    y0, m0 = (int(p) for p in start[:7].split("-"))
    y1, m1 = (int(p) for p in end[:7].split("-"))
    rows = r.q(f"""EVALUATE
SUMMARIZECOLUMNS ( 'Months'[Month], 'Brand'[Brand], TREATAS ( {lst(bs)}, 'Brand'[Brand] ),
    FILTER ( ALL ( 'Months'[Month] ), 'Months'[Month] >= DATE ( {y0}, {m0}, 1 ) && 'Months'[Month] <= EOMONTH ( DATE ( {y1}, {m1}, 1 ), 0 ) ),
    "Interest", [Search Interest], "Last12", [Interest Last 12M] )
ORDER BY 'Brand'[Brand], 'Months'[Month]""")
    series: dict[str, list] = {}
    last12: dict[str, float] = {}
    for x in rows:
        series.setdefault(x["Brand"], []).append([x["Month"][:7], x["Interest"]])
    for b in bs:
        lr = r.q(f"EVALUATE ROW ( \"v\", CALCULATE ( [Interest Last 12M], 'Brand'[Brand] = {s(b)} ) )")
        last12[b] = round(lr[0]["v"] or 0, 2)
    step = max(1, int(every))
    return {"series": {b: pts[::step] for b, pts in series.items()}, "avg_last_12m": last12,
            "peak": {b: max(pts, key=lambda p: p[1] or 0) for b, pts in series.items() if pts}}


def company_financials(r: Runner, company: str = "Juhayna", unit: str = "EGP") -> dict:
    c = check_company(company)
    rows = r.q(f"""EVALUATE
SUMMARIZECOLUMNS ( 'Revenue_FY'[Year], 'Revenue_FY'[Basis], TREATAS ( {{ {s(c)} }}, 'Revenue_FY'[Company] ),
    "EGP_M", SUM ( 'Revenue_FY'[RevenueEGP] ), "USD_M", SUM ( 'Revenue_FY'[RevenueUSD] ), "FX", AVERAGE ( 'Revenue_FY'[FX] ) )
ORDER BY 'Revenue_FY'[Year]""")
    return {"company": c, "unit_asked": unit.upper(), "years": [
        {"y": int(x["Year"]), "egp_m": round(x["EGP_M"]), "usd_m": round(x["USD_M"], 1), "fx": round(x["FX"], 2), "basis": x["Basis"]} for x in rows]}


def forecast(r: Runner, company: str = "Juhayna", horizon: int = 6) -> dict:
    if str(company).lower() == "all":
        fy = r.q("""EVALUATE
SUMMARIZECOLUMNS ( 'Revenue_FY'[Company],
    "F2026", CALCULATE ( SUM ( 'Revenue_FY'[RevenueEGP] ), 'Revenue_FY'[Year] = 2026 ),
    "F2027", CALCULATE ( SUM ( 'Revenue_FY'[RevenueEGP] ), 'Revenue_FY'[Year] = 2027 ) )""")
        mp = r.q("""EVALUATE
SELECTCOLUMNS ( FILTER ( 'Models', LEFT ( 'Models'[Model], 8 ) = "Ensemble" ), "Company", 'Models'[Company], "MAPE", 'Models'[MAPE_Holdout] )""")
        q = r.q("""EVALUATE
SUMMARIZECOLUMNS ( 'Revenue_Q'[Company], 'Revenue_Q'[Quarter], "Actual", SUM ( 'Revenue_Q'[RevenueEGP] ), "Forecast", SUM ( 'Revenue_Q'[ForecastEGP] ) )
ORDER BY 'Revenue_Q'[Company], 'Revenue_Q'[Quarter]""")
        mape = {x["Company"]: x["MAPE"] for x in mp}
        idx: dict[str, list] = {}
        for x in q:
            v = x["Actual"] if x["Actual"] is not None else x["Forecast"]
            if v is not None:
                idx.setdefault(x["Company"], []).append([x["Quarter"], v])
        comps = []
        for x in fy:
            pts = idx.get(x["Company"], [])
            base = pts[0][1] if pts else 1
            comps.append({"c": x["Company"], "f2026_m": round(x["F2026"]), "f2027_m": round(x["F2027"]),
                          "growth_2027": round(x["F2027"] / x["F2026"] - 1, 4), "mape_holdout_pct": round(mape.get(x["Company"], 0), 2),
                          "indexed": [[p, round(v / base * 100, 1)] for p, v in pts]})
        comps.sort(key=lambda z: -z["growth_2027"])
        return {"companies": comps, "index_base": "first quarter = 100"}
    c = check_company(company)
    q = r.q(f"""EVALUATE
SUMMARIZECOLUMNS ( 'Revenue_Q'[Quarter], TREATAS ( {{ {s(c)} }}, 'Revenue_Q'[Company] ),
    "Actual", SUM ( 'Revenue_Q'[RevenueEGP] ), "Forecast", SUM ( 'Revenue_Q'[ForecastEGP] ),
    "Lo80", SUM ( 'Revenue_Q'[Lo80] ), "Hi80", SUM ( 'Revenue_Q'[Hi80] ), "Backtest", SUM ( 'Revenue_Q'[BacktestEGP] ) )
ORDER BY 'Revenue_Q'[Quarter]""")
    models = r.q(f"""EVALUATE
SELECTCOLUMNS ( FILTER ( 'Models', 'Models'[Company] = {s(c)} ),
    "Model", 'Models'[Model], "MAPE_Holdout", 'Models'[MAPE_Holdout], "MAPE_Select", 'Models'[MAPE_Select], "Weight", 'Models'[Weight] )
ORDER BY [MAPE_Holdout]""")
    fy = r.q(f"""EVALUATE
SUMMARIZECOLUMNS ( 'Revenue_FY'[Year], TREATAS ( {{ {s(c)} }}, 'Revenue_FY'[Company] ), "EGP_M", SUM ( 'Revenue_FY'[RevenueEGP] ) )
ORDER BY 'Revenue_FY'[Year]""")
    ens = next((m for m in models if str(m["Model"]).startswith("Ensemble")), None)
    singles = [m for m in models if not str(m["Model"]).startswith("Ensemble")]
    dx = r.q(f"""EVALUATE
SELECTCOLUMNS ( FILTER ( 'Company', 'Company'[Company] = {s(c)} ),
    "RealGrowth2027", 'Company'[RealGrowth2027], "Growth2027", 'Company'[Growth2027], "Low", 'Company'[Forecast2027Low],
    "High", 'Company'[Forecast2027High], "MASE", 'Company'[MASE], "CovIn", 'Company'[CoverageIn], "CovN", 'Company'[CoverageN],
    "BtNominal", 'Company'[BacktestMAPE], "BtReal", 'Company'[RealMethodMAPE] )""")[0]
    return {
        "company": c,
        "actual": [[x["Quarter"], round(x["Actual"])] for x in q if x["Actual"] is not None][-8:],
        "forecast": [{"q": x["Quarter"], "f": round(x["Forecast"]), "lo80": round(x["Lo80"]), "hi80": round(x["Hi80"])}
                     for x in q if x["Forecast"] is not None][:max(1, int(horizon))],
        "fy_egp_m": {int(x["Year"]): round(x["EGP_M"]) for x in fy},
        "ensemble_mape_holdout_pct": round(ens["MAPE_Holdout"], 2) if ens else None,
        "models": [{"m": m["Model"], "mape_holdout_pct": round(m["MAPE_Holdout"], 2), "weight": round(m["Weight"] or 0, 3)} for m in singles],
        "growth_2027_pct": round(dx["Growth2027"] * 100, 1),
        "real_growth_2027_pct": round(dx["RealGrowth2027"] * 100, 1),
        "inflation_scenarios_2027_egp_m": {"low_9pct": round(dx["Low"]), "base_13_9pct": round(fy and {int(x["Year"]): x["EGP_M"] for x in fy}.get(2027, 0)),
                                           "high_20pct": round(dx["High"])},
        "mase": round(dx["MASE"], 2),
        "band_80_held": f"{dx['CovIn']} of {dx['CovN']} backtest quarters",
        "backtest_mape_pct": {"pound_ensemble": round(dx["BtNominal"], 2), "inflation_adjusted_method": round(dx["BtReal"], 2)},
    }


def get_kpis(r: Runner, page: str = "overview") -> dict:
    rows = r.q(f"""EVALUATE
SELECTCOLUMNS ( FILTER ( 'KPI', 'KPI'[Page] = {s(page)} ),
    "Key", 'KPI'[Key], "Label", 'KPI'[Label], "Value", 'KPI'[Value], "Display", 'KPI'[Display], "Note", 'KPI'[Sub], "Source", 'KPI'[Source] )
ORDER BY [Key]""")
    return {"page": page, "kpis": [{"k": x["Key"], "m": x["Label"], "v": x["Display"], "note": x["Note"], "src": x["Source"]} for x in rows]}


def where_sold(r: Runner, top_n: int = 6) -> dict:
    rows = r.q(f"""EVALUATE
TOPN ( {max(1, int(top_n))}, SELECTCOLUMNS ( 'Governorate', "Code", 'Governorate'[GovCode], "UrbanPop", 'Governorate'[UrbanPop] ), [UrbanPop], DESC )
ORDER BY [UrbanPop] DESC""")
    tot = r.q("EVALUATE ROW ( \"Total\", SUM ( 'Governorate'[UrbanPop] ) )")[0]["Total"]
    facts = r.q("""EVALUATE
SELECTCOLUMNS ( FILTER ( 'KPI', 'KPI'[Page] = "where" ), "Key", 'KPI'[Key], "Display", 'KPI'[Display] )""")
    return {"top": [{"g": x["Code"], "urban_m": round(x["UrbanPop"] / 1e6, 2), "pct": round(x["UrbanPop"] / tot, 4)} for x in rows],
            "urban_total_m": round(tot / 1e6, 2), "facts": {x["Key"]: x["Display"] for x in facts}}


def sources(r: Runner, ids: list[str] | None = None) -> dict:
    flt = f"FILTER ( 'Sources', 'Sources'[Id] IN {lst(ids)} )" if ids else "'Sources'"
    rows = r.q(f"EVALUATE SELECTCOLUMNS ( {flt}, \"Id\", 'Sources'[Id], \"Title\", 'Sources'[Title], \"URL\", 'Sources'[URL] )")
    return {"sources": [{"id": x["Id"], "t": x["Title"], "url": x["URL"]} for x in rows]}


TOOLS: dict[str, Callable] = {f.__name__: f for f in (search_share, search_trend, company_financials, forecast, get_kpis, where_sold, sources)}


def run(tool: str, args: dict) -> Call:
    call = Call(tool, dict(args or {}))
    t0 = time.perf_counter()
    try:
        call.result = TOOLS[tool](Runner(call), **call.args)
    except (ValueError, TypeError, KeyError) as exc:  # bad arguments: the model gets the reason and can retry
        call.error = str(exc)
    call.ms = round((time.perf_counter() - t0) * 1000, 1)
    return call


# Function declarations for Gemini (the MCP server exposes the same functions).
DECLARATIONS = [
    {"name": "search_share", "description": "Google search share in Egypt (attention, not sales). With governorate: each brand's share there in a category. "
     "With brand: that brand's strongest governorates and its median share. Neither: national share over the last 12 months.",
     "parameters": {"type": "object", "properties": {
         "category": {"type": "string", "enum": list(CATEGORIES)},
         "governorate": {"type": "string", "description": "English name or code, e.g. Alexandria or EG-ALX"},
         "brand": {"type": "string", "description": "Pepsi, Coca-Cola, Spiro Spathis, Big Cola, V7 Cola, talabat, Breadfast, instashop, elmenus, Rabbit"},
         "top_n": {"type": "integer"}}}},
    {"name": "search_trend", "description": "Monthly Google Trends interest (0-100), Jan 2021 to Oct 2026. Pass brands for series, or compare=true with a "
     "category to get each brand's 2021 average vs last-12-months average (who is growing or falling).",
     "parameters": {"type": "object", "properties": {
         "brands": {"type": "array", "items": {"type": "string"}}, "category": {"type": "string", "enum": list(CATEGORIES)},
         "start": {"type": "string", "description": "YYYY-MM"}, "end": {"type": "string", "description": "YYYY-MM"},
         "every": {"type": "integer", "description": "keep every Nth month"}, "compare": {"type": "boolean"}}}},
    {"name": "company_financials", "description": "Annual revenue of an EGX-listed food maker (Juhayna, Edita, Obour Land, Domty) in EGP millions and "
     "USD millions at each year's average rate. 2026 = 2 actual + 2 forecast quarters, 2027 = forecast. Revenue only: no profit or margin data.",
     "parameters": {"type": "object", "properties": {"company": {"type": "string"}, "unit": {"type": "string", "enum": ["EGP", "USD"]}}, "required": ["company"]}},
    {"name": "forecast", "description": "Quarterly revenue forecast (EGP millions) with 80% band from a 6-model rolling-origin ensemble, the ensemble's error "
     "on 4 unseen quarters, each model's error and weight, 2027 growth in pounds and after inflation (real), 2027 revenue under 9% / 13.9% / 20% "
     "inflation scenarios, MASE, how often the 80% band held, and the backtest error of the pound vs inflation-adjusted method. "
     "company='all' compares 2027 growth and accuracy across the four companies.",
     "parameters": {"type": "object", "properties": {"company": {"type": "string"}, "horizon": {"type": "integer"}}, "required": ["company"]}},
    {"name": "get_kpis", "description": "Headline numbers with sources for a report page: overview, where, delivery or forecast.",
     "parameters": {"type": "object", "properties": {"page": {"type": "string", "enum": ["overview", "where", "delivery", "forecast"]}}, "required": ["page"]}},
    {"name": "where_sold", "description": "Where packaged drinks sell: governorates with the most urban consumers (CAPMAS) plus channel facts (outlets, entry price, cafes growth).",
     "parameters": {"type": "object", "properties": {"top_n": {"type": "integer"}}}},
    {"name": "sources", "description": "Source list behind the numbers (ids like S1, S9). Empty = all.",
     "parameters": {"type": "object", "properties": {"ids": {"type": "array", "items": {"type": "string"}}}}},
]
