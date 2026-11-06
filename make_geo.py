"""Simplify geoBoundaries Egypt ADM1 into a small TS module for the custom visual."""
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent


def dp(pts, tol):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    n = np.hypot(*ab)
    if n < 1e-12:
        d = np.hypot(*(pts - a).T)
    else:
        d = np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / n
    i = int(np.argmax(d))
    if d[i] > tol:
        return np.vstack([dp(pts[: i + 1], tol)[:-1], dp(pts[i:], tol)])
    return np.vstack([a, b])


def area(r):
    x, y = r[:, 0], r[:, 1]
    return 0.5 * abs(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]))


g = json.loads((HERE / "raw" / "egy_adm1.geojson").read_text(encoding="utf-8"))
out, total = {}, 0
for f in g["features"]:
    geom = f["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    rings = []
    for poly in polys:
        r = np.asarray(poly[0], float)
        if area(r) < 0.004 and len(polys) > 1:
            continue
        s = dp(r, 0.006)
        if len(s) >= 4:
            rings.append([[round(float(x), 3), round(float(y), 3)] for x, y in s])
    out[f["properties"]["shapeISO"]] = rings
    total += sum(len(r) for r in rings)
ts = "// Egypt governorates, simplified from geoBoundaries EGY ADM1 (CC BY 4.0). [lon, lat] rings.\n"
ts += "export const EGYPT: Record<string, number[][][]> = " + json.dumps(out, separators=(",", ":")) + ";\n"
(HERE / "visual" / "src").mkdir(parents=True, exist_ok=True)
(HERE / "visual" / "src" / "egyptGeo.ts").write_text(ts, encoding="utf-8")
print("points", total, "bytes", len(ts))
