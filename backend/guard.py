"""Response guard: every figure in a model-written answer must trace back to a tool result.

A figure counts as traced when it equals a returned value, a unit change of one (share -> %,
millions -> billions), or a ratio, change, sum or difference of two returned values, within the
rounding the answer shows. Years, small counts and figures quoted from the question are skipped.
"""
from __future__ import annotations

import re
from bisect import bisect_left
from itertools import islice

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789.,")
NUM = re.compile(r"(?<![\w.])[-−]?\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> list[tuple[str, float, int]]:
    out = []
    for m in NUM.finditer(text.translate(AR_DIGITS)):
        raw = m.group(0).replace("−", "-")
        clean = raw.replace(",", "")
        try:
            v = float(clean)
        except ValueError:
            continue
        dec = len(clean.split(".")[1]) if "." in clean else 0
        out.append((m.group(0), v, dec))
    return out


def _flatten(x, acc: list[float]):
    if isinstance(x, bool):
        return
    if isinstance(x, (int, float)):
        acc.append(float(x))
    elif isinstance(x, dict):
        for v in x.values():
            _flatten(v, acc)
    elif isinstance(x, (list, tuple)):
        for v in x:
            _flatten(v, acc)
    elif isinstance(x, str):
        for _, v, _ in numbers_in(x):
            acc.append(v)


def candidates(results: list) -> set[float]:
    base: list[float] = []
    for r in results:
        _flatten(r, base)
    base = list(dict.fromkeys(v for v in base if v == v))[:220]
    out: set[float] = set()
    for v in base:
        out.update({v, v * 100, v / 1000, v / 1e6, abs(v)})
    for a in base:
        for b in islice(base, 220):
            if b:
                out.update({a / b, (a / b - 1) * 100, abs(a / b - 1) * 100, (1 - a / b) * 100})
            out.update({a - b, abs(a - b), a + b, (a - b) * 100, abs(a - b) * 100})
    return out


def _close(x: float, dec: int, sorted_c: list[float]) -> bool:
    tol = max(0.5 * 10 ** -dec + 1e-9, x * 0.006)
    i = bisect_left(sorted_c, x - tol)
    return i < len(sorted_c) and sorted_c[i] <= x + tol


def check(texts: list[str], results: list, question: str) -> tuple[int, list[str]]:
    """Return (figures checked, figures not traced)."""
    asked = {v for _, v, _ in numbers_in(question)}
    sorted_c = sorted({abs(c) for c in candidates(results)})
    checked, bad = 0, []
    for t in texts:
        for raw, v, dec in numbers_in(t or ""):
            if dec == 0 and (2000 <= v <= 2035 or abs(v) <= 12) or v in asked:
                continue
            checked += 1
            if not _close(abs(v), dec, sorted_c):
                bad.append(raw)
    return checked, bad
