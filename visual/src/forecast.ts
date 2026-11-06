"use strict";

import * as d3 from "d3";
import { Ctx, DataLike, T, Tip, clear, h, uid } from "./core";

interface Q { q: string; t: Date; act: number; bt: number; fc: number; lo: number; hi: number; aU: number; fU: number; fx: number; }

let unit: "EGP" | "USD" = "EGP";

export function renderForecast(ctx: Ctx, d: DataLike) {
    clear(ctx.el);
    const root = h("div", "ep-fc", undefined, ctx.el);
    const qs: Q[] = d.rows.map(r => {
        const act = d.n(r, "RevenueEGP"), aU = d.n(r, "ActualUSD"), fc = d.n(r, "ForecastEGP"), fU = d.n(r, "ForecastUSD");
        return { q: d.s(r, "Quarter"), t: d.d(r, "QuarterEnd") as Date, act, bt: d.n(r, "BacktestEGP"), fc, lo: d.n(r, "Lo80"), hi: d.n(r, "Hi80"), aU, fU,
            fx: isFinite(act) && isFinite(aU) && aU ? act / aU : (isFinite(fc) && isFinite(fU) && fU ? fc / fU : NaN) };
    }).filter(x => x.t).sort((a, b) => +a.t - +b.t);
    const head = h("div", "ep-car-head ep-fc-head", undefined, root);
    const left = h("div", "", undefined, head);
    h("div", "ep-cardtitle", ctx.title || "Juhayna quarterly revenue and forecast", left);
    h("div", "ep-car-note", ctx.subtitle || "6 models, rolling-origin backtest, top-3 inverse-error ensemble, 80% band", left);
    const tg = h("div", "ep-toggle", undefined, head);
    (["EGP", "USD"] as const).forEach(u => {
        const b = h("button", "ep-tg" + (u === unit ? " on" : ""), u === "EGP" ? "EGP" : "USD", tg);
        b.onclick = (e) => { e.stopPropagation(); if (unit !== u) { unit = u; renderForecast({ ...ctx, first: true }, d); } };
    });
    if (!qs.length) { h("div", "ep-empty", "Add Juhayna fields", root); return; }

    const U = unit === "USD";
    const val = (x: Q, k: "act" | "fc" | "lo" | "hi" | "bt") => {
        const v = x[k];
        if (!U) return v;
        if (k === "act") return x.aU;
        if (k === "fc") return x.fU;
        return isFinite(v) && isFinite(x.fx) ? v / x.fx : NaN;
    };
    const W = ctx.width, H = Math.max(120, ctx.height - 48);
    const m = { l: 52, r: 120, t: 16, b: 46 };
    const svg = d3.select(root).append("svg").attr("width", W).attr("height", H).attr("class", "ep-svg");
    const x = d3.scaleTime().domain(d3.extent(qs, q => q.t) as [Date, Date]).range([m.l, W - m.r]);
    const maxV = d3.max(qs, q => Math.max(val(q, "act") || 0, val(q, "hi") || 0, val(q, "fc") || 0)) || 1;
    const y = d3.scaleLinear().domain([0, maxV * 1.04]).nice(6).range([H - m.b, m.t]);
    const fmt = (v: number) => U ? `$${v.toFixed(0)}M` : `${(v / 1000).toFixed(1)}B`;

    const g = svg.append("g");
    g.selectAll("line.gr").data(y.ticks(5)).join("line").attr("class", "gr")
        .attr("x1", m.l).attr("x2", W - m.r).attr("y1", v => y(v)).attr("y2", v => y(v)).attr("stroke", T.line).attr("stroke-dasharray", v => v ? "2 4" : "");
    g.selectAll("text.ya").data(y.ticks(5)).join("text").attr("class", "ep-axis ya").attr("x", m.l - 8).attr("y", v => y(v) + 4).attr("text-anchor", "end")
        .text(v => U ? `$${v}M` : (v === 0 ? "0" : `${v / 1000}B`));
    g.selectAll("text.xa").data(qs.filter(q => q.q.endsWith("Q4") || q.q.endsWith("Q2") && q === qs[0])).join("text").attr("class", "ep-axis xa")
        .attr("x", q => x(q.t)).attr("y", H - m.b + 16).attr("text-anchor", "middle").text(q => q.q.slice(0, 4));

    const actual = qs.filter(q => isFinite(val(q, "act")));
    const fut = qs.filter(q => isFinite(val(q, "fc")));
    const lastA = actual[actual.length - 1];
    const cut = x(lastA.t);
    g.append("rect").attr("x", cut).attr("y", m.t).attr("width", W - m.r - cut + 10).attr("height", H - m.t - m.b).attr("fill", T.goldTint).attr("opacity", 0.55);
    g.append("text").attr("class", "ep-ev").attr("x", cut + 8).attr("y", m.t + 13).text("Forecast →");

    const gid = uid("fg");
    const grad = svg.append("defs").append("linearGradient").attr("id", gid).attr("x1", 0).attr("x2", 0).attr("y1", 0).attr("y2", 1);
    grad.append("stop").attr("offset", 0).attr("stop-color", T.nile).attr("stop-opacity", 0.25);
    grad.append("stop").attr("offset", 1).attr("stop-color", T.nile).attr("stop-opacity", 0.02);
    const line = (k: "act" | "fc" | "bt") => d3.line<Q>().x(q => x(q.t)).y(q => y(val(q, k))).curve(d3.curveMonotoneX);
    g.append("path").datum(actual).attr("fill", `url(#${gid})`)
        .attr("d", d3.area<Q>().x(q => x(q.t)).y0(y(0)).y1(q => y(val(q, "act"))).curve(d3.curveMonotoneX));
    const band = [lastA, ...fut];
    g.append("path").datum(band).attr("fill", T.gold).attr("opacity", 0.2)
        .attr("d", d3.area<Q>().x(q => x(q.t)).y0(q => y(q === lastA ? val(q, "act") : val(q, "lo"))).y1(q => y(q === lastA ? val(q, "act") : val(q, "hi"))).curve(d3.curveMonotoneX));
    const pa = g.append("path").datum(actual).attr("d", line("act")).attr("fill", "none").attr("stroke", T.nile).attr("stroke-width", 2.8).attr("stroke-linecap", "round");
    const bt = qs.filter(q => isFinite(q.bt));
    if (!U && bt.length) g.append("path").datum(bt).attr("d", line("bt")).attr("fill", "none").attr("stroke", "#A99F8C").attr("stroke-width", 2).attr("stroke-dasharray", "5 4");
    const fpts = [{ ...lastA, fc: lastA.act, fU: lastA.aU }, ...fut];
    const pf = g.append("path").datum(fpts).attr("d", line("fc")).attr("fill", "none").attr("stroke", T.gold).attr("stroke-width", 2.6).attr("stroke-dasharray", "1 0");
    if (ctx.first) {
        [pa, pf].forEach((p, i) => {
            const len = (p.node() as SVGPathElement).getTotalLength();
            p.attr("stroke-dasharray", `${len} ${len}`).attr("stroke-dashoffset", len).transition().delay(i * 900).duration(i ? 900 : 1300).ease(d3.easeCubicOut).attr("stroke-dashoffset", 0);
        });
    }
    g.selectAll("circle.a").data(actual).join("circle").attr("class", "a").attr("cx", q => x(q.t)).attr("cy", q => y(val(q, "act"))).attr("r", 2.6).attr("fill", T.nile);
    g.selectAll("circle.f").data(fut).join("circle").attr("class", "f").attr("cx", q => x(q.t)).attr("cy", q => y(val(q, "fc"))).attr("r", 3.2).attr("fill", "#fff").attr("stroke", T.gold).attr("stroke-width", 2);

    // end labels
    const lastF = fut[fut.length - 1];
    const lab = (q: Q, k: "act" | "fc", color: string, text: string, dy: number) => {
        const gg = g.append("g").attr("transform", `translate(${x(q.t) + 10},${y(val(q, k)) + dy})`);
        gg.append("text").attr("class", "ep-endlab").attr("fill", color).text(text);
    };
    lab(lastA, "act", T.nile, `${lastA.q} ${fmt(val(lastA, "act"))}`, 22);
    if (lastF) {
        lab(lastF, "fc", "#8A6516", `${lastF.q} ${fmt(val(lastF, "fc"))}`, 4);
        g.append("text").attr("class", "ep-axis").attr("x", x(lastF.t) + 10).attr("y", y(val(lastF, "fc")) + 19)
            .text(`80%: ${fmt(val(lastF, "lo"))} to ${fmt(val(lastF, "hi"))}`);
    }

    // legend
    const lg = h("div", "ep-legend", undefined, root);
    const chip = (c: string, t: string, dash = false) => { const s = h("span", "ep-chip", undefined, lg); const i = h("i", dash ? "ep-dash" : "", undefined, s); i.style.background = dash ? "none" : c; i.style.borderColor = c; s.appendChild(document.createTextNode(t)); };
    chip(T.nile, U ? "Actual, USD at each year's average rate" : "Actual");
    if (!U) chip("#A99F8C", "Backtest on 4 unseen quarters", true);
    chip(T.gold, U ? "Forecast at 2026 average rate" : "Ensemble forecast + 80% band");

    const tip = new Tip(root);
    svg.append("rect").attr("x", m.l).attr("y", m.t).attr("width", W - m.l - m.r).attr("height", H - m.t - m.b).attr("fill", "transparent")
        .on("mousemove", (ev: MouseEvent) => {
            const [mx] = d3.pointer(ev);
            const i = d3.bisector((q: Q) => +q.t).center(qs, +x.invert(mx));
            const q = qs[Math.max(0, Math.min(qs.length - 1, i))];
            const rows = isFinite(val(q, "act"))
                ? `<div class="ep-tip-r"><i style="background:${T.nile}"></i>Actual<b>${fmt(val(q, "act"))}</b></div>` + (isFinite(q.bt) && !U ? `<div class="ep-tip-r"><i style="background:#A99F8C"></i>Backtest<b>${fmt(q.bt)}</b></div>` : "")
                : `<div class="ep-tip-r"><i style="background:${T.gold}"></i>Forecast<b>${fmt(val(q, "fc"))}</b></div><div class="ep-tip-sub">80% band ${fmt(val(q, "lo"))} to ${fmt(val(q, "hi"))}</div>`;
            tip.show(`<div class="ep-tip-h">${q.q}</div>${rows}`, ev);
        }).on("mouseleave", () => tip.hide());
}
