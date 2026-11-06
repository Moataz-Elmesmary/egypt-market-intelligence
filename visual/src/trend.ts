"use strict";

import * as d3 from "d3";
import { Ctx, DataLike, T, Tip, clear, esc, h, uid } from "./core";

interface Pt { t: Date; v: number; }
interface Series { brand: string; color: string; pts: Pt[]; last: number; }

const MON = d3.timeFormat("%b %Y");

export function renderTrend(ctx: Ctx, d: DataLike) {
    clear(ctx.el);
    const root = h("div", "ep-trend", undefined, ctx.el);
    const head = h("div", "ep-car-head", undefined, root);
    h("div", "ep-cardtitle", ctx.title || "Search interest over time", head);
    h("div", "ep-car-note", ctx.subtitle || "Google Trends, Egypt, monthly", head);

    const rows = d.rows.filter(r => !ctx.page || !d.has("Category") || d.s(r, "Category") === ctx.page);
    const by = new Map<string, Series>();
    const events = new Map<number, string>();
    rows.forEach(r => {
        const b = d.s(r, "Brand"), t = d.d(r, "Month"), v = d.has("Search Interest") ? d.n(r, "Search Interest") : d.n(r, "Interest");
        if (!b || !t || !isFinite(v)) return;
        if (!by.has(b)) by.set(b, { brand: b, color: d.s(r, "Color") || T.nile, pts: [], last: 0 });
        by.get(b)!.pts.push({ t, v });
        const ev = d.s(r, "Event");
        if (ev) events.set(+t, ev);
    });
    const series = [...by.values()].map(s => { s.pts.sort((a, b) => +a.t - +b.t); s.last = s.pts[s.pts.length - 1]?.v || 0; return s; })
        .filter(s => d3.max(s.pts, p => p.v)! > 0)
        .sort((a, b) => d3.sum(b.pts, p => p.v) - d3.sum(a.pts, p => p.v));
    if (!series.length) { h("div", "ep-empty", "Add Month, Brand and Interest", root); return; }
    const RAMP = [T.nile, T.gold, "#A99F8C", "#C6BDAD", "#DAD3C6"];
    series.forEach((s, i) => { s.color = RAMP[Math.min(i, RAMP.length - 1)]; });

    const W = ctx.width, H = Math.max(80, ctx.height - 44);
    const m = { l: 34, r: 92, t: 18, b: 24 };
    const svg = d3.select(root).append("svg").attr("width", W).attr("height", H).attr("class", "ep-svg");
    const all = series.flatMap(s => s.pts);
    const x = d3.scaleTime().domain(d3.extent(all, p => p.t) as [Date, Date]).range([m.l, W - m.r]);
    const vmax = d3.max(all, p => p.v) || 1;
    const y = d3.scaleLinear().domain([0, vmax <= 100 && vmax > 80 ? 100 : vmax * 1.08]).nice(4).range([H - m.b, m.t]);

    const g = svg.append("g");
    g.append("g").selectAll("line").data(y.ticks(4)).join("line")
        .attr("x1", m.l).attr("x2", W - m.r).attr("y1", v => y(v)).attr("y2", v => y(v))
        .attr("stroke", T.line).attr("stroke-dasharray", v => v === 0 ? "" : "2 4");
    g.append("g").selectAll("text").data(y.ticks(4)).join("text")
        .attr("x", m.l - 8).attr("y", v => y(v) + 4).attr("text-anchor", "end").attr("class", "ep-axis").text(v => String(v));
    g.append("g").selectAll("text").data(x.ticks(W < 520 ? 4 : 6)).join("text")
        .attr("x", v => x(v)).attr("y", H - 6).attr("text-anchor", "middle").attr("class", "ep-axis").text(v => d3.timeFormat("%Y")(v));

    // event markers
    const evg = g.append("g");
    const placed: [number, number, number][] = [];   // x0, x1, row
    [...events.entries()].sort((a, b) => a[0] - b[0]).forEach(([t, label]) => {
        const xx = x(new Date(t));
        evg.append("line").attr("x1", xx).attr("x2", xx).attr("y1", m.t).attr("y2", H - m.b).attr("stroke", T.gold).attr("stroke-dasharray", "3 3").attr("opacity", 0.8);
        const lab = evg.append("g");
        const tx = lab.append("text").attr("class", "ep-ev").attr("y", 10).text(label);
        const bb = (tx.node() as SVGTextElement).getBBox();
        lab.insert("rect", "text").attr("x", -3).attr("y", -1).attr("width", bb.width + 6).attr("height", 15).attr("rx", 4).attr("fill", "#FFFFFF").attr("opacity", 0.92);
        const x0 = xx + bb.width + 10 > W - m.r ? xx - bb.width - 8 : xx + 5;
        let row = 0;
        while (placed.some(([a, b, r]) => r === row && x0 < b + 6 && x0 + bb.width > a - 6)) row += 1;
        placed.push([x0, x0 + bb.width, row]);
        lab.attr("transform", `translate(${x0},${m.t + 2 + row * 18})`);
    });

    const line = d3.line<Pt>().x(p => x(p.t)).y(p => y(p.v)).curve(d3.curveMonotoneX);
    const area = d3.area<Pt>().x(p => x(p.t)).y0(y(0)).y1(p => y(p.v)).curve(d3.curveMonotoneX);
    const gid = uid("tg");
    const grad = svg.append("defs").append("linearGradient").attr("id", gid).attr("x1", 0).attr("x2", 0).attr("y1", 0).attr("y2", 1);
    grad.append("stop").attr("offset", 0).attr("stop-color", series[0].color).attr("stop-opacity", 0.22);
    grad.append("stop").attr("offset", 1).attr("stop-color", series[0].color).attr("stop-opacity", 0);
    g.append("path").datum(series[0].pts).attr("d", area).attr("fill", `url(#${gid})`);

    series.forEach((s, i) => {
        const p = g.append("path").datum(s.pts).attr("d", line).attr("fill", "none").attr("stroke", s.color)
            .attr("stroke-width", i === 0 ? 2.8 : i === 1 ? 2.3 : 1.7).attr("stroke-linejoin", "round").attr("stroke-linecap", "round");
        if (ctx.first) {
            const len = (p.node() as SVGPathElement).getTotalLength();
            p.attr("stroke-dasharray", `${len} ${len}`).attr("stroke-dashoffset", len)
                .transition().delay(i * 160).duration(1400).ease(d3.easeCubicOut).attr("stroke-dashoffset", 0)
                .on("end", function () { d3.select(this).attr("stroke-dasharray", null); });
        }
    });
    // direct end labels, nudged apart
    const ends = series.map(s => ({ s, y: y(s.last) }));
    ends.sort((a, b) => a.y - b.y);
    for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 15) ends[i].y = ends[i - 1].y + 15;
    const over = ends.length ? ends[ends.length - 1].y - (H - m.b) : 0;   // keep the stack inside the plot
    if (over > 0) ends.forEach(e => { e.y -= over; });
    ends.forEach(e => {
        const gg = g.append("g").attr("transform", `translate(${W - m.r + 8},${e.y})`);
        gg.append("circle").attr("r", 4).attr("cx", -8).attr("cy", y(e.s.last) - e.y).attr("fill", e.s.color).attr("stroke", "#fff").attr("stroke-width", 2);
        gg.append("text").attr("class", "ep-endlab").attr("y", 4).attr("x", 0).text(`${e.s.brand} ${e.s.last}`);
    });

    // hover crosshair
    const tip = new Tip(root);
    const months = [...new Set(all.map(p => +p.t))].sort((a, b) => a - b).map(t => new Date(t));
    const cross = g.append("line").attr("y1", m.t).attr("y2", H - m.b).attr("stroke", T.ink2).attr("stroke-width", 1).attr("opacity", 0);
    const dots = g.append("g");
    svg.append("rect").attr("x", m.l).attr("y", m.t).attr("width", W - m.l - m.r).attr("height", H - m.t - m.b).attr("fill", "transparent")
        .on("mousemove", (ev: MouseEvent) => {
            const [mx] = d3.pointer(ev);
            const t = x.invert(mx);
            const i = d3.bisector((dd: Date) => +dd).center(months, +t);
            const tt = months[Math.max(0, Math.min(months.length - 1, i))];
            const xx = x(tt);
            cross.attr("x1", xx).attr("x2", xx).attr("opacity", 0.5);
            const vals = series.map(s => ({ s, v: s.pts.find(p => +p.t === +tt)?.v ?? NaN })).filter(o => isFinite(o.v));
            dots.selectAll("circle").data(vals).join("circle").attr("cx", xx).attr("cy", o => y(o.v)).attr("r", 4.5)
                .attr("fill", o => o.s.color).attr("stroke", "#fff").attr("stroke-width", 2);
            const ev2 = events.get(+tt);
            tip.show(`<div class="ep-tip-h">${MON(tt)}</div>` + (ev2 ? `<div class="ep-tip-ev">${esc(ev2)}</div>` : "") +
                vals.sort((a, b) => b.v - a.v).map(o => `<div class="ep-tip-r"><i style="background:${o.s.color}"></i>${esc(o.s.brand)}<b>${o.v}</b></div>`).join(""),
                ev);
        })
        .on("mouseleave", () => { cross.attr("opacity", 0); dots.selectAll("circle").remove(); tip.hide(); });
}
