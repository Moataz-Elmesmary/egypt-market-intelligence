"""The numbers the README badges read (docs/metrics.json), recomputed from the code and the data.

    python tools/metrics.py           rewrite docs/metrics.json
    python tools/metrics.py --check   recompute and fail if a published number drifted (CI runs this)

Run it after build_egypt_data.py. The live evals need Power BI Desktop and a Gemini key, so CI
cannot rerun them: their last result is kept as published, with its date.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

EG = Path(__file__).absolute().parent.parent
OUT = EG / "docs" / "metrics.json"
PBIP = EG / "pbip"
NAME = "Egypt Market Intelligence"
sys.path.insert(0, str(EG / "backend"))


def compute() -> dict:
    d = json.loads((EG / "data" / "egypt_data.json").read_text(encoding="utf-8"))
    m: dict = {"tables": len(d), "rows": sum(len(v) for v in d.values())}

    lead = {}
    for b in d["Brand"]:
        c = b["Category"]
        if c not in lead or b["ShareOfSearch12M"] > lead[c]["ShareOfSearch12M"]:
            lead[c] = b
    m["search_leaders"] = {c: f'{b["Brand"]} {b["ShareOfSearch12M"] * 100:.1f}%' for c, b in lead.items()}

    comp = sorted(d["Company"], key=lambda r: r["EnsembleMAPE"])
    m["forecast"] = {r["Company"]: {"ensemble_mape": round(r["EnsembleMAPE"], 1), "mase": round(r["MASE"], 2),
                                    "band_80": r["Coverage"], "egp_2027_bn": round(r["Forecast2027"] / 1000, 1),
                                    "growth_2027_pct": round(r["Growth2027"] * 100, 1),
                                    "real_growth_2027_pct": round(r["RealGrowth2027"] * 100, 1)} for r in comp}
    m["best_ensemble_mape"] = f'{comp[0]["EnsembleMAPE"]:.1f}%'

    import evals  # routing only: the gate and the router, no model calls
    ok = sum((not got.startswith("instant")) if want == "not instant" else got == want
             for q, want in evals.CASES for got in [evals.decide(q)])
    m["routing"] = f"{ok}/{len(evals.CASES)}"

    sm = PBIP / f"{NAME}.SemanticModel" / "definition"
    m["measures"] = sum(sum(ln.startswith("\tmeasure ") for ln in t.read_text(encoding="utf-8").splitlines())
                        for t in (sm / "tables").glob("*.tmdl"))
    m["relationships"] = sum(ln.startswith("relationship ") for ln in (sm / "relationships.tmdl").read_text(encoding="utf-8").splitlines())
    m["pages"] = sum(p.is_dir() for p in (PBIP / f"{NAME}.Report" / "definition" / "pages").iterdir())

    tb = json.loads((EG / "mcp" / "token_benchmark.json").read_text(encoding="utf-8"))
    m["mcp_tools"] = tb["tools"]
    m["token_saving"] = f'{tb["saving_pct"]:.1f}%'
    return m


def drift(new, old, path=""):
    """Counts and labels must match exactly; forecast figures may move by a rounding step across platforms."""
    out = []
    if isinstance(old, dict):
        for k in old:
            if k not in new:
                out.append(f"{path}{k}: missing")
            else:
                out += drift(new[k], old[k], f"{path}{k}.")
    elif isinstance(old, float):
        if abs(new - old) > 0.3:
            out.append(f"{path[:-1]}: {old} -> {new}")
    elif new != old:
        out.append(f"{path[:-1]}: {old} -> {new}")
    return out


def main():
    m = compute()
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    if "live" in old:
        m["live"] = old["live"]
    if "--check" in sys.argv:
        bad = drift({k: v for k, v in m.items() if k != "live"}, {k: v for k, v in old.items() if k != "live"})
        for b in bad:
            print("drift:", b)
        print(f"metrics: {'OK' if not bad else f'{len(bad)} drifted'} · routing {m['routing']} · {m['tables']} tables · "
              f"{m['measures']} measures · best ensemble error {m['best_ensemble_mape']}")
        raise SystemExit(1 if bad else 0)
    OUT.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", OUT.relative_to(EG))


if __name__ == "__main__":
    main()
