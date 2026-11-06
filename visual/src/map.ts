"use strict";

import * as d3 from "d3";
import powerbi from "powerbi-visuals-api";
import { Ctx, DataLike, T, Tip, clear, esc, fmtNum, h, mix, uid } from "./core";
import { EGYPT } from "./egyptGeo";

interface Gov {
    code: string; name: string; ar: string; region: string; urban: number;
    leader: string; leaderShare: number; leaderColor: string; runner: string; runnerShare: number;
    focus: string; focusShare: number; focusColor: string;
    id: powerbi.visuals.ISelectionId; feature: d3.GeoPermissibleObjects;
}

const BIG_LABELS = new Set(["EG-MT", "EG-WAD", "EG-BA", "EG-JS", "EG-SIN", "EG-ASN", "EG-MN", "EG-AST", "EG-SHG", "EG-KN"]);
const INSET_LABELS = new Set(["EG-C", "EG-GZ", "EG-ALX", "EG-SHR", "EG-DK", "EG-BH", "EG-KB", "EG-GH", "EG-PTS", "EG-IS", "EG-KFS", "EG-MNF", "EG-DT"]);
const selected = new Set<string>();

function feature(code: string): d3.GeoPermissibleObjects {
    const rings = (EGYPT[code] || []).map(r => {
        let a = 0;
        for (let i = 0; i < r.length - 1; i++) a += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1];
        return a > 0 ? [...r].reverse() : r;  // d3-geo wants clockwise exteriors
    });
    return { type: "Feature", properties: { code }, geometry: { type: "MultiPolygon", coordinates: rings.map(r => [r]) } } as unknown as d3.GeoPermissibleObjects;
}

export function renderMap(ctx: Ctx, d: DataLike) {
    clear(ctx.el);
    const root = h("div", "ep-map", undefined, ctx.el);
    const head = h("div", "ep-car-head", undefined, root);
    const titleEl = h("div", "ep-cardtitle", "", head);
    const note = h("div", "ep-car-note", ctx.subtitle || "Share of Google searches within the category, by governorate", head);

    const govs: Gov[] = d.rows.map((r, i) => ({
        code: d.s(r, "GovCode"), name: d.s(r, "Governorate"), ar: d.s(r, "GovernorateAR"), region: d.s(r, "Region"),
        urban: d.n(r, "UrbanPop"),
        leader: d.s(r, "Leader"), leaderShare: d.n(r, "Leader Share"), leaderColor: d.s(r, "Leader Color") || T.nile,
        runner: d.s(r, "Runner Up"), runnerShare: d.n(r, "Runner Share"),
        focus: d.s(r, "Focus Brand"), focusShare: d.n(r, "Focus Share"), focusColor: d.s(r, "Focus Color") || T.nile,
        id: d.table ? ctx.host.createSelectionIdBuilder().withTable(d.table, i).createSelectionId() : (null as unknown as powerbi.visuals.ISelectionId),
        feature: feature(d.s(r, "GovCode"))
    })).filter(g => EGYPT[g.code]);
    if (!govs.length) { h("div", "ep-empty", "Add governorate fields", root); return; }

    const focus = govs.find(g => g.focus)?.focus || "";
    const focusColor = T.nile;
    // harmonious palette: the most frequent leader is teal, the next gold
    const freq = new Map<string, number>();
    govs.forEach(g => freq.set(g.leader, (freq.get(g.leader) || 0) + 1));
    const order = [...freq.entries()].sort((a, b) => b[1] - a[1]).map(e => e[0]);
    const pal = new Map<string, string>(order.map((b, i) => [b, [T.nile, T.gold, "#8C7F6A"][Math.min(i, 2)]]));
    govs.forEach(g => { g.leaderColor = pal.get(g.leader) || T.nile; });
    titleEl.textContent = ctx.title || (focus ? `Where ${focus} is searched most` : "Who leads each governorate");
    const shares = govs.map(g => g.focusShare).filter(isFinite);
    const [lo, hi] = d3.extent(shares) as [number, number];
    const ramp = (v: number) => mix("#F2EBDD", focusColor, 0.12 + 0.88 * (hi > lo ? (v - lo) / (hi - lo) : 1));
    const fill = (g: Gov) => {
        if (focus) return isFinite(g.focusShare) ? ramp(g.focusShare) : "#EEE8DC";
        const lead = isFinite(g.runnerShare) ? g.leaderShare - g.runnerShare : g.leaderShare;
        return mix(g.leaderColor, "#F6F1E8", Math.max(0.05, 0.75 - lead * 1.4));
    };

    const W = ctx.width, H = Math.max(120, ctx.height - 46);
    const svg = d3.select(root).append("svg").attr("width", W).attr("height", H).attr("class", "ep-svg");
    const fc = { type: "FeatureCollection", features: govs.map(g => g.feature) } as unknown as d3.ExtendedFeatureCollection;
    // Delta inset sits beside the country on wide tiles, below it on tall ones
    const wide = W / H > 1.2;
    const insetW = wide ? Math.min(W * 0.4, 300) : W - 16;
    const insetH = wide ? insetW * 0.72 : Math.min(H * 0.38, insetW * 0.62);
    const ix = wide ? W - insetW - 8 : 8, iy = wide ? 8 : H - insetH - 30;
    const proj = d3.geoMercator().fitExtent(wide ? [[8, 8], [ix - 16, H - 30]] : [[8, 4], [W - 8, iy - 10]], fc);
    const path = d3.geoPath(proj);
    const tip = new Tip(root);

    const tipHtml = (g: Gov) => {
        const main = focus
            ? `<div class="ep-tip-r"><i style="background:${focusColor}"></i>${esc(focus)}<b>${(g.focusShare * 100).toFixed(0)}%</b></div>`
            : `<div class="ep-tip-r"><i style="background:${g.leaderColor}"></i>${esc(g.leader)}<b>${(g.leaderShare * 100).toFixed(0)}%</b></div>` +
              (g.runner ? `<div class="ep-tip-r"><i style="background:${pal.get(g.runner) || "#C6BDAD"}"></i>${esc(g.runner)}<b>${(g.runnerShare * 100).toFixed(0)}%</b></div>` : "");
        return `<div class="ep-tip-h">${esc(g.name)} <span class="ep-ar">${esc(g.ar)}</span></div><div class="ep-tip-sub">${esc(g.region)} · ${fmtNum(g.urban)} urban consumers</div>${main}`;
    };
    const onClick = (ev: MouseEvent, g: Gov) => {
        ev.stopPropagation();
        const multi = ev.ctrlKey || ev.metaKey;
        if (!multi) { const had = selected.has(g.code) && selected.size === 1; selected.clear(); if (!had) selected.add(g.code); }
        else if (selected.has(g.code)) selected.delete(g.code); else selected.add(g.code);
        const ids = govs.filter(x => selected.has(x.code)).map(x => x.id);
        if (d.table) { if (ids.length) ctx.selection.select(ids, false); else ctx.selection.clear(); }
        paint();
    };

    const drawLayer = (layer: d3.Selection<SVGGElement, unknown, null, undefined>, p: d3.GeoPath, labels: Set<string>, small: boolean) => {
        layer.selectAll("path").data(govs).join("path")
            .attr("d", g => p(g.feature as d3.GeoPermissibleObjects) || "")
            .attr("fill", g => fill(g)).attr("stroke", "#FFFFFF").attr("stroke-width", small ? 0.9 : 1.1).attr("class", "ep-gov").attr("data-code", g => (small ? "i-" : "") + g.code)
            .on("mousemove", (ev: MouseEvent, g) => tip.show(tipHtml(g), ev))
            .on("mouseleave", () => tip.hide())
            .on("click", onClick);
        layer.selectAll("text").data(govs.filter(g => labels.has(g.code))).join("text")
            .attr("class", "ep-maplab").attr("text-anchor", "middle")
            .attr("transform", g => { const c = p.centroid(g.feature as d3.GeoPermissibleObjects); return `translate(${c[0]},${c[1]})`; })
            .each(function (g) {
                const t = d3.select(this);
                t.selectAll("*").remove();
                t.append("tspan").attr("x", 0).attr("dy", "-0.15em").text(g.name);
                const v = focus ? g.focusShare : g.leaderShare;
                if (isFinite(v)) t.append("tspan").attr("x", 0).attr("dy", "1.15em").attr("class", "ep-maplab-v").text(`${(v * 100).toFixed(0)}%`);
            });
    };

    const main = svg.append("g");
    drawLayer(main, path, BIG_LABELS, false);

    // Nile Delta & Greater Cairo inset
    const delta = { type: "MultiPoint", coordinates: [[29.6, 29.85], [32.6, 31.6]] } as unknown as d3.GeoPermissibleObjects;
    const iproj = d3.geoMercator().fitExtent([[ix + 8, iy + 24], [ix + insetW - 8, iy + insetH - 6]], delta);
    const ipath = d3.geoPath(iproj);
    const cid = uid("clip");
    svg.append("defs").append("clipPath").attr("id", cid).append("rect").attr("x", ix).attr("y", iy).attr("width", insetW).attr("height", insetH).attr("rx", 10);
    const inset = svg.append("g");
    inset.append("rect").attr("x", ix).attr("y", iy).attr("width", insetW).attr("height", insetH).attr("rx", 10).attr("fill", "#FBF8F2").attr("stroke", T.line);
    const il = inset.append("g").attr("clip-path", `url(#${cid})`);
    drawLayer(il, ipath, INSET_LABELS, true);
    inset.append("text").attr("x", ix + 10).attr("y", iy + 15).attr("class", "ep-inset-t").text("Nile Delta & Greater Cairo · الدلتا والقاهرة الكبرى");
    // locator box on the main map
    const b0 = proj([29.6, 31.6])!, b1 = proj([32.6, 29.85])!;
    main.append("rect").attr("x", b0[0]).attr("y", b0[1]).attr("width", b1[0] - b0[0]).attr("height", b1[1] - b0[1])
        .attr("fill", "none").attr("stroke", T.ink2).attr("stroke-dasharray", "3 2").attr("rx", 3).style("pointer-events", "none");

    // ranked list in the free corner of wide tiles
    const listTop = iy + insetH + 14 + 46, listH = H - (iy + insetH + 14) - 40;
    if (wide && listH > 90) {
        const list = h("div", "ep-map-list", undefined, root);
        Object.assign(list.style, { left: ix + "px", top: listTop + "px", width: insetW + "px", height: listH + "px" });
        const rowsN = Math.max(3, Math.min(6, Math.floor((listH - 22) / 26)));
        if (focus) {
            h("div", "ep-map-lt", `Top governorates for ${focus}`, list);
            govs.filter(g => isFinite(g.focusShare)).sort((a, b) => b.focusShare - a.focusShare).slice(0, rowsN).forEach(g => {
                const r = h("div", "ep-map-row", undefined, list);
                h("span", "ep-map-g", g.name, r);
                const b = h("span", "ep-map-bar", undefined, r);
                const f = h("i", "", undefined, b); f.style.width = (g.focusShare / (hi || 1)) * 100 + "%"; f.style.background = focusColor;
                h("b", "", `${(g.focusShare * 100).toFixed(0)}%`, r);
            });
        } else {
            h("div", "ep-map-lt", "Tightest races · lead in points", list);
            govs.filter(g => isFinite(g.runnerShare)).sort((a, b) => (a.leaderShare - a.runnerShare) - (b.leaderShare - b.runnerShare)).slice(0, rowsN).forEach(g => {
                const r = h("div", "ep-map-row", undefined, list);
                h("span", "ep-map-g", g.name, r);
                const b = h("span", "ep-map-bar ep-map-duo", undefined, r);
                const a1 = h("i", "", undefined, b); a1.style.width = g.leaderShare * 100 + "%"; a1.style.background = g.leaderColor;
                const a2 = h("i", "", undefined, b); a2.style.width = g.runnerShare * 100 + "%"; a2.style.background = pal.get(g.runner) || "#C6BDAD";
                h("b", "", `${g.leader} +${((g.leaderShare - g.runnerShare) * 100).toFixed(0)}`, r);
            });
        }
    }

    // legend
    const lg = h("div", "ep-legend", undefined, root);
    if (focus) {
        h("span", "", `${(lo * 100).toFixed(0)}%`, lg);
        const bar = h("span", "ep-ramp", undefined, lg);
        bar.style.background = `linear-gradient(90deg, ${ramp(lo)}, ${ramp(hi)})`;
        h("span", "", `${(hi * 100).toFixed(0)}%`, lg);
    } else {
        const leaders = [...new Map(govs.map(g => [g.leader, g.leaderColor])).entries()];
        leaders.forEach(([name, col]) => { const c = h("span", "ep-chip", undefined, lg); const sw = h("i", "", undefined, c); sw.style.background = col; c.appendChild(document.createTextNode(name + " leads")); });
        h("span", "ep-legend-note", "darker = bigger lead", lg);
    }
    h("span", "ep-legend-note", "Click a governorate to filter the page", lg);

    const paint = () => {
        svg.selectAll<SVGPathElement, Gov>("path.ep-gov")
            .attr("opacity", g => !selected.size || selected.has(g.code) ? 1 : 0.28)
            .attr("stroke", g => selected.has(g.code) ? T.ink : "#FFFFFF")
            .attr("stroke-width", g => selected.has(g.code) ? 1.8 : 1);
    };
    svg.on("click", () => { selected.clear(); if (d.table) ctx.selection.clear(); paint(); });
    paint();
    if (ctx.first) svg.selectAll("path.ep-gov").attr("opacity", 0).transition().delay((_, i) => i * 18).duration(500).attr("opacity", 1);
    note.title = "Source: Google Trends; CAPMAS population and urban share";
}
