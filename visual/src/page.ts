"use strict";

import * as d3 from "d3";
import { Ctx, DataLike, ObjRows, T, clear, countUp, h, icon, logoMark } from "./core";
import { LOGOS } from "./logos";
import { STYLE, renderCarousel } from "./carousel";
import { renderInsights, renderKpis } from "./simple";
import { renderTrend } from "./trend";
import { renderMap } from "./map";
import { renderForecast } from "./forecast";
import { renderAI } from "./ai";

// Full-page mode: one visual draws a whole report page as HTML (like an HTML-content portal),
// fed by the Feed table (Dataset, Seq, Json). Ask AI floats on every page.

type Rec = Record<string, any>;
interface Feed { [ds: string]: Rec[] }

const PAGES: Record<string, { title: string; ar: string; sub: string }> = {
    overview: { title: "Egypt Market Intelligence", ar: "السوق المصري بالأرقام", sub: "Soft drinks · delivery apps · where Egypt buys · public data to Oct 2026" },
    where: { title: "Where Egypt buys", ar: "خريطة الاستهلاك", sub: "27 governorates · price points · channels" },
    delivery: { title: "Delivery wars", ar: "سباق التوصيل", sub: "talabat · Breadfast · instashop · elmenus · Rabbit" },
    forecast: { title: "Revenue forecast", ar: "توقعات الإيرادات", sub: "Egypt's listed food makers · 20 quarters of filings each · 6 models" },
};

const st = { category: "Soft drinks", focus: "Breadfast", drawer: false, view: "", company: "Juhayna" };

function parse(d: DataLike): Feed {
    const f: Feed = {};
    d.rows.map(r => ({ ds: d.s(r, "Dataset"), seq: d.n(r, "Seq"), json: d.s(r, "Json") }))
        .sort((a, b) => a.seq - b.seq)
        .forEach(r => { try { (f[r.ds] = f[r.ds] || []).push(JSON.parse(r.json)); } catch { /* skip bad row */ } });
    return f;
}

function box(parent: HTMLElement, cls: string, x: number, y: number, w: number, hh: number) {
    const e = h("div", cls, undefined, parent);
    Object.assign(e.style, { left: x + "px", top: y + "px", width: w + "px", height: hh + "px" });
    return e;
}

function sub(ctx: Ctx, el: HTMLElement, w: number, hh: number, extra: Partial<Ctx> = {}): Ctx {
    return { ...ctx, el, width: w, height: hh, title: "", subtitle: "", page: "", ...extra };
}

export function logoPlate(parent: HTMLElement, brand: string, cls = "ep-plate") {
    const L = LOGOS[brand], S = STYLE[brand];
    const plate = h("div", cls, undefined, parent);
    if (L && S) {
        const onBody = S.logo === "white" || brand === "Rabbit";
        plate.style.background = onBody ? S.body : "#FFFFFF";
        const img = h("img", "", undefined, plate);
        img.src = L[S.logo === "white" ? "white" : "color"];
        img.alt = brand;
    } else {
        plate.classList.add("is-word");
        plate.style.background = S ? S.body : T.nile;
        plate.style.color = S ? S.ink : "#fff";
        plate.textContent = brand;
    }
    return plate;
}

// ---------------------------------------------------------------- page pieces
function header(ctx: Ctx, root: HTMLElement, key: string, W: number, onCat?: () => void) {
    const p = PAGES[key] || PAGES.overview;
    const hd = box(root, "ep-pg-head", 16, 10, W - 32, 58);
    const mark = h("div", "ep-mark", undefined, hd);
    mark.appendChild(logoMark(30));
    const txt = h("div", "ep-htxt", undefined, hd);
    const t = h("div", "ep-htitle", undefined, txt);
    h("span", "", p.title, t);
    h("span", "ep-htitle-ar", p.ar, t);
    h("div", "ep-hsub", p.sub, txt);
    const right = h("div", "ep-pg-right", undefined, hd);
    if (onCat) {
        const tg = h("div", "ep-seg", undefined, right);
        ([["Soft drinks", "المشروبات الغازية"], ["Delivery apps", "تطبيقات التوصيل"]] as const).forEach(([c, ar]) => {
            const b = h("button", "ep-seg-b" + (st.category === c ? " on" : ""), undefined, tg);
            h("span", "", c, b); h("small", "", ar, b);
            b.onclick = () => { if (st.category !== c) { st.category = c; tg.querySelectorAll(".ep-seg-b").forEach(x => x.classList.toggle("on", x === b)); onCat(); } };
        });
    }
    const live = h("div", "ep-live", undefined, right);
    h("i", "", undefined, live);
    h("span", "", "Power BI semantic model · 18 tables · 17 sources", live);
}

function ticker(root: HTMLElement, f: Feed, x: number, y: number, w: number) {
    const tk = box(root, "ep-ticker", x, y, w, 30);
    const lab = h("div", "ep-ticker-lab", undefined, tk);
    lab.appendChild(icon("spark", 14, "#fff", 2));
    h("span", "", "INSIGHTS", lab);
    const track = h("div", "ep-ticker-track", undefined, tk);
    const items: [string, string][] = (f.insight || []).map(r => [String(r.Title), String(r.TitleAR)]);
    (f.kpi || []).filter(k => k.Page !== "overview").slice(0, 6).forEach(k => items.push([`${k.Label}: ${k.Display}`, String(k.LabelAR)]));
    const run = h("div", "ep-ticker-run", undefined, track);
    for (let rep = 0; rep < 2; rep++) items.forEach(([en, ar]) => {
        const it = h("span", "ep-tick", undefined, run);
        h("b", "", en, it);
        const a = h("span", "ep-tick-ar", ar, it); a.dir = "rtl";
    });
    run.style.animationDuration = `${Math.max(40, items.length * 7)}s`;
}

function trendFor(f: Feed, brand: string) {
    return (f.trend || []).find(t => t.b === brand) as { m: string[]; v: number[] } | undefined;
}

function spark(parent: HTMLElement, vals: number[], color: string, w: number, hh: number) {
    const svg = d3.select(parent).append("svg").attr("width", w).attr("height", hh).attr("class", "ep-spark");
    const x = d3.scaleLinear().domain([0, vals.length - 1]).range([2, w - 2]);
    const y = d3.scaleLinear().domain([0, Math.max(1, d3.max(vals) || 1)]).range([hh - 3, 3]);
    svg.append("path").datum(vals).attr("fill", color).attr("opacity", 0.12)
        .attr("d", d3.area<number>().x((_, i) => x(i)).y0(hh).y1(v => y(v)).curve(d3.curveMonotoneX));
    const p = svg.append("path").datum(vals).attr("fill", "none").attr("stroke", color).attr("stroke-width", 1.8)
        .attr("d", d3.line<number>().x((_, i) => x(i)).y(v => y(v)).curve(d3.curveMonotoneX));
    const len = (p.node() as SVGPathElement).getTotalLength();
    p.attr("stroke-dasharray", `${len} ${len}`).attr("stroke-dashoffset", len).transition().duration(1100).attr("stroke-dashoffset", 0);
    svg.append("circle").attr("cx", x(vals.length - 1)).attr("cy", y(vals[vals.length - 1])).attr("r", 2.6).attr("fill", color);
}

// Competitor board: logos, share bar, 24-month sparkline, change vs 2021.
function board(el: HTMLElement, f: Feed, cat: string, w: number, hh: number) {
    clear(el);
    const head = h("div", "ep-card-h", undefined, el);
    h("div", "ep-cardtitle", cat === "Delivery apps" ? "Who Egypt orders from" : "Who Egypt reaches for", head);
    h("div", "ep-car-note", "Share of Google searches, last 12 months · 24-month trend", head);
    const brands = (f.brand || []).filter(b => b.Category === cat).sort((a, b) => b.ShareOfSearch12M - a.ShareOfSearch12M);
    const max = d3.max(brands, b => b.ShareOfSearch12M) || 1;
    const list = h("div", "ep-board", undefined, el);
    const rowH = Math.max(46, Math.min(70, (hh - 70) / Math.max(1, brands.length)));
    brands.forEach((b, i) => {
        const r = h("div", "ep-brow" + (i === 0 ? " lead" : ""), undefined, list);
        r.style.height = rowH + "px";
        r.style.animationDelay = `${i * 90}ms`;
        h("div", "ep-brank", String(i + 1), r);
        logoPlate(r, b.Brand);
        const nm = h("div", "ep-bname", undefined, r);
        h("b", "", b.Brand, nm);
        const second = h("div", "", undefined, nm);
        h("span", "ep-bar-ar", b.BrandAR, second);
        second.appendChild(document.createTextNode(" · " + String(b.Company)));
        const bar = h("div", "ep-bbar", undefined, r);
        const fill = h("i", "", undefined, bar);
        fill.style.background = i === 0 ? T.nile : "#7FB8B3";
        requestAnimationFrame(() => { fill.style.width = Math.max(1.5, (b.ShareOfSearch12M / max) * 100) + "%"; });
        const val = h("b", "ep-bval", undefined, r);
        countUp(val, (b.ShareOfSearch12M * 100).toFixed(1) + "%", 900, i * 90);
        const sp = h("div", "ep-bspark", undefined, r);
        const tr = trendFor(f, b.Brand);
        if (tr) spark(sp, tr.v.slice(-24), i === 0 ? T.nile : "#8C7F6A", Math.max(60, w * 0.16), rowH - 18);
        const ratio = b.Interest2021 > 0.05 ? b.InterestLast12M / b.Interest2021 : NaN;
        const ch = h("span", "ep-bdelta", "", r);
        if (isFinite(ratio)) {
            ch.textContent = ratio >= 1 ? `${ratio.toFixed(1)}x` : `−${((1 - ratio) * 100).toFixed(0)}%`;
            ch.classList.add(ratio >= 1.15 ? "up" : ratio <= 0.87 ? "down" : "flat");
            ch.title = "Search interest, last 12 months vs 2021";
        } else { ch.textContent = b.InterestLast12M > 0.05 ? "new" : "—"; ch.classList.add("flat"); }
    });
}

function urbanBars(el: HTMLElement, f: Feed) {
    clear(el);
    const head = h("div", "ep-card-h", undefined, el);
    h("div", "ep-cardtitle", "Where the urban shoppers are", head);
    h("div", "ep-car-note", "Urban consumers by governorate, millions · CAPMAS", head);
    const g = [...(f.gov || [])].sort((a, b) => b.UrbanPop - a.UrbanPop).slice(0, 8);
    const max = g[0]?.UrbanPop || 1;
    const list = h("div", "ep-ubars", undefined, el);
    g.forEach((r, i) => {
        const row = h("div", "ep-ubar", undefined, list);
        const lab = h("div", "ep-ulab", undefined, row);
        h("b", "", r.Governorate, lab);
        h("span", "", r.GovernorateAR, lab);
        const bar = h("div", "ep-bbar", undefined, row);
        const fill = h("i", "", undefined, bar);
        fill.style.background = i < 3 ? T.nile : "#7FB8B3";
        window.setTimeout(() => { fill.style.width = (r.UrbanPop / max) * 100 + "%"; }, 80 + i * 70);
        h("b", "ep-bval", (r.UrbanPop / 1e6).toFixed(1) + "M", row);
    });
}

function companyChips(root: HTMLElement, f: Feed, x: number, y: number, w: number, onPick: () => void) {
    const wrap = box(root, "ep-chips", x, y, w, 44);
    (f.company || []).forEach(c => {
        const b = h("button", "ep-cchip" + (st.company === c.Company ? " on" : ""), undefined, wrap);
        h("b", "", c.Company, b);
        h("span", "", c.CompanyAR, b);
        b.onclick = () => { st.company = c.Company; wrap.querySelectorAll(".ep-cchip").forEach(z => z.classList.toggle("on", z === b)); onPick(); };
    });
}

function leaderboard(el: HTMLElement, f: Feed, company: string) {
    clear(el);
    const head = h("div", "ep-card-h", undefined, el);
    h("div", "ep-cardtitle", `Model leaderboard · ${company}`, head);
    h("div", "ep-car-note", "Error on 4 quarters the models never saw (MAPE)", head);
    const m = [...(f.model || [])].filter(r => r.Company === company).sort((a, b) => a.MAPE_Holdout - b.MAPE_Holdout);
    const max = d3.max(m, r => r.MAPE_Holdout) || 1;
    const list = h("div", "ep-ubars", undefined, el);
    m.forEach((r, i) => {
        const ens = String(r.Model).startsWith("Ensemble");
        const row = h("div", "ep-ubar" + (ens ? " ens" : ""), undefined, list);
        const lab = h("div", "ep-ulab", undefined, row);
        h("b", "", ens ? "Ensemble (top 3)" : r.Model, lab);
        h("span", "", r.Weight > 0 && !ens ? `weight ${(r.Weight * 100).toFixed(0)}% of ensemble` : ens ? "what the report uses" : "not in top 3 — shown for comparison", lab);
        const bar = h("div", "ep-bbar", undefined, row);
        const fill = h("i", "", undefined, bar);
        fill.style.background = ens ? T.gold : r.Weight > 0 ? T.nile : "#CFC6B6";
        window.setTimeout(() => { fill.style.width = (r.MAPE_Holdout / max) * 100 + "%"; }, 80 + i * 70);
        h("b", "ep-bval", r.MAPE_Holdout.toFixed(1) + "% err", row);
    });
}

function brandChips(root: HTMLElement, f: Feed, x: number, y: number, w: number, onPick: () => void) {
    const wrap = box(root, "ep-chips", x, y, w, 48);
    (f.brand || []).filter(b => b.Category === "Delivery apps").forEach(b => {
        const c = h("button", "ep-lchip" + (st.focus === b.Brand ? " on" : ""), undefined, wrap);
        logoPlate(c, b.Brand, "ep-plate sm");
        c.title = b.Brand;
        c.onclick = () => { st.focus = b.Brand; wrap.querySelectorAll(".ep-lchip").forEach(x => x.classList.toggle("on", x === c)); onPick(); };
    });
}

function geoRows(f: Feed, cat: string, focus: string) {
    const brands = (f.brand || []).filter(b => b.Category === cat);
    const geo = new Map((f.geo || []).map(g => [g.b, g.s as Record<string, number>]));
    return (f.gov || []).map(g => {
        const sh = brands.map(b => ({ b: b.Brand, s: geo.get(b.Brand)?.[g.GovCode] ?? NaN })).filter(x => isFinite(x.s)).sort((a, b) => b.s - a.s);
        return {
            GovCode: g.GovCode, Governorate: g.Governorate, GovernorateAR: g.GovernorateAR, Region: g.Region, UrbanPop: g.UrbanPop,
            Leader: sh[0]?.b, "Leader Share": sh[0]?.s, "Leader Color": T.nile, "Runner Up": sh[1]?.b, "Runner Share": sh[1]?.s,
            "Focus Brand": focus || "", "Focus Share": focus ? geo.get(focus)?.[g.GovCode] : NaN, "Focus Color": T.nile
        };
    });
}

function trendRows(f: Feed, cat: string) {
    const ev = new Map((f.event || []).filter(e => e.c === cat).map(e => [e.m, e.en]));
    const out: Rec[] = [];
    (f.trend || []).filter(t => t.c === cat).forEach(t => t.m.forEach((m: string, i: number) => out.push({
        Month: m + "-01T00:00:00", Brand: t.b, Category: cat, "Search Interest": t.v[i], Event: ev.get(m) || ""
    })));
    return out;
}

function carouselRows(f: Feed, cat: string) {
    return (f.brand || []).filter(b => b.Category === cat).map(b => ({
        Brand: b.Brand, BrandAR: b.BrandAR, Company: b.Company, Origin: b.Origin, Shape: b.Shape,
        "Share of Search": b.ShareOfSearch12M, "Interest 2021": b.Interest2021, "Interest Last 12M": b.InterestLast12M
    }));
}

function aiNode(ctx: Ctx, root: HTMLElement, f: Feed, W: number, H: number) {
    const dw = Math.min(480, Math.max(360, W * 0.38));
    const shade = box(root, "ep-shade", 0, 0, W, H);
    const drawer = box(root, "ep-drawer", W - dw, 0, dw, H);
    const dh = h("div", "ep-drawer-h", undefined, drawer);
    const lg = h("span", "ep-ai-logo sm", undefined, dh);
    lg.appendChild(icon("spark", 16, "#fff", 2));
    const tt = h("div", "", undefined, dh);
    h("b", "", "Ask AI", tt);
    h("small", "", "English or Egyptian Arabic · بالعربي أو بالإنجليزي", tt);
    const x = h("button", "ep-drawer-x", "×", dh);
    const body = h("div", "ep-drawer-b", undefined, drawer);
    const fab = box(root, "ep-fab", W - 150, H - 62, 134, 46);
    const fi = h("span", "ep-fab-ic", undefined, fab);
    fi.appendChild(icon("spark", 18, "#fff", 2));
    h("span", "", "Ask AI", fab);
    h("i", "ep-fab-ring", undefined, fab);
    let built = false;
    const open = (v: boolean) => {
        st.drawer = v;
        root.classList.toggle("ai-open", v);
        if (v && !built) { built = true; renderAI(sub(ctx, body, dw, H - 64, { page: "drawer" }), new ObjRows(f.kb || [])); }
        if (v) window.setTimeout(() => (body.querySelector(".ep-ai-input") as HTMLInputElement)?.focus(), 350);
    };
    fab.onclick = () => open(true);
    x.onclick = () => open(false);
    shade.onclick = () => open(false);
    if (st.drawer) open(true);
}

// ---------------------------------------------------------------- pages
const NAV: [string, string, string, string][] = [
    ["overview", "Overview", "نظرة عامة", "spark"], ["where", "Map", "الخريطة", "pin"],
    ["delivery", "Delivery", "التوصيل", "bike"], ["forecast", "Forecast", "التوقعات", "up"],
];
const RAIL = 84;

// Portal navigation: a left rail switches views inside the visual (one report page, many views).
function rail(outer: HTMLElement, H: number, current: string, go: (k: string) => void) {
    const r = box(outer, "ep-rail", 0, 0, RAIL, H);
    const logo = h("div", "ep-mark ep-rail-mark", undefined, r);
    logo.appendChild(logoMark(28));
    NAV.forEach(([k, en, ar, ic]) => {
        const b = h("button", "ep-rail-b" + (k === current ? " on" : ""), undefined, r);
        b.appendChild(icon(ic, 22, k === current ? "#FFFFFF" : T.ink2, 1.9));
        h("span", "", en, b);
        h("small", "", ar, b);
        b.onclick = () => { if (k !== current) go(k); };
    });
    const foot = h("div", "ep-rail-foot", undefined, r);
    h("b", "", "PBI", foot);
    h("span", "", "live model", foot);
}

export function renderPage(ctx: Ctx, d: DataLike) {
    clear(ctx.el);
    const f = parse(d);
    if (!st.view) st.view = PAGES[ctx.page] ? ctx.page : "overview";
    const outer = h("div", "ep-page", undefined, ctx.el);
    outer.style.width = ctx.width + "px"; outer.style.height = ctx.height + "px";
    rail(outer, ctx.height, st.view, k => { st.view = k; renderPage({ ...ctx, first: true }, d); });
    const W = ctx.width - RAIL, H = ctx.height, P = 16, G = 12;
    const root = box(outer, "ep-pg-content", RAIL, 0, W, H);
    root.setAttribute("data-view", st.view);
    const key = st.view;
    const inner = W - 2 * P;

    if (key === "overview") {
        let shelf: HTMLElement, brd: HTMLElement;
        const top = 74, kTop = top + 38, mTop = kTop + 96 + G, mH = H - mTop - P;
        const lw = Math.round(inner * 0.55), rw = inner - lw - G;
        const draw = () => {
            renderCarousel(sub(ctx, shelf, lw, mH, { title: st.category === "Delivery apps" ? "The delivery shelf · share of search" : "The cola shelf · share of search", subtitle: "Google Trends, Egypt · last 12 months · click a pack" }), new ObjRows(carouselRows(f, st.category)));
            board(brd, f, st.category, rw, mH);
        };
        header(ctx, root, key, W, draw);
        ticker(root, f, P, top, inner);
        renderKpis(sub(ctx, box(root, "ep-slot", P, kTop, inner, 96), inner, 96, { page: "overview", first: ctx.first }), new ObjRows(f.kpi || []));
        shelf = box(root, "ep-card", P, mTop, lw, mH);
        brd = box(root, "ep-card", P + lw + G, mTop, rw, mH);
        draw();
    } else if (key === "where") {
        const kTop = 76, mTop = kTop + 96 + G, mH = H - mTop - P;
        const lw = Math.round(inner * 0.6), rw = inner - lw - G, ub = Math.round(mH * 0.54);
        const mapEl = box(root, "ep-card", P, mTop, lw, mH);
        const draw = () => renderMap(sub(ctx, mapEl, lw, mH, { title: st.category === "Delivery apps" ? "Which app leads each governorate" : "Pepsi or Coca-Cola, governorate by governorate", subtitle: "Share of Google searches within the category · hover a governorate" }), new ObjRows(geoRows(f, st.category, "")));
        header(ctx, root, key, W, draw);
        renderKpis(sub(ctx, box(root, "ep-slot", P, kTop, inner, 96), inner, 96, { page: "where", first: ctx.first }), new ObjRows(f.kpi || []));
        draw();
        urbanBars(box(root, "ep-card", P + lw + G, mTop, rw, ub), f);
        const ins = box(root, "ep-card", P + lw + G, mTop + ub + G, rw, mH - ub - G);
        renderInsights(sub(ctx, ins, rw, mH - ub - G, { page: "where", title: "Field notes" }), new ObjRows(f.insight || []));
    } else if (key === "delivery") {
        const kTop = 76, mTop = kTop + 96 + G, mH = H - mTop - P;
        const lw = Math.round(inner * 0.6), rw = inner - lw - G, th = Math.round(mH * 0.6);
        header(ctx, root, key, W);
        renderKpis(sub(ctx, box(root, "ep-slot", P, kTop, inner, 96), inner, 96, { page: "delivery", first: ctx.first }), new ObjRows(f.kpi || []));
        const tr = box(root, "ep-card", P, mTop, lw, th);
        renderTrend(sub(ctx, tr, lw, th, { title: "Who Egypt searches for when ordering", subtitle: "Google Trends, Egypt · talabat's peak month = 100" }), new ObjRows(trendRows(f, "Delivery apps")));
        const ins = box(root, "ep-card", P, mTop + th + G, lw, mH - th - G);
        renderInsights(sub(ctx, ins, lw, mH - th - G, { page: "delivery", title: "What the data says" }), new ObjRows(f.insight || []));
        const mapEl = box(root, "ep-card", P + lw + G, mTop + 56, rw, mH - 56);
        const draw = () => renderMap(sub(ctx, mapEl, rw, mH - 56, { title: `Where ${st.focus} is searched most`, subtitle: "Share of delivery-app searches by governorate" }), new ObjRows(geoRows(f, "Delivery apps", st.focus)));
        brandChips(root, f, P + lw + G, mTop, rw, draw);
        draw();
    } else {
        const kTop = 76, mTop = kTop + 96 + G, mH = H - mTop - P;
        const lw = Math.round(inner * 0.66), rw = inner - lw - G, lh = Math.round(mH * 0.55);
        header(ctx, root, key, W);
        renderKpis(sub(ctx, box(root, "ep-slot", P, kTop, inner, 96), inner, 96, { page: "forecast", first: ctx.first }), new ObjRows(f.kpi || []));
        const fc = box(root, "ep-card", P, mTop + 52, lw, mH - 52);
        const lbEl = box(root, "ep-card", P + lw + G, mTop, rw, lh);
        const draw = () => {
            const c = (f.company || []).find(x => x.Company === st.company) || {};
            renderForecast(sub(ctx, fc, lw, mH - 52, { title: `${st.company} quarterly revenue and forecast`, subtitle: `${c.Segment || ""} · 6 models, rolling-origin backtest, top-3 inverse-error ensemble, 80% band` }),
                new ObjRows((f.jq || []).filter(r => r.Company === st.company)));
            leaderboard(lbEl, f, st.company);
        };
        companyChips(root, f, P, mTop, lw, draw);
        draw();
        const ins = box(root, "ep-card", P + lw + G, mTop + lh + G, rw, mH - lh - G);
        renderInsights(sub(ctx, ins, rw, mH - lh - G, { page: "forecast", title: "Read this first" }), new ObjRows(f.insight || []));
    }
    aiNode(ctx, outer, f, ctx.width, H);
}
