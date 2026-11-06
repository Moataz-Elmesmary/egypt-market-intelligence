"""Six quarterly forecasters, a rolling-origin backtest and a top-3 inverse-error ensemble.

Every model works on log revenue (so seasonality and growth are multiplicative) and returns h quarters.
run_forecast() picks the ensemble on four selection origins, scores it on the last 4 quarters it never saw,
and builds an empirical 80% band from the ensemble's own misses at each horizon.
"""
from __future__ import annotations

import functools
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.forecasting.theta import ThetaModel
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX


def quiet(fn):
    """20-odd quarters is short for seasonal ARMA; statsmodels warns about starting values. The backtest judges each fit instead."""
    @functools.wraps(fn)
    def run(*a, **k):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return fn(*a, **k)
    return run


def quarter_labels(start: str, n: int) -> list[str]:
    y, q = int(start[:4]), int(start[-1])
    out = []
    for _ in range(n):
        out.append(f"{y}Q{q}")
        q += 1
        if q == 5:
            y, q = y + 1, 1
    return out


def fc_snaive(y, h):
    """Same quarter last year."""
    return np.array([y[len(y) - 4 + (i % 4)] for i in range(h)], float)


def fc_snaive_drift(y, h):
    """Same quarter last year, grown by the last 4 quarters vs the 4 before."""
    g = np.mean(y[-4:]) / np.mean(y[-8:-4])
    return np.array([y[len(y) - 4 + (i % 4)] * g ** (1 + i // 4) for i in range(h)], float)


@quiet
def fc_ets(y, h):
    """Holt-Winters: damped additive trend + additive season on log revenue."""
    m = ExponentialSmoothing(np.log(y), trend="add", damped_trend=True, seasonal="add",
                             seasonal_periods=4, initialization_method="estimated").fit()
    return np.exp(m.forecast(h))


@quiet
def fc_theta(y, h):
    s = pd.Series(np.log(y), index=pd.period_range("2000Q1", periods=len(y), freq="Q"))
    return np.exp(ThetaModel(s, period=4).fit().forecast(h).values)


@quiet
def fc_sarima(y, h):
    m = SARIMAX(np.log(y), order=(1, 0, 0), seasonal_order=(0, 1, 1, 4), trend="c").fit(disp=False)
    return np.exp(m.forecast(h))


def fc_ols(y, h):
    """Log-linear trend + quarter dummies."""
    n = len(y)
    t = np.arange(n + h)
    X = np.column_stack([np.ones(n + h), t] + [(t % 4 == k).astype(float) for k in range(1, 4)])
    beta, *_ = np.linalg.lstsq(X[:n], np.log(y), rcond=None)
    return np.exp(X[n:] @ beta)


MODELS = {
    "Seasonal naive": fc_snaive,
    "Seasonal naive + drift": fc_snaive_drift,
    "Holt-Winters (ETS)": fc_ets,
    "Theta": fc_theta,
    "SARIMA": fc_sarima,
    "Trend + season OLS": fc_ols,
}


def mape(a, f) -> float:
    a, f = np.asarray(a, float), np.asarray(f, float)
    return float(np.mean(np.abs(f - a) / a))


def run_forecast(start: str, y, H: int = 6):
    """Quarterly rows (actual, backtest, forecast, 80% band, each model's path) and the model leaderboard."""
    y = np.asarray(y, float)
    n = len(y)
    labels = quarter_labels(start, n + H)
    origins = [n - 8, n - 7, n - 6, n - 5, n - 4]   # fit on y[:o], forecast 4 ahead
    errs = {m: [] for m in MODELS}                    # weights come from the first four origins only
    hold = {}
    for m, fn in MODELS.items():
        for o in origins[:-1]:
            f = fn(y[:o], 4)
            k = min(4, n - o)
            errs[m].append(mape(y[o:o + k], f[:k]))
        f = fn(y[:n - 4], 4)
        hold[m] = (mape(y[n - 4:], f), f)             # the last 4 quarters are never used to choose
    sel = {m: float(np.mean(v)) for m, v in errs.items()}
    top = sorted(sel, key=sel.get)[:3]
    w = {m: (1 / sel[m]) for m in top}
    tot = sum(w.values())
    w = {m: w[m] / tot for m in top}
    ens_hold = sum(w[m] * hold[m][1] for m in top)
    pct = {h: [] for h in range(4)}                   # empirical band: the ensemble's own misses by horizon
    for o in origins:
        f = sum(w[m] * MODELS[m](y[:o], 4) for m in top)
        for h in range(min(4, n - o)):
            pct[h].append(abs(f[h] - y[o + h]) / y[o + h])
    band = [max(0.02, float(np.quantile(pct[min(h, 3)], 0.8))) for h in range(H)]
    fut = {m: fn(y, H) for m, fn in MODELS.items()}
    ens = sum(w[m] * fut[m] for m in top)
    board = [{"model": m, "mape_select": round(sel[m] * 100, 2), "mape_holdout": round(hold[m][0] * 100, 2),
              "weight": round(w.get(m, 0.0), 3)} for m in MODELS]
    board.append({"model": "Ensemble (top-3, 1/MAPE)", "mape_select": None,
                  "mape_holdout": round(mape(y[n - 4:], ens_hold) * 100, 2), "weight": 1.0})
    rows = []
    for i, lab in enumerate(labels):
        r = {"quarter": lab, "actual": float(y[i]) if i < n else None}
        if n - 4 <= i < n:
            r["backtest"] = round(float(ens_hold[i - (n - 4)]), 1)
        if i >= n:
            j = i - n
            r["forecast"] = round(float(ens[j]), 1)
            r["lo80"] = round(float(ens[j] * (1 - band[j])), 1)
            r["hi80"] = round(float(ens[j] * (1 + band[j])), 1)
            for m in MODELS:
                r[m] = round(float(fut[m][j]), 1)
        rows.append(r)
    return rows, board
