"""Forecast diagnostics and the inflation-aware forecast, on top of the 6-model ensemble in forecast_models.py.

Egyptian revenue in pounds grows with inflation as much as with the business, so this module:
1. deflates quarterly revenue with the urban CPI (annual averages, 2021 = 100) to get real revenue,
2. runs the same 6 models on real revenue and blends the best 3 by inverse error,
3. re-inflates the real forecast under three stated inflation scenarios,
4. scores both methods on the same rolling origins with no hindsight (the real method assumes
   the trailing year's inflation carries on), and reports which one was more accurate,
5. measures what the headline MAPE hides: error by horizon, MASE against a seasonal naive,
   and how often the 80% band really held the actual (band built without the quarter it tests).
"""
from __future__ import annotations

import numpy as np

import forecast_models as fc

# Urban CPI, annual average change. 2021-2025: World Bank FP.CPI.TOTL.ZG (urban CPI) / CAPMAS;
# 2026: mean of the Jan-Sep 2026 year-on-year readings published by CAPMAS / CBE.
INFL = {2021: 0.052, 2022: 0.139, 2023: 0.339, 2024: 0.283, 2025: 0.141, 2026: 0.142}
SCENARIOS = [  # (name, annual inflation over the forecast horizon, note)
    ("Low", 0.09, "Back to the top of the CBE's 7% ± 2 target range"),
    ("Base", 0.139, "Stays at the latest reading (13.9%, Sep 2026)"),
    ("High", 0.20, "Renewed price pressure"),
]
US_INFL = 0.03   # for the pound's drift against the dollar (inflation differential)


def levels():
    out, p = {}, 100.0
    for y in sorted(INFL):
        if y > 2021:
            p *= 1 + INFL[y]
        out[y] = p
    return out


def cpi(labels):
    """Quarterly CPI (2021 = 100): log-linear between annual averages placed mid-year."""
    lv = levels()
    xs = np.array([y + 0.5 for y in sorted(lv)])
    ls = np.log([lv[y] for y in sorted(lv)])
    out = []
    for lab in labels:
        t = int(lab[:4]) + (int(lab[-1]) - 0.5) / 4
        out.append(float(np.exp(np.interp(t, xs, ls))))
    return np.array(out)


def blend(y, h, origins):
    """Fit the 6 models at each origin; pick the best 3 by mean error over the selection origins."""
    sel = {m: [] for m in fc.MODELS}
    for m, fn in fc.MODELS.items():
        for o in origins:
            f = fn(y[:o], 4)
            k = min(4, len(y) - o)
            sel[m].append(fc.mape(y[o:o + k], f[:k]))
    score = {m: float(np.mean(v)) for m, v in sel.items()}
    top = sorted(score, key=score.get)[:3]
    w = {m: 1 / score[m] for m in top}
    tot = sum(w.values())
    return {m: w[m] / tot for m in top}, score


def ens(y, h, w):
    return sum(wt * fc.MODELS[m](y, h) for m, wt in w.items())


def analyse(labels_hist, y_nom, H=6):
    """Everything for one company. labels_hist/y_nom: actual quarters only."""
    y_nom = np.asarray(y_nom, float)
    n = len(y_nom)
    lab_all = fc.quarter_labels(labels_hist[0], n + H)
    P = cpi(labels_hist)
    y_real = y_nom / P * 100
    origins = [n - 8, n - 7, n - 6, n - 5, n - 4]

    # same weight selection as the main forecast, on nominal and on real revenue
    w_nom, _ = blend(y_nom, 4, origins[:-1])
    w_real, _ = blend(y_real, 4, origins[:-1])

    # backtest both methods on every origin, no hindsight
    rows, err_nom, err_real = [], [], []
    for o in origins:
        k = min(4, n - o)
        f_nom = ens(y_nom[:o], 4, w_nom)[:k]
        trail = P[o - 1] / P[o - 5] - 1                      # last year's inflation, known at the origin
        path = P[o - 1] * (1 + trail) ** (np.arange(1, k + 1) / 4)
        f_real = ens(y_real[:o], 4, w_real)[:k] * path / 100
        for h in range(k):
            a = y_nom[o + h]
            err_nom.append(abs(f_nom[h] - a) / a)
            err_real.append(abs(f_real[h] - a) / a)
            rows.append(dict(origin=lab_all[o], horizon=h + 1, quarter=lab_all[o + h], actual=a,
                             nominal=f_nom[h], real_method=f_real[h], ape_nominal=abs(f_nom[h] - a) / a))
    mape_nom, mape_real = float(np.mean(err_nom)) * 100, float(np.mean(err_real)) * 100

    # honest band coverage: each quarter's band comes from the other origins' errors at that horizon
    inside = 0
    for r in rows:
        others = [x["ape_nominal"] for x in rows if x["horizon"] == r["horizon"] and x["origin"] != r["origin"]]
        b = max(0.02, float(np.quantile(others, 0.8))) if others else 0.05
        r["lo80"], r["hi80"] = r["nominal"] * (1 - b), r["nominal"] * (1 + b)
        r["inside"] = bool(r["lo80"] <= r["actual"] <= r["hi80"])
        inside += r["inside"]
    by_h = {h: float(np.mean([x["ape_nominal"] for x in rows if x["horizon"] == h])) * 100 for h in range(1, 5)}

    # MASE on the 4 held-out quarters: error vs the in-sample seasonal-naive error
    f_hold = ens(y_nom[:n - 4], 4, w_nom)
    scale = float(np.mean(np.abs(y_nom[4:n - 4] - y_nom[:n - 8])))
    mase = float(np.mean(np.abs(f_hold - y_nom[n - 4:])) / scale)

    # the inflation-aware forecast: real ensemble, re-inflated under each scenario
    real_fut = ens(y_real, H, w_real)
    fut_labels = lab_all[n:]
    scen = {}
    for name, rate, _ in SCENARIOS:
        path = P[-1] * (1 + rate) ** (np.arange(1, H + 1) / 4)
        scen[name] = real_fut * path / 100
    return dict(
        labels=lab_all, cpi=P, real=y_real, real_fut=real_fut, fut_labels=fut_labels, scen=scen,
        w_real=w_real, mape_nominal_bt=mape_nom, mape_real_bt=mape_real, by_h=by_h,
        coverage=(inside, len(rows)), mase=mase, backtest=rows,
    )


def scenario_factor(k, rate, base=0.139):
    """Shift the main (nominal) forecast k quarters ahead from the base inflation to a scenario's."""
    return ((1 + rate) / (1 + base)) ** (k / 4)


def fx_2027(fx_2026, rate):
    return fx_2026 * (1 + rate - US_INFL)
