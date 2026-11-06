"""egypt-market-mcp: the in-report assistant's 7 tools as an MCP server.

The functions are imported from egypt/backend/tools.py, the same code the Power BI assistant runs,
so an MCP client (VS Code, Cursor, any agent) queries the open Power BI model with
the same DAX. The client's LLM never receives the tables: it calls a tool and gets a few rows back.

Run (stdio):  python egypt/mcp/egypt_mcp.py      (needs the report open in Power BI Desktop)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import tools as T  # noqa: E402
from model import DaxError, ModelOffline  # noqa: E402

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as FastMCP
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.exceptions import ToolError

mcp = FastMCP("egypt-market-mcp")
DOC = {d["name"]: d["description"] for d in T.DECLARATIONS}


def _run(name: str, **kw):
    try:
        c = T.run(name, {k: v for k, v in kw.items() if v not in (None, "", [])})
    except (ModelOffline, DaxError) as exc:  # the report is closed, or the engine refused: say so plainly
        raise ToolError(str(exc)) from exc
    if c.error:  # a bad argument: the client's model reads the reason and can retry
        raise ToolError(c.error)
    return c.result


def _doc(f):
    f.__doc__ = DOC[f.__name__]
    return f


@mcp.tool()
@_doc
def search_share(category: str = "", governorate: str = "", brand: str = "", top_n: int = 5) -> dict:
    return _run("search_share", category=category, governorate=governorate, brand=brand, top_n=top_n)


@mcp.tool()
@_doc
def search_trend(brands: list[str] | None = None, category: str = "", start: str = "2021-01", end: str = "2026-12",
                 every: int = 1, compare: bool = False) -> dict:
    return _run("search_trend", brands=brands, category=category, start=start, end=end, every=every, compare=compare)


@mcp.tool()
@_doc
def company_financials(company: str, unit: str = "EGP") -> dict:
    return _run("company_financials", company=company, unit=unit)


@mcp.tool()
@_doc
def forecast(company: str, horizon: int = 6) -> dict:
    return _run("forecast", company=company, horizon=horizon)


@mcp.tool()
@_doc
def get_kpis(page: str = "overview") -> dict:
    return _run("get_kpis", page=page)


@mcp.tool()
@_doc
def where_sold(top_n: int = 6) -> dict:
    return _run("where_sold", top_n=top_n)


@mcp.tool()
@_doc
def sources(ids: list[str] | None = None) -> dict:
    return _run("sources", ids=ids)


if __name__ == "__main__":
    mcp.run()
