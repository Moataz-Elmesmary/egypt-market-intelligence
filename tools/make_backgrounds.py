"""Render the designed backgrounds of the native pages and their popups (2x PNGs), plus the logo.

Same design language as the portal page: sand canvas, the narrow dark rail with the pyramid mark,
white cards with a hairline border, teal + gold accents only. Each page background carries the rail,
the header text, the tile shells and the panel shells; the Power BI visuals sit transparent on top,
in the boxes from layout.py. Popups are transparent PNGs (dimmed page + card) toggled by bookmarks.
    python tools/make_backgrounds.py
"""
import asyncio
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

EG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EG))
import layout as L  # noqa: E402

OUT = EG / "pbip_assets"
src = (EG / "visual" / "src" / "core.ts").read_text(encoding="utf-8")
ICONS = dict(re.findall(r'^\s+(\w+): "([^"]+)",?$', src.split("const ICONS")[1].split("};")[0], flags=re.M))

NILE, NILE2, GOLD, INK, INK2, MUTED, LINE, SAND = "#0B6E69", "#12958B", "#C2922F", "#1C2928", "#4F5F5C", "#87918E", "#E8E1D4", "#F5F0E7"
RAIL_BG = "#13312F"

PYRAMID = ('<svg viewBox="0 0 40 36" width="{w}" height="{h}"><defs><linearGradient id="pg{u}" x1="0" y1="0" x2="1" y2="1">'
           '<stop offset="0" stop-color="#F6CF7A"/><stop offset="1" stop-color="#D08A1E"/></linearGradient></defs>'
           '<path d="M20 1 L39 35 H1 Z" fill="url(#pg{u})"/><path d="M20 1 L39 35 H24 Z" fill="#000" opacity=".16"/>'
           '<path d="M9.5 21 H30.5" stroke="{bg}" stroke-width="2.2"/><path d="M5 29 H35" stroke="{bg}" stroke-width="2.2"/></svg>')


def pyramid(w, h, bg, u):
    return PYRAMID.format(w=w, h=h, bg=bg, u=u)


def icon(name, color, size=16, stroke=1.9):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" '
            f'stroke-linecap="round" stroke-linejoin="round"><path d="{ICONS[name]}"/></svg>')


CSS = f"""
*{{box-sizing:border-box}}html,body{{margin:0;width:1280px;height:720px;font-family:'Segoe UI',sans-serif;overflow:hidden}}
.abs{{position:absolute}}
.canvas{{left:0;top:0;width:1280px;height:720px;background:{SAND}}}
.canvas:before{{content:"";position:absolute;right:-120px;top:-160px;width:520px;height:420px;border-radius:50%;
  background:radial-gradient(closest-side,rgba(18,149,139,.07),rgba(18,149,139,0))}}
.rail{{left:0;top:0;width:{L.SIDE}px;height:720px;background:{RAIL_BG}}}
.mark{{position:absolute;left:19px;top:16px;width:46px;height:46px;border-radius:14px;display:grid;place-items:center;
  background:linear-gradient(140deg,{NILE2},{NILE} 60%,#07514D);box-shadow:0 8px 18px -8px rgba(11,110,105,.7)}}
.nav{{position:absolute;left:8px;width:68px;border-radius:14px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;
  color:#A9C2BE;font:700 10.5px 'Segoe UI';text-align:center;line-height:1.1}}
.nav small{{font:600 9.5px 'Segoe UI';color:#7E9C97;direction:rtl}}
.nav.on{{background:linear-gradient(140deg,{NILE2},{NILE});color:#fff;box-shadow:0 8px 18px -8px rgba(18,149,139,.8)}}
.nav.on small{{color:#CDE8E4}}
.rfoot{{position:absolute;bottom:18px;width:100%;text-align:center}}
.rfoot b{{display:block;font:800 11px 'Segoe UI';color:#F0C870;letter-spacing:.08em}}.rfoot span{{font:600 9.5px 'Segoe UI';color:#7E9C97}}
.crumb{{font:700 9px 'Segoe UI';letter-spacing:.24em;color:#B5862F}}.crumb b{{color:{NILE};font-weight:800}}
.h1{{font:800 23px 'Segoe UI';color:{INK};white-space:nowrap;letter-spacing:-.005em}}
.h1 span{{font:700 16px 'Segoe UI';color:#B5862F;margin-left:10px}}
.sub{{font:500 11px 'Segoe UI';color:{MUTED};white-space:nowrap}}
.ask{{border-radius:20px;display:flex;align-items:center;justify-content:center;gap:8px;font:700 12.5px 'Segoe UI';color:#fff;
  background:linear-gradient(135deg,#118A81,{NILE} 55%,#07514D);box-shadow:0 10px 20px -10px rgba(11,110,105,.9)}}
.ask i{{width:22px;height:22px;border-radius:50%;background:rgba(255,255,255,.16);display:grid;place-items:center}}
.clear{{border-radius:16px;display:flex;align-items:center;justify-content:center;font:700 10.5px 'Segoe UI';color:{INK2};
  background:#FFFFFF;border:1px solid {LINE}}}
.card{{position:absolute;background:#fff;border:1px solid {LINE};border-radius:14px;box-shadow:0 6px 16px -12px rgba(60,45,20,.35)}}
.tile{{overflow:hidden}}
.tile:after{{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:linear-gradient({NILE2},{GOLD});opacity:.9}}
.tile .ic{{position:absolute;left:12px;top:10px;width:26px;height:26px;border-radius:8px;background:#E3F1EF;display:grid;place-items:center}}
.tile .lb{{position:absolute;left:46px;top:15px;right:30px;font:600 11px/1.2 'Segoe UI';color:{INK2};white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.tile .ar{{position:absolute;left:46px;top:23px;right:30px;font:600 9.5px 'Segoe UI';color:#B5862F;direction:rtl;text-align:left;white-space:nowrap}}
.tile .go{{position:absolute;right:9px;top:10px;width:17px;height:17px;border-radius:50%;background:#F3EEE5;display:grid;place-items:center;
  font:700 11px/1 'Segoe UI';color:{NILE}}}
.panel{{border-radius:16px}}
.panel .ic{{position:absolute;left:14px;top:12px;width:26px;height:26px;border-radius:8px;background:#E3F1EF;display:grid;place-items:center}}
.panel h3{{position:absolute;left:48px;top:9px;margin:0;font:700 13px 'Segoe UI';color:{INK};white-space:nowrap}}
.panel p{{position:absolute;left:48px;top:27px;margin:0;font:500 10px 'Segoe UI';color:{MUTED};white-space:nowrap}}
.read{{background:linear-gradient(180deg,#FFFFFF 0,#FFFFFF 60%,#FFFCF6 100%)}}
.read .ic{{background:linear-gradient(140deg,#D9AA4A,{GOLD});}}
.read h3 span{{font:700 11.5px 'Segoe UI';color:#B5862F;margin-left:6px}}
.dim{{left:0;top:0;width:1280px;height:720px;background:rgba(19,49,47,.46)}}
.pop{{position:absolute;border-radius:18px;background:#fff;border:1px solid {LINE};box-shadow:0 30px 60px -24px rgba(10,30,28,.55);overflow:hidden}}
.pop .eyebrow{{position:absolute;left:62px;top:13px;font:700 8.5px 'Segoe UI';letter-spacing:.24em;color:#B5862F}}
.pop h2{{position:absolute;left:62px;top:25px;margin:0;font:800 17px 'Segoe UI';color:{INK}}}
.pop .pic{{position:absolute;left:20px;top:14px;width:32px;height:32px;border-radius:10px;background:linear-gradient(140deg,{NILE2},{NILE});display:grid;place-items:center}}
.pop .rule{{position:absolute;left:20px;right:20px;top:58px;height:1px;background:#EFE8DC}}
.x{{position:absolute;border-radius:50%;background:#FBF8F2;border:1px solid {LINE};color:{INK2};display:grid;place-items:center;font:400 17px/1 'Segoe UI'}}
"""


def rail(active):
    items = "".join(
        f'<div class="nav{" on" if k == active else ""}" style="top:{y}px;height:{h}px">'
        f'{icon(ic, "#FFFFFF" if k == active else "#A9C2BE", 20)}<span>{en}</span><small>{ar}</small></div>'
        for (k, _x, y, _w, h), (_k, en, ar, ic) in zip(L.nav_boxes(), L.RAIL))
    return (f'<div class="abs rail"><div class="mark">{pyramid(28, 25, "#0B6E69", "r")}</div>{items}'
            f'<div class="rfoot"><b>PBI</b><span>live model</span></div></div>')


def header(p):
    x0 = L.X0
    ask = L.ASK
    out = (f'<div class="abs crumb" style="left:{x0}px;top:13px">EGYPT MARKET INTELLIGENCE&nbsp;&nbsp;·&nbsp;&nbsp;<b>0{p["n"]}</b> / 05</div>'
           f'<div class="abs h1" style="left:{x0 - 1}px;top:24px">{p["title"]}<span>{p["ar"]}</span></div>'
           f'<div class="abs sub" style="left:{x0}px;top:56px">{p["sub"]}</div>'
           f'<div class="abs ask" style="left:{ask[0]}px;top:{ask[1]}px;width:{ask[2]}px;height:{ask[3]}px">'
           f'<i>{icon("spark", "#FFFFFF", 13, 2.2)}</i>Ask AI</div>')
    if p.get("slicers"):
        c = L.CLEAR
        out += f'<div class="abs clear" style="left:{c[0]}px;top:{c[1]}px;width:{c[2]}px;height:{c[3]}px">Clear ✕</div>'
    return out


def tile(box, en, ar, ic):
    x, y, w, h = box
    return (f'<div class="card tile" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
            f'<div class="ic">{icon(ic, NILE, 15, 2)}</div><div class="lb">{en}</div><div class="go">›</div></div>')


def panel(box, title, sub, ic):
    x, y, w, h = box
    return (f'<div class="card panel" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"><div class="ic">{icon(ic, NILE, 15, 2)}</div>'
            f'<h3>{title}</h3><p>{sub}</p></div>')


def read_panel():
    x, y, w, h = L.READ
    return (f'<div class="card panel read" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"><div class="ic">{icon("spark", "#FFFFFF", 15, 2.2)}</div>'
            f'<h3>The read<span>الخلاصة</span></h3><p>Numbered notes from the model\'s own numbers</p></div>')


def page_html(key, p):
    tiles = "".join(tile(*t) for t in p["tiles"])
    panels = "".join(panel(*q) for q in p["panels"])
    return (f"<!doctype html><meta charset=utf-8><style>{CSS}</style><div class='abs canvas'></div>"
            f"{rail(key)}{header(p)}{tiles}{panels}{read_panel()}")


def popup_html(title, page_title):
    x, y, w, h = L.POPUP
    cx, cy, cw, ch = L.POPUP_CLOSE
    return (f"<!doctype html><meta charset=utf-8><style>{CSS}html,body{{background:transparent}}</style>"
            f"<div class='abs dim'></div><div class='pop' style='left:{x}px;top:{y}px;width:{w}px;height:{h}px'>"
            f"<div class='pic'>{icon('spark', '#FFFFFF', 16, 2.2)}</div><div class='eyebrow'>{page_title.upper()} · DETAILS</div>"
            f"<h2>{title}</h2><div class='rule'></div></div>"
            f"<div class='x' style='left:{cx}px;top:{cy}px;width:{cw}px;height:{ch}px'>×</div>")


def ai_html():
    x, y, w, h = L.AI_PANEL
    cx, cy, cw, ch = L.AI_CLOSE
    return (f"<!doctype html><meta charset=utf-8><style>{CSS}html,body{{background:transparent}}</style>"
            f"<div class='abs dim' style='background:rgba(19,49,47,.30)'></div>"
            f"<div class='pop' style='left:{x - 8}px;top:{y - 34}px;width:{w + 16}px;height:{h + 42}px'>"
            f"<div class='abs' style='left:16px;top:9px;font:800 12.5px Segoe UI;color:{INK}'>"
            f"<span style='color:{NILE}'>✦</span> Ask AI <span style='font-weight:600;color:#B5862F;margin-left:6px'>بالعربي أو بالإنجليزي</span></div></div>"
            f"<div class='x' style='left:{cx}px;top:{cy}px;width:{cw}px;height:{ch + 4}px;font-size:15px'>×</div>")


MARK = (f"<!doctype html><meta charset=utf-8><style>html,body{{margin:0;background:transparent}}"
        f".m{{width:92px;height:92px;border-radius:26px;display:grid;place-items:center;background:linear-gradient(140deg,{NILE2},{NILE} 60%,#07514D)}}</style>"
        f"<div class='m'>{pyramid(56, 50, '#0B6E69', 'm')}</div>")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", headless=True)
        pg = await b.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
        made = []
        for key, spec in L.PAGES.items():
            await pg.set_content(page_html(key, spec))
            await pg.screenshot(path=str(OUT / f"bg_{key}.png"))
            made.append(f"bg_{key}.png")
            for pk, title in spec["popups"].items():
                await pg.set_content(popup_html(title, spec["title"]))
                await pg.screenshot(path=str(OUT / f"pop_{key}_{pk}.png"), omit_background=True)
                made.append(f"pop_{key}_{pk}.png")
        await pg.set_content(ai_html())
        await pg.screenshot(path=str(OUT / "pop_ai.png"), omit_background=True)
        made.append("pop_ai.png")
        mp = await b.new_page(viewport={"width": 92, "height": 92}, device_scale_factor=2)
        await mp.set_content(MARK)
        await mp.screenshot(path=str(OUT / "logo_mark.png"), omit_background=True)
        await b.close()
    print("rendered:", ", ".join(made))


if __name__ == "__main__":
    asyncio.run(main())
