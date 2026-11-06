"""Scope gate and instant router.

gate()  : refuses before any tool or model call when a question has nothing to do with the data
          (no entity, no domain word) or tries to steer the assistant (prompt injection).
route() : recognises the common question shapes and returns a Plan with a confidence score.
          At or above THRESHOLD the plan runs with no LLM call; below it the question goes to
          Gemini with the same tools. The router never answers a question it only half understands.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

THRESHOLD = 0.8


def norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[ً-ْـ]", "", s)
    s = re.sub(r"[أإآ]", "ا", s).replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    s = re.sub(r"[؟?!.,،:;()\"']", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def is_arabic(s: str) -> bool:
    return bool(re.search(r"[؀-ۿ]", s))


BRANDS = {
    "Pepsi": ["pepsi", "بيبسي", "بيبسى"], "Coca-Cola": ["coca-cola", "coca cola", "coke", "كوكاكولا", "كوكا كولا", "كوكا"],
    "Spiro Spathis": ["spiro", "spathis", "سبيرو", "سباتس"], "Big Cola": ["big cola", "بيج كولا"], "V7 Cola": ["v7", "في 7", "في سفن"],
    "talabat": ["talabat", "طلبات"], "Breadfast": ["breadfast", "بريدفاست", "بريد فاست"], "instashop": ["instashop", "انستاشوب", "انستا شوب"],
    "elmenus": ["elmenus", "المنيوز", "المنيو"], "Rabbit": ["rabbit", "رابيت"],
}
DELIVERY = {"talabat", "Breadfast", "instashop", "elmenus", "Rabbit"}
COMPANIES = {"Juhayna": ["juhayna", "جهينه"], "Edita": ["edita", "ايديتا", "اديتا"], "Obour Land": ["obour", "عبور"], "Domty": ["domty", "دومتي", "دومتى"]}
GOVS = {
    "EG-C": ["cairo", "القاهره", "مصر الجديده"], "EG-GZ": ["giza", "الجيزه", "جيزه"], "EG-ALX": ["alexandria", "alex", "اسكندريه", "الاسكندريه"],
    "EG-KB": ["qalyubia", "القليوبيه"], "EG-SHR": ["sharqia", "الشرقيه"], "EG-DK": ["dakahlia", "mansoura", "الدقهليه", "المنصوره"],
    "EG-GH": ["gharbia", "tanta", "الغربيه", "طنطا"], "EG-MNF": ["monufia", "المنوفيه"], "EG-BH": ["beheira", "البحيره"],
    "EG-KFS": ["kafr el sheikh", "كفر الشيخ"], "EG-DT": ["damietta", "دمياط"], "EG-PTS": ["port said", "بورسعيد"],
    "EG-IS": ["ismailia", "الاسماعيليه"], "EG-SUZ": ["suez", "السويس"], "EG-FYM": ["faiyum", "fayoum", "الفيوم"],
    "EG-BNS": ["beni suef", "بني سويف"], "EG-MN": ["minya", "المنيا"], "EG-AST": ["asyut", "assiut", "اسيوط"],
    "EG-SHG": ["sohag", "سوهاج"], "EG-KN": ["qena", "قنا"], "EG-LX": ["luxor", "الاقصر"], "EG-ASN": ["aswan", "اسوان"],
    "EG-BA": ["red sea", "hurghada", "البحر الاحمر", "الغردقه"], "EG-JS": ["south sinai", "sharm", "جنوب سيناء", "شرم"],
    "EG-SIN": ["north sinai", "شمال سيناء"], "EG-MT": ["matrouh", "north coast", "sahel", "مطروح", "الساحل"], "EG-WAD": ["new valley", "الوادي الجديد"],
}
W = {
    "app": ["app", "delivery", "order", "توصيل", "تطبيق", "ابلكيشن", "اوردر", "دليفري"],
    "cola": ["cola", "soda", "soft drink", "كولا", "مشروب", "غازي", "ساقعه"],
    "move": ["grow", "falling", "decline", "rising", "losing", "momentum", "winning", "بيكبر", "بتكبر", "بيقع", "بتقع", "نمو", "تراجع",
             "بيزيد", "بيقل", "صاعد", "نازل", "بيكسب", "بتكسب", "بيخسر"],
    "fc": ["forecast", "predict", "projection", "2027", "next year", "توقع", "هتعمل", "السنه الجايه", "هيعمل"],
    "pick": ["which", "fastest", "compare", "all", "listed", "مين", "اسرع", "انهي", "قارن", "كل الشركات"],
    "boycott": ["boycott", "مقاطعه", "قاطع"],
    "sold": ["sold", "sell", "consum", "buy", "بتتباع", "بيتباع", "استهلاك", "بيشربوا", "بيشتروا"],
    "rev": ["revenue", "sales", "dollar", "usd", "pound", "egp", "ايراد", "مبيعات", "دولار", "جنيه"],
    "help": ["what can you", "help", "تقدر تعمل", "بتعرف تعمل", "ساعدني", "بتجاوب على ايه"],
    "why": ["why", "how come", "explain", "ليه", "لماذا", "اشرح", "فسر"],
    # things the model does not hold: a question about them must not be force-fitted onto a near tool
    "unsupported": ["profit", "margin", "ebitda", "net income", "stock price", "share price", "market cap", "dividend", "employees",
                    "salary", "price of", "ربح", "ارباح", "هامش", "سعر السهم", "سعر سهم", "سهم", "اسهم", "القيمه السوقيه", "موظفين", "مرتب", "توزيعات"],
    # judgement calls ("is it reliable", "should we") need reasoning over the figures, not a template
    "judge": ["reliable", "trust", "should", "enough", "worth", "recommend", "risk", "better", "ينفع", "اعتمد", "اثق", "نثق", "احسن",
              "افضل", "اخاطر", "مخاطره", "انصح", "تنصح", "يستاهل"],
    # brands people ask about that the model does not cover: never answered with a neighbour's numbers
    "foreign": ["nescafe", "nestle", "pringles", "chipsy", "molto", "lipton", "red bull", "redbull", "sprite", "fanta", "7up", "7 up",
                "schweppes", "mirinda", "mountain dew", "uber", "careem", "swvl", "jumia", "amazon", "noon", "fawry", "instapay", "mrsool",
                "نسكافيه", "نستله", "برينجلز", "شيبسي", "مولتو", "ليبتون", "ريد بول", "سبرايت", "فانتا", "سفن اب", "شويبس", "ميرندا",
                "ماونتن ديو", "اوبر", "كريم", "سويفل", "جوميا", "امازون", "فوري", "انستاباي", "مرسول"],
    "domain": ["market", "brand", "search", "google", "trend", "share", "governorate", "city", "company", "egx", "quarter", "egypt",
               "سوق", "براند", "بحث", "جوجل", "حصه", "محافظه", "مدينه", "شركه", "بورصه", "ربع", "مصر", "سنه", "شهر"],
}
INJECTION = [r"ignore (all |the )?(previous|above|prior) (instructions|rules)", r"system prompt", r"you are now", r"jailbreak",
             r"developer mode", r"\bdrop table\b", r"evaluate\s+\w+\s*\(", r"تجاهل (كل )?التعليمات", r"انسى التعليمات"]


KNOWN_LATIN = {norm(a) for tbl in (BRANDS, COMPANIES, GOVS) for al in tbl.values() for a in al if a.isascii()} | {
    "egypt", "egx", "google", "trends", "gmv", "usd", "egp", "q1", "q2", "q3", "q4", "ai", "pbi", "power", "bi", "kpi", "ok", "vs"}


def unknown_names(raw: str) -> list[str]:
    """Latin words that look like names (capitalised mid-sentence, or any Latin word in an Arabic
    question) and match nothing the model knows: a sign the question is about something else."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9&\-]+", raw)
    ar = is_arabic(raw)
    out = []
    for i, w in enumerate(words):
        n = norm(w)
        if n in KNOWN_LATIN or any(n in k or k in n for k in KNOWN_LATIN if len(k) > 3):
            continue
        first = raw.strip().startswith(w)
        if ar or (w[0].isupper() and not first and n not in ("i", "is", "the")):
            out.append(w)
    return out


def find(q: str, table: dict) -> list[str]:
    return [k for k, al in table.items() if any(norm(a) in q for a in al)]


def has(q: str, key: str) -> bool:
    return any(norm(w) in q for w in W[key])


@dataclass
class Plan:
    intent: str
    tool: str
    args: dict
    confidence: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class Gate:
    ok: bool
    kind: str = ""        # "", "out_of_scope", "security"
    reason: str = ""


def gate(question: str) -> Gate:
    raw = question.strip()
    if len(raw) < 2:
        return Gate(False, "out_of_scope", "empty question")
    if len(raw) > 600:
        return Gate(False, "out_of_scope", "question longer than 600 characters")
    low = raw.lower()
    if any(re.search(p, low) for p in INJECTION):
        return Gate(False, "security", "the question tries to change the assistant's instructions")
    q = norm(raw)
    known = find(q, BRANDS) or find(q, COMPANIES) or find(q, GOVS)
    words = any(has(q, k) for k in ("app", "cola", "move", "fc", "boycott", "sold", "rev", "help", "domain", "unsupported"))
    if not known and not words:
        return Gate(False, "out_of_scope", "no brand, company, governorate or market term in the question")
    if has(q, "foreign"):
        return Gate(False, "not_covered", "names a brand or company the model does not cover")
    if has(q, "unsupported") and not (has(q, "rev") or has(q, "fc")):
        return Gate(False, "not_held", "asks for a metric the model does not hold (profit, margin, share price, staff)")
    return Gate(True)


def route(question: str) -> Plan | None:
    q = norm(question)
    brands, comps, govs = find(q, BRANDS), find(q, COMPANIES), find(q, GOVS)
    app_cat = has(q, "app") or any(b in DELIVERY for b in brands)
    cola = has(q, "cola") or any(b not in DELIVERY for b in brands)
    reasons: list[str] = []
    penalty = 0.0
    if has(q, "unsupported"):
        penalty += 0.5; reasons.append("asks for a metric the model does not hold")
    if has(q, "why"):
        penalty += 0.25; reasons.append("asks for an explanation, not a figure")
    if has(q, "judge"):
        penalty += 0.2; reasons.append("asks for a judgement, not a figure")
    if has(q, "foreign") or unknown_names(question):
        penalty += 0.5; reasons.append("names something the model does not cover")
    if len(q.split()) > 22:
        penalty += 0.15; reasons.append("long question")
    if len(govs) > 1 or (len(brands) > 1 and not has(q, "boycott")) or len(comps) > 1:
        penalty += 0.3; reasons.append("compares several entities")
    if comps and brands:
        penalty += 0.3; reasons.append("mixes a company and a brand")

    def plan(intent, tool, args, base, why):
        return Plan(intent, tool, args, round(max(0.0, base - penalty), 2), [why] + reasons)

    if has(q, "help") and not (brands or comps or govs):
        return plan("help", "", {}, 0.95, "asks what the assistant covers")
    if govs:
        cat = "Delivery apps" if app_cat or (not cola and not brands) else "Soft drinks"
        base = 0.92 if (app_cat or cola) else 0.82
        return plan("gov_category", "search_share", {"governorate": govs[0], "category": cat}, base, f"governorate {govs[0]} + {cat}")
    if has(q, "fc") and (not comps or has(q, "pick")):
        if brands:
            return plan("forecast_brand", "forecast", {"company": "all"}, 0.4, "forecast asked for a brand; only companies have revenue forecasts")
        return plan("forecast_compare", "forecast", {"company": "all"}, 0.9, "forecast across companies")
    if comps and has(q, "fc"):
        return plan("forecast", "forecast", {"company": comps[0], "horizon": 6}, 0.92, f"forecast for {comps[0]}")
    if has(q, "move") and not comps:
        cat = "Delivery apps" if app_cat else "Soft drinks" if (brands or cola) else "Delivery apps"
        return plan("momentum", "search_trend", {"category": cat, "compare": True}, 0.9 if (app_cat or cola) else 0.82, f"growth within {cat}")
    if has(q, "boycott") or "Spiro Spathis" in brands:
        return plan("boycott", "search_trend", {"brands": ["Pepsi", "Spiro Spathis"], "start": "2023-01", "end": "2024-12"}, 0.9, "boycott effect")
    if comps:
        return plan("company_usd", "company_financials", {"company": comps[0], "unit": "USD"}, 0.88 if has(q, "rev") else 0.82,
                    f"revenue for {comps[0]}")
    if "talabat" in brands or (app_cat and not brands):
        return plan("delivery_size", "get_kpis", {"page": "delivery"}, 0.88, "delivery market size")
    if has(q, "sold"):
        return plan("where_sold", "where_sold", {"top_n": 6}, 0.88, "where drinks sell")
    if brands:
        return plan("where_brand", "search_share", {"brand": brands[0]}, 0.86, f"strongest governorates for {brands[0]}")
    return None
