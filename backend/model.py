"""Live DAX access to the Egypt Market Intelligence model open in Power BI Desktop.

Power BI Desktop runs a local Analysis Services engine per open report and writes its port to the
workspace folder. We try each port and keep the one whose model has the Egypt tables. Every query
the assistant runs is DAX against that engine, so a number in an answer is the number the report shows.
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

PBI_BIN = os.environ.get("PBI_BIN", r"C:\Program Files\Microsoft Power BI Desktop\bin")
sys.path.append(PBI_BIN)
import clr  # noqa: E402

clr.AddReference("Microsoft.PowerBI.AdomdClient")
from Microsoft.AnalysisServices.AdomdClient import AdomdCommand, AdomdConnection  # noqa: E402
from System import DBNull, DateTime  # noqa: E402

WORKSPACES = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Power BI Desktop" / "AnalysisServicesWorkspaces"
MARKER = "EVALUATE ROW ( \"n\", COUNTROWS ( 'Feed' ), \"g\", COUNTROWS ( 'SearchGeo' ) )"


class ModelOffline(Exception):
    """The Egypt report is not open in Power BI Desktop."""


class DaxError(Exception):
    """The engine rejected a query."""


def _ports() -> list[int]:
    out = []
    for f in sorted(WORKSPACES.glob("*/Data/msmdsrv.port.txt"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            out.append(int(f.read_bytes().decode("utf-16-le").strip("﻿\x00 \r\n")))
        except (OSError, ValueError):
            continue
    return out


def _py(v):
    if v is None or isinstance(v, type(DBNull.Value)):
        return None
    if isinstance(v, DateTime):
        return v.ToString("yyyy-MM-dd")
    if isinstance(v, (bool, int, float, str)):
        return v
    try:
        return float(v)
    except (TypeError, ValueError):
        return str(v)


def _clean(name: str) -> str:
    # 'Brand[Brand]' -> 'Brand', '[Share]' -> 'Share'
    return name.split("[", 1)[-1].rstrip("]") if "[" in name else name


class Model:
    def __init__(self):
        self._lock = threading.Lock()
        self._conn = None
        self.port = None

    def _connect(self):
        for port in _ports():
            conn = AdomdConnection(f"Data Source=localhost:{port}")
            try:
                conn.Open()
                cmd = AdomdCommand(MARKER, conn)
                r = cmd.ExecuteReader()
                r.Read()
                ok = _py(r.GetValue(0)) and _py(r.GetValue(1))
                r.Close()
                if ok:
                    self._conn, self.port = conn, port
                    return
            except Exception:
                pass
            try:
                conn.Close()
            except Exception:
                pass
        raise ModelOffline("Open 'Egypt Market Intelligence' in Power BI Desktop: the assistant reads the live model.")

    def query(self, dax: str) -> tuple[list[dict], float]:
        with self._lock:
            for attempt in (1, 2):
                if self._conn is None:
                    self._connect()
                t0 = time.perf_counter()
                try:
                    cmd = AdomdCommand(dax, self._conn)
                    r = cmd.ExecuteReader()
                    names = [_clean(r.GetName(i)) for i in range(r.FieldCount)]
                    rows = []
                    while r.Read():
                        rows.append({n: _py(r.GetValue(i)) for i, n in enumerate(names)})
                    r.Close()
                    return rows, (time.perf_counter() - t0) * 1000
                except Exception as exc:
                    msg = str(exc)
                    lost = type(exc).__name__ in ("AdomdConnectionException", "InvalidOperationException")
                    if lost and attempt == 1:
                        self._conn = None  # Power BI was reopened: find the new port once
                        continue
                    if lost:
                        raise ModelOffline(msg[:300]) from exc
                    raise DaxError(msg.split("\r\n")[0][:400]) from exc
        raise ModelOffline("model unavailable")


MODEL = Model()
