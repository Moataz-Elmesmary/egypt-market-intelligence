"""Egypt Market Intelligence: builds the Excel model Power BI reads, plus a JSON copy for the MCP server.

Sources are public (see SOURCES). Google Trends pulls live in raw/google_trends_eg.json.
Run: python egypt/build_egypt_data.py
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import forecast_models as fc  # noqa: E402  (6 models, rolling-origin backtest, top-3 ensemble)

OUT = HERE / "data"
XLSX = OUT / "Egypt_Market_Intelligence_2026.xlsx"

SOURCES = {
    "S1": ("Google Trends, Egypt, monthly 2021-01 to 2026-10 (pulled 2026-10-30)", "https://trends.google.com/trends/explore?geo=EG"),
    "S2": ("CAPMAS governorate population, Nov 2023 estimate (via Wikipedia, Governorates of Egypt)", "https://en.wikipedia.org/wiki/Governorates_of_Egypt"),
    "S3": ("CAPMAS urban share by governorate, 2016 (via Wikipedia)", "https://en.wikipedia.org/wiki/Governorates_of_Egypt"),
    "S4": ("CAPMAS: domestic population reaches 109.5 million (Egypt Today, 2026)", "https://www.egypttoday.com/Article/1/149579/Egypt%E2%80%99s-domestic-population-reaches-109-5-Million-CAPMAS"),
    "S5": ("Coca-Cola HBC, Bitesize investor series: Egypt, transcript (7 Jul 2026)", "https://www.coca-colahellenic.com/content/dam/cch/us/documents/investors-and-financial/results-reports-and-presentations/2026/Coca-Cola-HBC-bitesize-egypt-transcript-july726.pdf"),
    "S6": ("talabat Investor Presentation (14 May 2026), Redseer category shares", "https://ir.talabat.com/wp-content/uploads/2026/06/20260514_talabat-Investor-Presentation.pdf"),
    "S7": ("talabat FY2025 results: GMV $9.5bn (+28% cFX), revenue $3.9bn (TradeArabia)", "https://www.tradearabia.com/News/389296/Talabat-posts-28_Percent-GMV-growth-in-2025-sets-$100m-for-expansion"),
    "S8": ("talabat H1 2025 results: non-GCC 17% of GMV (Aug 2025)", "https://corporate.talabat.com/news/corporate-website-news-item-8/"),
    "S9": ("Quarterly income statements: Juhayna (JUFO), Edita (EFID), Obour Land (OLFI), Domty (DOMT), EGX filings via StockAnalysis", "https://stockanalysis.com/quote/egx/JUFO/financials/income-statement/?p=quarterly"),
    "S10": ("Juhayna H1 2026 consolidated sales +25% to EGP 17.68bn (Zawya)", "https://www.zawya.com/en/capital-markets/equities/egypt-juhayna-records-23-yoy-rise-in-h1-2026-consolidated-profits-421669"),
    "S11": ("USD/EGP annual average rates (TradersUnion tracker)", "https://tradersunion.com/currencies/price-history/usd-egp/"),
    "S12": ("CAPMAS urban inflation 13.9% in Sep 2026 (Daily News Egypt)", "https://www.dailynewsegypt.com/2026/10/10/egypts-annual-urban-inflation-eases-to-13-9-in-september/"),
    "S13": ("Reuters via Arab News: Coke and Pepsi boycott lifts local sodas (V7, Spiro Spathis)", "https://www.arabnews.com/node/2570049/amp"),
    "S14": ("Breadfast raises $50m pre-Series C (allAfrica, Feb 2026)", "https://fr.allafrica.com/stories/202602200319.html"),
    "S15": ("talabat Integrated Annual Report 2024 (instashop acquisition)", "https://ir.talabat.com/wp-content/uploads/2025/04/20250404_Talabat-Annual-Report-2024-En.pdf"),
    "S16": ("geoBoundaries EGY ADM1 (CC BY 4.0)", "https://www.geoboundaries.org/"),
}

CATS = {"Soft drinks": "مشروبات غازية", "Delivery apps": "تطبيقات التوصيل"}

# brand, Arabic, category, company, origin, color, shape, sort
BRANDS = [
    ("Pepsi", "بيبسي", "Soft drinks", "PepsiCo", "Global", "#1E4FB8", "can", 1),
    ("Coca-Cola", "كوكاكولا", "Soft drinks", "Coca-Cola HBC Egypt", "Global", "#D7262F", "can", 2),
    ("Spiro Spathis", "سبيرو سباتس", "Soft drinks", "Spiro Spathis (est. Cairo 1920)", "Egyptian", "#2E8B57", "bottle", 3),
    ("Big Cola", "بيج كولا", "Soft drinks", "AJE Group", "Global", "#E08A16", "bottle", 4),
    ("V7 Cola", "في 7 كولا", "Soft drinks", "V7 (launched in Egypt Jul 2023)", "Egyptian", "#6A4BB5", "can", 5),
    ("talabat", "طلبات", "Delivery apps", "talabat Holding (DFM-listed)", "Regional", "#FF5A00", "app", 1),
    ("Breadfast", "بريدفاست", "Delivery apps", "Breadfast", "Egyptian", "#AA0082", "app", 2),
    ("instashop", "انستاشوب", "Delivery apps", "talabat (acquired 2025)", "Regional", "#ED037C", "app", 3),
    ("elmenus", "المنيوز", "Delivery apps", "elmenus", "Egyptian", "#F02A00", "app", 4),
    ("Rabbit", "رابيت", "Delivery apps", "Rabbit", "Egyptian", "#141414", "app", 5),
]
TREND_ORDER = {"cola": ["Pepsi", "Coca-Cola", "Spiro Spathis", "Big Cola", "V7 Cola"],
               "apps": ["talabat", "Breadfast", "Rabbit", "instashop", "elmenus"]}
TREND_CAT = {"cola": "Soft drinks", "apps": "Delivery apps"}
# report palette for the native pages: the leader teal, the main rival gold, the rest in quiet tints (no brand rainbow)
TONE = {"Pepsi": "#0B6E69", "Coca-Cola": "#C2922F", "Spiro Spathis": "#7FB8B3", "Big Cola": "#B5AA95", "V7 Cola": "#DDD3C1",
        "talabat": "#0B6E69", "Breadfast": "#C2922F", "Rabbit": "#7FB8B3", "instashop": "#B5AA95", "elmenus": "#DDD3C1"}

# code, English, Arabic, CAPMAS region, population Nov-2023, urban % 2016
GOVS = [
    ("EG-C", "Cairo", "القاهرة", "Urban", 10456284, 100.0),
    ("EG-ALX", "Alexandria", "الإسكندرية", "Urban", 5703824, 98.8),
    ("EG-PTS", "Port Said", "بورسعيد", "Urban", 835193, 100.0),
    ("EG-SUZ", "Suez", "السويس", "Urban", 843385, 100.0),
    ("EG-DT", "Damietta", "دمياط", "Lower Egypt", 2023380, 38.7),
    ("EG-DK", "Dakahlia", "الدقهلية", "Lower Egypt", 7058212, 28.2),
    ("EG-SHR", "Sharqia", "الشرقية", "Lower Egypt", 8032683, 23.1),
    ("EG-KB", "Qalyubia", "القليوبية", "Lower Egypt", 6137896, 44.7),
    ("EG-KFS", "Kafr El Sheikh", "كفر الشيخ", "Lower Egypt", 3731540, 23.1),
    ("EG-GH", "Gharbia", "الغربية", "Lower Egypt", 5483000, 30.0),
    ("EG-MNF", "Monufia", "المنوفية", "Lower Egypt", 4743341, 20.6),
    ("EG-BH", "Beheira", "البحيرة", "Lower Egypt", 6940234, 19.5),
    ("EG-IS", "Ismailia", "الإسماعيلية", "Lower Egypt", 1482999, 45.4),
    ("EG-GZ", "Giza", "الجيزة", "Upper Egypt", 9534283, 58.6),
    ("EG-BNS", "Beni Suef", "بني سويف", "Upper Egypt", 3618395, 23.2),
    ("EG-FYM", "Faiyum", "الفيوم", "Upper Egypt", 4141222, 22.5),
    ("EG-MN", "Minya", "المنيا", "Upper Egypt", 6332918, 18.9),
    ("EG-AST", "Asyut", "أسيوط", "Upper Egypt", 5071485, 26.5),
    ("EG-SHG", "Sohag", "سوهاج", "Upper Egypt", 5714903, 21.4),
    ("EG-KN", "Qena", "قنا", "Upper Egypt", 3651215, 19.7),
    ("EG-ASN", "Aswan", "أسوان", "Upper Egypt", 1698201, 42.3),
    ("EG-LX", "Luxor", "الأقصر", "Upper Egypt", 1429385, 37.8),
    ("EG-BA", "Red Sea", "البحر الأحمر", "Frontier", 409394, 95.1),
    ("EG-WAD", "New Valley", "الوادي الجديد", "Frontier", 324600, 48.0),
    ("EG-MT", "Matrouh", "مطروح", "Frontier", 580304, 70.6),
    ("EG-SIN", "North Sinai", "شمال سيناء", "Frontier", 544494, 60.2),
    ("EG-JS", "South Sinai", "جنوب سيناء", "Frontier", 145934, 51.1),
]
REGION_AR = {"Urban": "المحافظات الحضرية", "Lower Egypt": "الوجه البحري", "Upper Egypt": "الوجه القبلي", "Frontier": "المحافظات الحدودية"}

# Quarterly revenue, EGP millions, quarter ends 2021Q3..2026Q2 (S9). name: (Arabic, ticker, segment, segment AR, revenue)
COMPANIES = {
    "Juhayna": ("جهينة", "JUFO", "Dairy & juice", "ألبان وعصائر",
                [2435, 2282, 2403, 2761, 2996, 3203, 3246, 3554, 4371, 4365, 5435, 6036, 6864, 5969, 6803, 7362, 7972, 7848, 8600, 9078]),
    "Edita": ("إيديتا", "EFID", "Snacks & bakery", "مخبوزات وسناكس",
              [1395, 1539, 1559, 1573, 2016, 2523, 2780, 2858, 3116, 3372, 3927, 4062, 3912, 4245, 4283, 4964, 5493, 6175, 5770, 6480]),
    "Obour Land": ("عبور لاند", "OLFI", "Cheese", "أجبان",
                   [820, 883.69, 923.8, 873.87, 1343, 1420, 1470, 1486, 2050, 2196, 1750, 2084, 2838, 2794, 2552, 2505, 3181, 2879, 2959, 3084]),
    "Domty": ("دومتي", "DOMT", "Cheese & juice", "أجبان وعصائر",
              [956.09, 1087, 1122, 1152, 1319, 1490, 1699, 1533, 1948, 2325, 2282, 2064, 2544, 2336, 2252, 2004, 2723, 2412, 2559, 2827]),
}
FX = {2021: 15.65, 2022: 19.18, 2023: 30.65, 2024: 45.36, 2025: 49.25, 2026: 50.35}  # EGP per USD, annual avg (S11; 2026 = YTD)

MONTH_EVENTS = {  # month: (category, English, Arabic)
    "2023-10": ("cola", "Boycott of Western sodas begins", "بداية مقاطعة المشروبات الغربية"),
    "2025-02": ("apps", "talabat closes instashop deal", "طلبات تستحوذ على انستاشوب"),
    "2026-02": ("apps", "Breadfast raises $50M", "بريدفاست تجمع 50 مليون دولار"),
}


def parse_trends():
    raw = json.loads((HERE / "raw" / "google_trends_eg.json").read_text(encoding="utf-8"))
    trend, geo = [], []
    for key, names in TREND_ORDER.items():
        for tok in raw[key]["ts"].split():
            mon, vals = tok.split(":")
            month = pd.to_datetime(mon, format="%b-%Y")
            for name, v in zip(names, vals.split("/")):
                trend.append(dict(Month=month, Brand=name, Category=TREND_CAT[key], Interest=int(v)))
        for tok in raw[key]["geo"].split():
            code, vals = tok.split(":")
            for name, v in zip(names, vals.split("/")):
                geo.append(dict(GovCode=code, Brand=name, Category=TREND_CAT[key], Share=int(v) / 100))
    trend = pd.DataFrame(trend)
    last = trend["Month"].max()
    trend["Last12M"] = trend["Month"] > last - pd.DateOffset(months=12)
    return trend, pd.DataFrame(geo)


def centroids():
    g = json.loads((HERE / "raw" / "egy_adm1.geojson").read_text(encoding="utf-8"))
    out = {}
    for f in g["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        best, area_best = None, -1
        for poly in polys:
            ring = np.asarray(poly[0])
            x, y = ring[:, 0], ring[:, 1]
            a = 0.5 * np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])
            if abs(a) > area_best:
                cx = np.sum((x[:-1] + x[1:]) * (x[:-1] * y[1:] - x[1:] * y[:-1])) / (6 * a)
                cy = np.sum((y[:-1] + y[1:]) * (x[:-1] * y[1:] - x[1:] * y[:-1])) / (6 * a)
                best, area_best = (round(float(cy), 3), round(float(cx), 3)), abs(a)
        out[f["properties"]["shapeISO"]] = best
    return out


def share_last12(trend, cat):
    t = trend[(trend.Category == cat) & trend.Last12M].groupby("Brand")["Interest"].mean()
    return (t / t.sum()).to_dict()


def build():
    OUT.mkdir(exist_ok=True)
    trend, geo = parse_trends()
    cent = centroids()

    brand = pd.DataFrame(BRANDS, columns=["Brand", "BrandAR", "Category", "Company", "Origin", "Color", "Shape", "Sort"])
    brand["CategoryAR"] = brand.Category.map(CATS)
    brand["CategorySort"] = brand.Category.map({"Soft drinks": 1, "Delivery apps": 2})
    brand["Tone"] = brand.Brand.map(TONE)
    sos = {**share_last12(trend, "Soft drinks"), **share_last12(trend, "Delivery apps")}
    first12 = trend[trend.Month < "2022-01-01"].groupby("Brand")["Interest"].mean()
    last12 = trend[trend.Last12M].groupby("Brand")["Interest"].mean()
    brand["ShareOfSearch12M"] = brand.Brand.map(sos).round(4)
    brand["Interest2021"] = brand.Brand.map(first12).round(2)
    brand["InterestLast12M"] = brand.Brand.map(last12).round(2)

    gov = pd.DataFrame(GOVS, columns=["GovCode", "Governorate", "GovernorateAR", "Region", "Population", "UrbanPct"])
    gov["RegionAR"] = gov.Region.map(REGION_AR)
    gov["UrbanPop"] = (gov.Population * gov.UrbanPct / 100).round(0)
    gov["Lat"] = gov.GovCode.map(lambda c: cent[c][0])
    gov["Lon"] = gov.GovCode.map(lambda c: cent[c][1])

    months = pd.DataFrame({"Month": sorted(trend.Month.unique())})
    months["MonthLabel"] = months.Month.dt.strftime("%b %Y")
    months["Year"] = months.Month.dt.year
    key = months.Month.dt.strftime("%Y-%m")
    for cat, col in (("cola", "EventCola"), ("apps", "EventApps")):
        months[col] = key.map(lambda k: MONTH_EVENTS[k][1] if k in MONTH_EVENTS and MONTH_EVENTS[k][0] == cat else "")
        months[col + "AR"] = key.map(lambda k: MONTH_EVENTS[k][2] if k in MONTH_EVENTS and MONTH_EVENTS[k][0] == cat else "")

    # Forecast: the same 6-model rolling-origin ensemble, run for each listed food maker
    parts, boards = [], []
    for name, (ar, tick, seg, seg_ar, q) in COMPANIES.items():
        rows, board = fc.run_forecast("2021Q3", q, H=6)
        d = pd.DataFrame(rows)
        d.insert(0, "Company", name)
        parts.append(d)
        b = pd.DataFrame(board)
        b.insert(0, "Company", name)
        boards.append(b)
    jq = pd.concat(parts, ignore_index=True)
    jq["QuarterEnd"] = pd.PeriodIndex(jq.quarter, freq="Q").to_timestamp(how="end").normalize()
    jq["Year"] = jq.QuarterEnd.dt.year
    jq["FX"] = jq.Year.map(lambda y: FX.get(y, FX[2026]))
    jq["ActualUSD"] = (jq.actual / jq.FX).round(1)
    jq["ForecastUSD"] = (jq.forecast / jq.FX).round(1)
    jq = jq.rename(columns={"quarter": "Quarter", "actual": "RevenueEGP", "forecast": "ForecastEGP",
                            "lo80": "Lo80", "hi80": "Hi80", "backtest": "BacktestEGP"})
    model_cols = list(fc.MODELS)
    jq = jq[["Company", "Quarter", "QuarterEnd", "Year", "RevenueEGP", "BacktestEGP", "ForecastEGP", "Lo80", "Hi80",
             "FX", "ActualUSD", "ForecastUSD"] + model_cols]
    lb = pd.concat(boards, ignore_index=True).rename(columns={"model": "Model", "mape_select": "MAPE_Select", "mape_holdout": "MAPE_Holdout", "weight": "Weight"})

    # inflation lens, scenarios and honest diagnostics (forecast_plus.py)
    import forecast_plus as FP
    hist_labs = sorted(jq[jq.RevenueEGP.notna()].Quarter.unique())
    fut_labs = sorted(q for q in jq.Quarter.unique() if q > hist_labs[-1])
    k_ahead = {q: i + 1 for i, q in enumerate(fut_labs)}
    base_rate = FP.SCENARIOS[1][1]
    cpi_q = dict(zip(hist_labs, FP.cpi(hist_labs)))
    cpi_q.update({q: cpi_q[hist_labs[-1]] * (1 + base_rate) ** (k / 4) for q, k in k_ahead.items()})
    jq["CPI"] = jq.Quarter.map(cpi_q).round(2)
    jq["RealEGP"] = (jq.RevenueEGP.fillna(jq.ForecastEGP) / jq.CPI * 100).round(1)
    jq["ForecastLow"] = (jq.ForecastEGP * jq.Quarter.map(lambda q: FP.scenario_factor(k_ahead.get(q, 0), FP.SCENARIOS[0][1]))).round(1)
    jq["ForecastHigh"] = (jq.ForecastEGP * jq.Quarter.map(lambda q: FP.scenario_factor(k_ahead.get(q, 0), FP.SCENARIOS[2][1]))).round(1)
    AN, bt_rows = {}, []
    for name, (_ar, _tick, _seg, _seg_ar, q) in COMPANIES.items():
        a = FP.analyse(fc.quarter_labels("2021Q3", len(q)), q)
        AN[name] = a
        bt_rows += [dict(Company=name, Origin=r["origin"], Horizon=r["horizon"], Quarter=r["quarter"], Actual=round(r["actual"]),
                         Forecast=round(r["nominal"]), Lo80=round(r["lo80"]), Hi80=round(r["hi80"]), Inside=int(r["inside"]),
                         APE=round(r["ape_nominal"], 4)) for r in a["backtest"]]
    backtest = pd.DataFrame(bt_rows)
    scenario = pd.DataFrame([dict(Scenario=n, Ord=i + 1, Inflation=r, FX2027=round(FP.fx_2027(FX[2026], r), 2), Note=note)
                             for i, (n, r, note) in enumerate(FP.SCENARIOS)])

    fyr = []
    for (comp, yr), g in jq.groupby(["Company", "Year"]):
        act, fut = g.RevenueEGP.notna().sum(), g.ForecastEGP.notna().sum()
        if act + fut < 4:
            continue
        v = float(g.RevenueEGP.fillna(0).sum() + g.ForecastEGP.fillna(0).sum())
        basis = "Actual" if fut == 0 else ("Forecast" if act == 0 else f"{act} actual + {fut} forecast quarters")
        fyr.append(dict(Company=comp, Year=int(yr), RevenueEGP=round(v), FX=FX.get(int(yr), FX[2026]), Basis=basis))
    fy = pd.DataFrame(fyr)
    fy["RevenueUSD"] = (fy.RevenueEGP / fy.FX).round(1)
    piv = fy.pivot(index="Year", columns="Company", values="RevenueEGP")
    comb = piv.sum(axis=1)
    x22 = comb[2025] / comb[2022]
    usd_g = (comb[2025] / FX[2025]) / (comb[2022] / FX[2022]) - 1
    grow = (piv.loc[2025] / piv.loc[2022]).sort_values(ascending=False)
    fast, fast_x = grow.index[0], float(grow.iloc[0])
    ens = lb[lb.Model.str.startswith("Ensemble")].set_index("Company")["MAPE_Holdout"]

    # numbers used by the KPI tiles and insight cards
    s = brand.set_index("Brand")
    coke_nat = geo[(geo.Category == "Soft drinks")].pivot(index="GovCode", columns="Brand", values="Share")
    tour = coke_nat["Coca-Cola"].sort_values(ascending=False)
    bf_geo = geo[(geo.Brand == "Breadfast")].set_index("GovCode")["Share"].sort_values(ascending=False)
    t_last = trend[trend.Month == trend.Month.max()].set_index("Brand")["Interest"]
    t_first = trend[trend.Month == trend.Month.min()].set_index("Brand")["Interest"]
    bf_ratio_now = t_last["Breadfast"] / t_last["talabat"]
    bf_ratio_then = t_first["Breadfast"] / t_first["talabat"]
    gname = gov.set_index("GovCode")

    kpi = [
        # Page, Ord, Key, Label, LabelAR, Value, Display, Sub, SubAR, Icon, Source
        ("overview", 1, "pop", "Egyptians at home", "عدد السكان", 109.5, "109.5M", "60% are under 30", "60% منهم تحت سن 30", "people", "S4;S5"),
        ("overview", 2, "percap", "Sparkling drinks per person", "نصيب الفرد سنويًا", 110, "110", "servings a year, +8% in 2025", "عبوة سنويًا، بزيادة 8% في 2025", "glass", "S5"),
        ("overview", 3, "gap", "Coca-Cola's gap to the leader", "فجوة كوكاكولا مع المتصدر", 5, "5 pts", "down from 13 pts in 2022", "انخفضت من 13 نقطة في 2022", "target", "S5"),
        ("overview", 4, "talabat", "talabat vs the next food app", "talabat مقابل أقرب منافس", 10, "10x+", "food delivery sales, Redseer", "مبيعات توصيل الطعام، وفق Redseer", "bike", "S6"),
        ("overview", 5, "infl", "Urban inflation, Sep 2026", "التضخم في الحضر", 13.9, "13.9%", "eased from 14.5% in Aug", "تراجع من 14.5% في أغسطس", "pulse", "S12"),
        ("where", 1, "outlets", "Outlets selling drinks", "منافذ بيع المشروبات", 150000, "150K", "20K fully activated sell 36% more", "20 ألف منفذ مُفعّل مبيعاته أعلى 36%", "store", "S5"),
        ("where", 2, "price", "Entry price, Upper Egypt", "أقل سعر في الصعيد", 8, "EGP 8", "192ml returnable glass bottle", "زجاجة مرتجعة 192 مل", "tag", "S5"),
        ("where", 3, "horeca", "Cafes & restaurants growth", "نمو المطاعم والمقاهي", 35, "+35%", "volume, Q1 2026; 4K new outlets", "في الربع الأول 2026، مع 4 آلاف منفذ جديد", "cup", "S5"),
        ("where", 4, "b2b", "Retailers ordering online", "تجار يطلبون إلكترونيًا", 27000, "27K", "3x vs 2024; WhatsApp orders 20x", "3 أضعاف 2024، وطلبات واتساب 20 ضعفًا", "phone", "S5"),
        ("delivery", 1, "gmv", "talabat group GMV 2025", "حجم أعمال talabat في 2025", 9.5, "$9.5B", "+28% at constant FX", "نمو 28% بسعر صرف ثابت", "bag", "S7"),
        ("delivery", 2, "nongcc", "Egypt, Jordan, Iraq share", "حصة مصر والأردن والعراق", 17, "17%", "of GMV in H1 2025, from 14%", "من حجم الأعمال في النصف الأول 2025، مقابل 14%", "pin", "S8"),
        ("delivery", 3, "bfratio", "Breadfast vs talabat search", "بحث بريدفاست مقابل talabat", round(bf_ratio_now * 100), f"{bf_ratio_now * 100:.0f}%", f"from {bf_ratio_then * 100:.0f}% in Jan 2021", f"مقابل {bf_ratio_then * 100:.0f}% في يناير 2021", "rocket", "S1"),
        ("delivery", 4, "bfraise", "Breadfast new funding", "تمويل جديد لبريدفاست", 50, "$50M", "pre-Series C, Feb 2026", "جولة ما قبل C، فبراير 2026", "coins", "S14"),
        ("forecast", 1, "sector25", "4 listed food makers, 2025", "إيرادات 4 شركات أغذية 2025", round(comb[2025]), f"EGP {comb[2025] / 1000:.1f}B", "Juhayna, Edita, Obour Land, Domty", "جهينة وإيديتا وعبور لاند ودومتي", "box", "S9"),
        ("forecast", 2, "x", "Growth in pounds since 2022", "النمو بالجنيه منذ 2022", round(x22, 2), f"{x22:.1f}x", f"EGP {comb[2022] / 1000:.1f}B to {comb[2025] / 1000:.1f}B", f"من {comb[2022] / 1000:.1f} إلى {comb[2025] / 1000:.1f} مليار جنيه", "up", "S9"),
        ("forecast", 3, "usd", "Growth in dollars since 2022", "النمو بالدولار منذ 2022", round(usd_g * 100, 1), f"{usd_g * 100:+.0f}%", f"${comb[2022] / FX[2022]:.0f}M to ${comb[2025] / FX[2025]:.0f}M", f"من {comb[2022] / FX[2022]:.0f} إلى {comb[2025] / FX[2025]:.0f} مليون دولار", "dollar", "S9;S11"),
        ("forecast", 4, "fy26", "2026 outlook, all four", "توقعات 2026 للشركات الأربع", round(comb[2026]), f"EGP {comb[2026] / 1000:.1f}B", f"+{(comb[2026] / comb[2025] - 1) * 100:.0f}% vs 2025", f"+{(comb[2026] / comb[2025] - 1) * 100:.0f}% مقارنة بـ 2025", "spark", "S9"),
    ]
    kpi = pd.DataFrame(kpi, columns=["Page", "Ord", "Key", "Label", "LabelAR", "Value", "Display", "Sub", "SubAR", "Icon", "Source"])

    top3 = tour.index[:3]
    lead = coke_nat.idxmax(axis=1)
    pepsi_n, coke_only = int((lead == "Pepsi").sum()), [c for c in lead.index if lead[c] == "Coca-Cola"]
    ins = [
        ("overview", 2, f"Pepsi leads {pepsi_n} of {len(lead)} governorates", f"بيبسي تتصدر {pepsi_n} محافظة من {len(lead)}",
         f"Coca-Cola leads only {', '.join(gname.loc[c, 'Governorate'] for c in coke_only)} ({tour[coke_only[0]] * 100:.0f}% vs {coke_nat.loc[coke_only[0], 'Pepsi'] * 100:.0f}%). The tourist coast is where it is closest.",
         f"كوكاكولا تتصدر {'، '.join(gname.loc[c, 'GovernorateAR'] for c in coke_only)} فقط ({tour[coke_only[0]] * 100:.0f}% مقابل {coke_nat.loc[coke_only[0], 'Pepsi'] * 100:.0f}%)، وتقترب أكثر في المدن السياحية.", "S1"),
        ("overview", 1, "The boycott spike faded", "أثر المقاطعة تلاشى",
         f"Spiro Spathis search jumped from 0 to 65 in Nov 2023 (Pepsi = 100). Today it is {s.loc['Spiro Spathis', 'ShareOfSearch12M'] * 100:.1f}% of cola searches.",
         f"قفز البحث عن سبيرو سباتس من صفر إلى 65 نقطة في نوفمبر 2023 (بيبسي = 100)، واليوم لا يتجاوز {s.loc['Spiro Spathis', 'ShareOfSearch12M'] * 100:.1f}% من البحث عن المشروبات الغازية.", "S1;S13"),
        ("where", 1, "Coca-Cola is strongest where tourists are", "كوكاكولا أقوى في المدن السياحية",
         ", ".join(f"{gname.loc[c, 'Governorate']} {tour[c] * 100:.0f}%" for c in top3) + f" of cola searches vs {coke_nat['Coca-Cola'].median() * 100:.0f}% in the median governorate.",
         "، ".join(f"{gname.loc[c, 'GovernorateAR']} {tour[c] * 100:.0f}%" for c in top3) + f" من البحث عن المشروبات الغازية، مقابل {coke_nat['Coca-Cola'].median() * 100:.0f}% في المحافظة المتوسطة.", "S1;S5"),
        ("where", 2, "Price decides in Upper Egypt", "السعر يحسم الشراء في الصعيد",
         "Coca-Cola HBC sells a 192ml glass bottle at EGP 8 there; returnable glass grew ~70% in Q1 2026 and holds 80% of the affordable segment.",
         "تبيع كوكاكولا زجاجة 192 مل بسعر 8 جنيهات هناك، ونمت الزجاجات المرتجعة نحو 70% في الربع الأول 2026، وتستحوذ على 80% من الشريحة الاقتصادية.", "S5"),
        ("delivery", 1, "Breadfast is strongest in Cairo and the North Coast", "بريدفاست الأقوى في القاهرة والساحل الشمالي",
         f"Breadfast takes {bf_geo['EG-MT'] * 100:.0f}% of delivery-app searches in Matrouh and {bf_geo['EG-C'] * 100:.0f}% in Cairo, but under 5% in most of the Delta and Upper Egypt.",
         f"تستحوذ بريدفاست على {bf_geo['EG-MT'] * 100:.0f}% من البحث عن تطبيقات التوصيل في مطروح و{bf_geo['EG-C'] * 100:.0f}% في القاهرة، وأقل من 5% في معظم الدلتا والصعيد.", "S1"),
        ("forecast", 1, f"Pounds up {x22:.1f}x, dollars {usd_g * 100:+.0f}%", f"الجنيه {x22:.1f} أضعاف، والدولار {usd_g * 100:+.0f}%",
         f"Juhayna, Edita, Obour Land and Domty grew from EGP {comb[2022] / 1000:.1f}B (2022) to {comb[2025] / 1000:.1f}B (2025). In dollars that is ${comb[2022] / FX[2022]:.0f}M to ${comb[2025] / FX[2025]:.0f}M. {fast} grew fastest ({fast_x:.1f}x).",
         f"نمت إيرادات جهينة وإيديتا وعبور لاند ودومتي من {comb[2022] / 1000:.1f} مليار جنيه في 2022 إلى {comb[2025] / 1000:.1f} مليار في 2025، أي من {comb[2022] / FX[2022]:.0f} إلى {comb[2025] / FX[2025]:.0f} مليون دولار. الأسرع نموًا: {COMPANIES[fast][0]} ({fast_x:.1f} أضعاف).", "S9;S11"),
    ]
    ins = pd.DataFrame(ins, columns=["Page", "Ord", "Title", "TitleAR", "Body", "BodyAR", "Source"])

    # long table the in-report AI reads (one row = one fact)
    kn = []
    for r in trend.itertuples():
        kn.append(("search_trend", r.Brand, s.loc[r.Brand, "BrandAR"], r.Category, r.Month.strftime("%Y-%m"), r.Interest, "index", "S1"))
    for r in geo.itertuples():
        kn.append(("search_geo", r.Brand, s.loc[r.Brand, "BrandAR"], r.GovCode, "2021-2026", r.Share, "share", "S1"))
    for r in gov.itertuples():
        for a in ("Population", "UrbanPct", "UrbanPop"):
            kn.append(("governorate", r.GovCode, f"{r.Governorate}|{r.GovernorateAR}|{r.Region}", a, "", float(getattr(r, a)), a, "S2;S3"))
    for r in jq.itertuples():
        for a in ("RevenueEGP", "ForecastEGP", "Lo80", "Hi80", "BacktestEGP", "ActualUSD", "ForecastUSD"):
            v = getattr(r, a)
            if pd.notna(v):
                kn.append(("rev_q", r.Company, COMPANIES[r.Company][0], a, r.Quarter, float(v), "EGP M" if "USD" not in a else "USD M", "S9;S11"))
    for r in fy.itertuples():
        kn.append(("rev_fy", r.Company, COMPANIES[r.Company][0], "RevenueEGP", str(r.Year), float(r.RevenueEGP), r.Basis, "S9"))
        kn.append(("rev_fy", r.Company, COMPANIES[r.Company][0], "RevenueUSD", str(r.Year), float(r.RevenueUSD), r.Basis, "S9;S11"))
    for r in lb.itertuples():
        kn.append(("model", r.Model, r.Company, "MAPE_Holdout", "", float(r.MAPE_Holdout), "%", "S9"))
    for r in kpi.itertuples():
        kn.append(("kpi", r.Key, r.LabelAR, r.Label, r.Display, float(r.Value), r.Sub, r.Source))
    for r in brand.itertuples():
        kn.append(("brand", r.Brand, r.BrandAR, r.Category, r.Company, float(r.ShareOfSearch12M), r.Color, "S1"))
    kn = pd.DataFrame(kn, columns=["Dataset", "Entity", "EntityAR", "Attr", "Period", "Value", "Unit", "Source"])
    kn.insert(0, "Id", range(1, len(kn) + 1))

    src = pd.DataFrame([dict(Id=k, Title=v[0], URL=v[1]) for k, v in SOURCES.items()])
    src = pd.concat([src, pd.DataFrame([dict(Id="S17", Title="Logos: Wikimedia Commons PD-textlogo files and company sites; trademarks of their owners", URL="https://commons.wikimedia.org/")])])

    # Feed: one JSON record per row, so a single full-page visual can draw any page and power Ask AI
    feed = []

    def add(ds, df):
        for rec in json.loads(df.to_json(orient="records", date_format="iso", force_ascii=False)):
            feed.append({"Dataset": ds, "Seq": len(feed) + 1, "Json": json.dumps(rec, ensure_ascii=False, separators=(",", ":"))})

    add("brand", brand)
    add("gov", gov)
    add("trend", pd.DataFrame([{"b": b, "c": g.Category.iloc[0], "m": g.Month.dt.strftime("%Y-%m").tolist(), "v": g.Interest.tolist()}
                               for b, g in trend.groupby("Brand", sort=False)]))
    add("geo", pd.DataFrame([{"b": b, "c": g.Category.iloc[0], "s": dict(zip(g.GovCode, g.Share.round(3)))} for b, g in geo.groupby("Brand", sort=False)]))
    add("event", pd.DataFrame([{"m": k, "c": "Soft drinks" if v[0] == "cola" else "Delivery apps", "en": v[1], "ar": v[2]} for k, v in MONTH_EVENTS.items()]))
    add("company", pd.DataFrame([dict(Company=k, CompanyAR=v[0], Ticker=v[1], Segment=v[2], SegmentAR=v[3]) for k, v in COMPANIES.items()]))
    add("jq", jq)
    add("jfy", fy)
    add("model", lb)
    add("kpi", kpi)
    add("insight", ins)
    add("kb", kn)
    add("source", src)
    feed = pd.DataFrame(feed)

    # one row per company: the dimension the forecast pages filter by, with the figures its cards show
    crow = []
    for name, (ar, tick, seg, seg_ar, _q) in COMPANIES.items():
        f = fy[fy.Company == name].set_index("Year")
        m = lb[lb.Company == name]
        single = m[~m.Model.str.startswith("Ensemble")]
        best = single.sort_values("MAPE_Holdout").iloc[0]
        top = single[single.Weight > 0].sort_values("Weight", ascending=False)
        blend = " · ".join(f"{r.Model} {r.Weight * 100:.0f}%" for r in top.itertuples())
        mp = float(ens[name])
        rel, rel_ar = ("High", "عالية") if mp < 6 else ("Medium", "متوسطة") if mp < 10 else ("Low", "منخفضة")
        r25, f26, f27 = f.loc[2025, "RevenueEGP"], f.loc[2026, "RevenueEGP"], f.loc[2027, "RevenueEGP"]
        g26, g27 = f26 / r25 - 1, f27 / f26 - 1
        a, fq = AN[name], jq[jq.Company == name]
        real = fq.groupby("Year").RealEGP.sum()
        rg27 = real[2027] / real[2026] - 1
        lo27, hi27 = fq[fq.Year == 2027].ForecastLow.sum(), fq[fq.Year == 2027].ForecastHigh.sum()
        cin, cn = a["coverage"]
        better = a["mape_real_bt"] < a["mape_nominal_bt"]
        note = (f"Backtest on {cn} quarters from 5 origins: the ensemble on pounds missed by {a['mape_nominal_bt']:.1f}% on average, "
                f"the inflation-adjusted method by {a['mape_real_bt']:.1f}%. "
                + ("The inflation-adjusted method was more accurate here. " if better else
                   "The pound ensemble stays the main forecast; the inflation view is used to split growth and for scenarios. ")
                + f"The 80% band held the actual in {cin} of {cn} quarters"
                + (" (about as often as it should)." if cin / cn >= 0.7 else ", less often than it should: read the band as too narrow."))
        crow.append(dict(
            Company=name, CompanyAR=ar, Ticker=tick, Segment=seg, SegmentAR=seg_ar,
            Revenue2025=round(r25), Forecast2026=round(f26), Forecast2027=round(f27), Growth2026=round(g26, 4), Growth2027=round(g27, 4),
            Revenue2025USD=round(f.loc[2025, "RevenueUSD"], 1), Forecast2027USD=round(f.loc[2027, "RevenueUSD"], 1),
            EnsembleMAPE=round(mp, 2), BestModel=best.Model, BestModelMAPE=round(float(best.MAPE_Holdout), 2), Blend=blend,
            Reliability=rel, ReliabilityAR=rel_ar,
            RealGrowth2027=round(rg27, 6), InflationPart=round(g27 - rg27, 6), Forecast2027Low=round(lo27), Forecast2027High=round(hi27),
            MASE=round(a["mase"], 2), CoverageIn=cin, CoverageN=cn, Coverage=f"{cin} of {cn}",
            ErrH1=round(a["by_h"][1], 2), ErrH2=round(a["by_h"][2], 2), ErrH3=round(a["by_h"][3], 2), ErrH4=round(a["by_h"][4], 2),
            BacktestMAPE=round(a["mape_nominal_bt"], 2), RealMethodMAPE=round(a["mape_real_bt"], 2), MethodNote=note,
            InsightEN=(f"{name} is expected to reach EGP {f27 / 1000:.1f}B in 2027 ({g27 * 100:+.0f}% on 2026). The forecast blends {blend}. "
                       f"On 4 quarters it never saw, it missed by {mp:.1f}% on average ({rel.lower()} confidence); the best single model, "
                       f"{best.Model}, missed by {best.MAPE_Holdout:.1f}%. After inflation, 2027 growth is {rg27 * 100:+.0f}% in real terms; "
                       f"if inflation runs at 9% or 20% instead of 13.9%, 2027 lands between EGP {lo27 / 1000:.1f}B and {hi27 / 1000:.1f}B."),
            InsightAR=(f"متوقع أن تصل إيرادات {ar} إلى {f27 / 1000:.1f} مليار جنيه في 2027 ({g27 * 100:+.0f}% عن 2026). الموديل مزيج من {blend}. "
                       f"على 4 أرباع لم يرها، أخطأ بمتوسط {mp:.1f}% (ثقة {rel_ar})، وأدق نموذج منفرد {best.Model} أخطأ بـ {best.MAPE_Holdout:.1f}%. "
                       f"بعد خصم التضخم النمو الحقيقي في 2027 {rg27 * 100:+.0f}%، ولو التضخم 9% أو 20% بدل 13.9% هتبقى 2027 بين {lo27 / 1000:.1f} و{hi27 / 1000:.1f} مليار جنيه."),
            Sort=0))
    company = pd.DataFrame(crow).sort_values("Growth2027", ascending=False)
    company["Sort"] = range(1, len(company) + 1)

    # numbered reading notes for the native pages, every figure taken from the tables above
    notes = []

    def note(page, ord_, tone, title, title_ar, body, src="", cat="", comp=""):
        notes.append(dict(Page=page, Category=cat, Company=comp, Ord=ord_, Tone=tone, Title=title, TitleAR=title_ar, Body=body, Source=src))

    for cat in CATS:
        gp = geo[geo.Category == cat].pivot(index="GovCode", columns="Brand", values="Share").fillna(0)
        share = {b: v for b, v in sos.items() if s.loc[b, "Category"] == cat}
        order = sorted(share, key=share.get, reverse=True)
        L, R = order[0], order[1]
        LA = s.loc[L, "BrandAR"]
        led = gp.idxmax(axis=1)
        n_led = int((led == L).sum())
        others = led[led != L]
        margin = gp[L] - gp[R]
        wide, close = margin.idxmax(), margin.abs().idxmin()
        rest = 1 - share[L] - share[R]
        widest = f"Widest lead: {gname.loc[wide, 'Governorate']}, {gp.loc[wide, L] * 100:.0f}% vs {gp.loc[wide, R] * 100:.0f}%."
        note("search", 1, "lead", f"{L} holds {share[L] * 100:.0f}% of searches", f"{LA} تستحوذ على {share[L] * 100:.0f}% من البحث",
             f"Last 12 months: {L} {share[L] * 100:.0f}%, {R} {share[R] * 100:.0f}%, the other brands {rest * 100:.0f}% together.", "S1", cat=cat)
        if len(others):
            body = "Other leaders: " + "; ".join(f"{b} in {gname.loc[g, 'Governorate']}" for g, b in others.head(3).items()) + ". " + widest
        else:
            body = f"No other brand leads a governorate; {L} holds over 90% of searches in {int((gp[L] > 0.9).sum())} of them."
        note("search", 2, "fact", f"Leads {n_led} of {len(led)} governorates", f"تتصدر {n_led} محافظة من {len(led)}", body, "S1", cat=cat)
        note("search", 3, "watch", f"Closest race: {gname.loc[close, 'Governorate']}", f"أقرب منافسة: {gname.loc[close, 'GovernorateAR']}",
             f"{L} {gp.loc[close, L] * 100:.0f}% vs {R} {gp.loc[close, R] * 100:.0f}%. In the median governorate the gap is {margin.median() * 100:.0f} pts.",
             "S1", cat=cat)
        note("search", 4, "method", "Search is attention, not sales", "البحث يقيس الاهتمام مش المبيعات",
             "Google Trends share of search, Jan 2021 – Oct 2026. Use it to compare brands and places, not volumes.", "S1", cat=cat)

    apps = TREND_ORDER["apps"]
    ds = {b: sos[b] for b in apps}
    ao = sorted(ds, key=ds.get, reverse=True)
    growth = (last12 / first12).reindex(apps).replace([float("inf")], float("nan")).dropna().sort_values(ascending=False)
    n_low = int((bf_geo < 0.05).sum())
    note("delivery", 1, "lead", f"talabat takes {ds['talabat'] * 100:.0f}% of app searches", f"طلبات تستحوذ على {ds['talabat'] * 100:.0f}% من البحث",
         f"Last 12 months; next is {ao[1]} at {ds[ao[1]] * 100:.0f}%. talabat group GMV 2025: $9.5B, +28% at constant FX.", "S1;S7")
    note("delivery", 2, "fact", f"Breadfast: {bf_ratio_then * 100:.0f}% → {bf_ratio_now * 100:.0f}% of talabat",
         f"بريدفاست من {bf_ratio_then * 100:.0f}% إلى {bf_ratio_now * 100:.0f}% من طلبات",
         "Breadfast's monthly search as a share of talabat's, Jan 2021 vs the latest month. It raised $50M (pre-Series C) in Feb 2026.", "S1;S14")
    note("delivery", 3, "watch", "Breadfast is a Cairo and coast story", "بريدفاست قوية في القاهرة والساحل بس",
         f"{bf_geo['EG-MT'] * 100:.0f}% of app searches in Matrouh, {bf_geo['EG-C'] * 100:.0f}% in Cairo, under 5% in {n_low} of {len(bf_geo)} governorates.", "S1")
    note("delivery", 4, "fact", f"Fastest grower: {growth.index[0]} {growth.iloc[0]:.1f}x", f"الأسرع نموًا: {s.loc[growth.index[0], 'BrandAR']}",
         f"Average search, last 12 months vs 2021. {growth.index[1]} {growth.iloc[1]:.1f}x, talabat {growth['talabat']:.1f}x.", "S1")
    note("delivery", 5, "method", "Switch the measure on the chart", "غيّر المقياس فوق الرسم",
         "Interest is Google's 0–100 index. Index 2021=100 compares growth; Share % compares position in the category.", "S1")

    for r in crow:
        n = r["Company"]
        g, rg, inf = r["Growth2027"] * 100, r["RealGrowth2027"] * 100, r["InflationPart"] * 100
        note("forecast", 1, "lead", f"EGP {r['Forecast2027'] / 1000:.1f}B in 2027", f"{r['Forecast2027'] / 1000:.1f} مليار جنيه في 2027",
             f"{g:+.0f}% on 2026 in pounds. Ensemble of {r['Blend']}.", "S9", comp=n)
        note("forecast", 2, "watch", f"After inflation: {rg:+.0f}%", f"بعد خصم التضخم: {rg:+.0f}%",
             f"About {inf:.0f} of the {g:.0f} pts is prices (13.9% base). At 9% or 20% inflation 2027 lands at EGP "
             f"{r['Forecast2027Low'] / 1000:.1f}–{r['Forecast2027High'] / 1000:.1f}B.", "S9;S12", comp=n)
        note("forecast", 3, "fact", f"Missed by {r['EnsembleMAPE']:.1f}% on unseen quarters", f"الخطأ {r['EnsembleMAPE']:.1f}% على أرباع جديدة",
             f"{r['Reliability']} confidence. Best single model: {r['BestModel']} ({r['BestModelMAPE']:.1f}%). MASE {r['MASE']:.2f}: "
             + ("beats a same-quarter-last-year guess." if r["MASE"] < 1 else "no better than a same-quarter-last-year guess."), "S9", comp=n)
        note("forecast", 4, "method", f"The 80% band held {r['CoverageIn']} of {r['CoverageN']}", f"الهامش احتوى الفعلي {r['CoverageIn']} من {r['CoverageN']}",
             "The band is the ensemble's own past misses at each horizon, so it widens further out. "
             + ("Coverage is on target." if r["CoverageIn"] / r["CoverageN"] >= 0.7 else "Read it as too narrow."), "S9", comp=n)
        better = r["RealMethodMAPE"] < r["BacktestMAPE"]
        note("deepdive", 1, "lead", f"Best single model: {r['BestModel']}", f"أدق نموذج: {r['BestModel']}",
             f"{r['BestModelMAPE']:.1f}% error on 4 unseen quarters; the blended ensemble {r['EnsembleMAPE']:.1f}%.", "S9", comp=n)
        note("deepdive", 2, "fact", f"1 quarter ahead {r['ErrH1']:.1f}%, 4 ahead {r['ErrH4']:.1f}%", "الخطأ حسب المدى",
             f"Average miss by horizon in a rolling backtest from 5 origins: {r['ErrH1']:.1f}% · {r['ErrH2']:.1f}% · {r['ErrH3']:.1f}% · {r['ErrH4']:.1f}%.",
             "S9", comp=n)
        note("deepdive", 3, "watch", "Pounds or inflation-adjusted?", "بالجنيه ولا بعد التضخم؟",
             f"Backtest error: pound ensemble {r['BacktestMAPE']:.1f}%, inflation-adjusted {r['RealMethodMAPE']:.1f}%. "
             + ("The adjusted method won here; it is shown as a cross-check." if better else "Pounds won, so they stay the main forecast."),
             "S9;S12", comp=n)
        note("deepdive", 4, "method", "How to read the paths", "إزاي تقرأ الرسم",
             "Black: actual. Teal: the ensemble. The 6 tinted lines are the single models; their spread is the model uncertainty.", "", comp=n)
    notes = pd.DataFrame(notes, columns=["Page", "Category", "Company", "Ord", "Tone", "Title", "TitleAR", "Body", "Source"])

    sheets = {
        "Brand": brand, "Governorate": gov, "Months": months, "SearchTrend": trend, "SearchGeo": geo,
        "Revenue_Q": jq, "Revenue_FY": fy, "Models": lb, "Company": company, "Backtest": backtest, "Scenario": scenario, "TrendMetric": pd.DataFrame({"Metric": ["Interest", "Index 2021=100", "Share %"], "Ord": [1, 2, 3]}), "KPI": kpi, "Insight": ins, "Notes": notes, "Knowledge": kn, "Sources": src, "Feed": feed,
    }
    write_excel(sheets)
    payload = {k: json.loads(v.to_json(orient="records", date_format="iso", force_ascii=False)) for k, v in sheets.items()}
    (OUT / "egypt_data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    rows = sum(len(v) for v in sheets.values())
    print(f"Egypt Market Intelligence · data build")
    print(f"  {len(sheets)} tables, {rows:,} rows  ->  data/{XLSX.name}")
    lead = {c: max((b for b in sos if s.loc[b, "Category"] == c), key=sos.get) for c in CATS}
    print("  Share of search, last 12 months:  " + " · ".join(f"{c}: {lead[c]} {sos[lead[c]] * 100:.1f}%" for c in CATS))
    print(f"  Forecast backtest, 4 unseen quarters ({len(fc.MODELS)} models, top-3 inverse-error ensemble):")
    print(f"    {'company':<12}{'ensemble':>9}{'best single model':>32}{'MASE':>7}{'80% band':>10}{'2027 EGP B':>12}{'real':>8}")
    for r in company.sort_values("EnsembleMAPE").itertuples():
        print(f"    {r.Company:<12}{r.EnsembleMAPE:>8.1f}%{r.BestModel + f' {r.BestModelMAPE:.1f}%':>32}{r.MASE:>7.2f}"
              f"{r.Coverage:>10}{r.Forecast2027 / 1000:>12.1f}{r.RealGrowth2027 * 100:>+7.1f}%")


def write_excel(sheets):
    wb = Workbook()
    ab = wb.active
    ab.title = "About"
    lines = ["Egypt Market Intelligence 2026", "Public data on Egyptian soft drinks, delivery apps, governorates and listed food makers.",
             "Each sheet is one Power BI table. Sources sheet lists every source id used in the Source columns.",
             "Google Trends values are relative search interest, not sales.",
             "Independent analysis. Not affiliated with any company shown."]
    for i, t in enumerate(lines, 1):
        ab.cell(row=i, column=1, value=t).font = Font(bold=(i == 1), size=14 if i == 1 else 11)
    head = PatternFill("solid", fgColor="0B6E69")
    for name, df in sheets.items():
        ws = wb.create_sheet(name)
        ws.append(list(df.columns))
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = head
            c.alignment = Alignment(horizontal="center")
        for row in df.itertuples(index=False):
            ws.append([None if (isinstance(v, float) and np.isnan(v)) else (v.to_pydatetime() if isinstance(v, pd.Timestamp) else (bool(v) if isinstance(v, np.bool_) else v)) for v in row])
        for i, col in enumerate(df.columns, 1):
            w = max(len(str(col)), *(len(str(v)) for v in df[col].head(200))) if len(df) else len(col)
            ws.column_dimensions[get_column_letter(i)].width = min(60, w + 2)
            if "Month" == col or "QuarterEnd" == col:
                for c in ws[get_column_letter(i)][1:]:
                    c.number_format = "yyyy-mm-dd"
        ws.freeze_panes = "A2"
    wb.save(XLSX)


if __name__ == "__main__":
    build()
