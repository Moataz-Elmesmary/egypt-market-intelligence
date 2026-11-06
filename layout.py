"""One layout for the native pages, shared by the background renderer (tools/make_backgrounds.py)
and the report builder (build_pbip.py): every panel, tile and popup drawn in a background is the
exact box a Power BI visual is placed on. Coordinates are report pixels on a 1280 x 720 page.

Design language = the portal page: sand canvas, narrow dark rail, white cards with a hairline border,
teal for the lead, gold for the rival, quiet tints for the rest. Every page uses the same grid:
a work area on the left (852 px) and a numbered "read" column on the right (300 px).
"""

SIDE = 84                    # rail width (same rail as the portal)
X0, X1 = 100, 1264           # content columns
HEAD_H = 80                  # header zone (no band: title on the sand)

# rail: (page, English, Arabic, icon)
RAIL = [("market", "Portal", "البوابة", "spark"), ("search", "Map", "الخريطة", "pin"),
        ("delivery", "Delivery", "التوصيل", "bike"), ("forecast", "Forecast", "التوقعات", "up"),
        ("deepdive", "Deep-dive", "الشركة", "box")]
RAIL_TOP, RAIL_STEP, RAIL_H = 92, 72, 62


def nav_boxes():
    """(key, x, y, w, h) of each rail item."""
    return [(k, 8, RAIL_TOP + i * RAIL_STEP, 68, RAIL_H) for i, (k, *_r) in enumerate(RAIL)]


ASK = (1156, 20, 108, 40)    # Ask AI pill
CLEAR = (1084, 24, 64, 32)   # clear all slicers


def tiles(y=88, h=80, n=5):
    w = (X1 - X0 - (n - 1) * 12) / n
    return [(round(X0 + i * (w + 12)), y, round(w), h) for i in range(n)]


T = tiles()
READ = (964, 180, 300, 528)                  # numbered notes column, every page
WIDE = (100, 180, 852, 316)                  # main chart
BOT_L, BOT_R = (100, 508, 420, 200), (532, 508, 420, 200)

POPUP = (240, 64, 800, 616)          # popup panel
POPUP_BODY = (264, 132, 752, 528)    # where popup visuals go
POPUP_CLOSE = (996, 80, 28, 28)
AI_PANEL = (868, 100, 396, 608)
AI_CLOSE = (1228, 76, 28, 22)

PAGES = {
    "search": {
        "n": 2, "title": "Where Egypt searches", "ar": "خريطة البحث في مصر",
        "sub": "Google share of search by governorate · Jan 2021 – Oct 2026 · click a tile for details",
        "slicers": [("Brand.Category", "Category", (680, 18, 128, 48)), ("Governorate.Region", "Region", (816, 18, 120, 48)),
                    ("Governorate.Governorate", "Governorate", (944, 18, 132, 48))],
        "tiles": [
            (T[0], "National leader", "المتصدر", "target"),
            (T[1], "Its share of search", "حصته من البحث", "spark"),
            (T[2], "Governorates it leads", "محافظات بيتصدرها", "pin"),
            (T[3], "Runner-up", "المركز التاني", "people"),
            (T[4], "Urban consumers (M)", "سكان الحضر", "store"),
        ],
        "panels": [
            ((100, 180, 420, 528), "Who leads each governorate", "Hover a governorate · darker = bigger lead", "pin"),
            ((532, 180, 420, 250), "Share of search by brand", "Last 12 months · click a bar to filter", "target"),
            ((532, 442, 420, 266), "Leader's share: region ▸ governorate", "Drill down with the arrows on the chart", "up"),
        ],
        "popups": {"leader": "Brand share by region", "led": "Where the leader wins, and by how much",
                   "urban": "Urban consumers by governorate"},
    },
    "delivery": {
        "n": 3, "title": "Delivery apps", "ar": "تطبيقات التوصيل",
        "sub": "talabat's lead, Breadfast's climb · Google Trends + company filings · click a tile for details",
        "slicers": [("Brand.Brand", "Brand", (808, 18, 128, 48)), ("Months.Year", "Year", (944, 18, 132, 48))],
        "switch": (640, 188, 304, 28),
        "tiles": [
            (T[0], "talabat vs the next app", "طلبات مقابل أقرب منافس", "bike"),
            (T[1], "talabat group GMV 2025", "حجم أعمال طلبات", "bag"),
            (T[2], "Breadfast vs talabat search", "بريدفاست مقابل طلبات", "rocket"),
            (T[3], "Breadfast new funding", "تمويل بريدفاست", "coins"),
            (T[4], "Fastest grower since 2021", "الأسرع نموًا", "up"),
        ],
        "panels": [
            (WIDE, "Google search, monthly", "talabat teal · Breadfast gold · the rest in tints", "pulse"),
            (BOT_L, "Momentum: 2021 vs last 12 months", "Growth = last-12-month average ÷ 2021", "rocket"),
            (BOT_R, "Share of search · last 12 months", "Click a bar to filter the page", "target"),
        ],
        "popups": {"talabat": "talabat vs the field", "breadfast": "Breadfast's climb"},
    },
    "forecast": {
        "n": 4, "title": "Revenue forecast", "ar": "توقعات الإيرادات",
        "sub": "4 EGX food makers · 6 models · rolling backtest · top-3 ensemble",
        "company": (620, 17, 524, 46),
        "switch": (676, 188, 268, 28),
        "tiles": [
            (T[0], "2025 revenue (EGP B)", "إيرادات 2025", "box"),
            (T[1], "2027 by scenario (EGP B)", "توقع 2027", "spark"),
            (T[2], "Growth 2027 in pounds", "النمو بالجنيه", "up"),
            (T[3], "Growth after inflation", "بعد التضخم", "coins"),
            (T[4], "Error on unseen quarters", "الخطأ", "target"),
        ],
        "panels": [
            (WIDE, "Quarterly revenue, forecast and 80% band", "Dashed: backtest on quarters the models never saw", "pulse"),
            (BOT_L, "Model leaderboard", "Error on 4 unseen quarters · ensemble weight", "target"),
            (BOT_R, "2027 growth: pounds vs after inflation", "The gap between the bars is inflation", "coins"),
        ],
        "popups": {"f27": "2027 forecast, quarter by quarter", "err": "How accurate is the forecast?"},
    },
    "deepdive": {
        "n": 5, "title": "Company deep-dive", "ar": "تفاصيل الشركة",
        "sub": "Every model's path next to the ensemble · year ▸ quarter drill",
        "company": (620, 17, 524, 46),
        "tiles": [
            (T[0], "Most accurate single model", "أدق نموذج", "target"),
            (T[1], "Ensemble error", "خطأ المزيج", "pulse"),
            (T[2], "MASE · below 1 beats naive", "مقارنة بالساذج", "spark"),
            (T[3], "80% band held the actual", "الهامش احتوى الفعلي", "box"),
            (T[4], "Confidence", "درجة الثقة", "shield"),
        ],
        "panels": [
            (WIDE, "Actual revenue and every model's forecast (EGP M)", "Black: actual · teal: ensemble · tints: the 6 models", "pulse"),
            (BOT_L, "Quarter by quarter", "Backtest vs actual, then the forecast", "box"),
            (BOT_R, "Revenue by year ▸ quarter", "Drill down with the arrows on the chart", "up"),
        ],
        "popups": {"acc": "Accuracy by horizon, quarter by quarter"},
    },
}
