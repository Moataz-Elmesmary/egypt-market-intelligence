"""Connect to the Egypt MCP server over stdio the way any agent would: list its tools, then call one.

    python mcp/demo_client.py [company]
The server runs the same tool code as the in-report gateway, so the numbers match the report.
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).with_name("egypt_mcp.py")


def payload(res):
    data = getattr(res, "structured_content", None) or getattr(res, "structuredContent", None)
    if data is None:
        data = json.loads(res.content[0].text)
    if isinstance(data, dict) and set(data) == {"result"}:
        data = data["result"]
    return data


async def main(company: str):
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            tools = (await s.list_tools()).tools
            print(f"connected to egypt-market-mcp · {len(tools)} tools\n")
            for t in tools:
                print(f"  {t.name:<18} {(t.description or '').strip().splitlines()[0][:78]}")
            print(f"\n> call forecast(company={company!r})\n")
            f = payload(await s.call_tool("forecast", {"company": company}))
            fy = f.get("fy_egp_m", {})
            for y in ("2025", "2026", "2027"):
                v = fy.get(y, fy.get(int(y)) if isinstance(fy, dict) else None)
                if v is not None:
                    print(f"  {y}  EGP {v / 1000:6.1f}B")
            sc = f.get("inflation_scenarios_2027_egp_m", {})
            print(f"\n  growth 2027 in pounds   {f.get('growth_2027_pct', 0):+.1f}%")
            print(f"  growth after inflation  {f.get('real_growth_2027_pct', 0):+.1f}%")
            if sc:
                print(f"  2027 at 9% / 20% CPI    EGP {sc['low_9pct'] / 1000:.1f}B / {sc['high_20pct'] / 1000:.1f}B")
            print(f"  error on unseen quarters {f.get('ensemble_mape_holdout_pct', 0):.1f}%   MASE {f.get('mase', 0):.2f}   80% band held {f.get('band_80_held', '')}")
            print("\n> call search_share(category='Delivery apps', governorate='Alexandria')\n")
            g = payload(await s.call_tool("search_share", {"category": "Delivery apps", "governorate": "Alexandria"}))
            for b in (g.get("brands") or [])[:4]:
                print(f"  {b.get('b', ''):<12} {b.get('s', 0) * 100:5.1f}%")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "Juhayna"))
