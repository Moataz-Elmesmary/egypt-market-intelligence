"use strict";

import * as d3 from "d3";
import { Ctx, DataLike, T, clear, h, icon, isArabic } from "./core";

// The in-report assistant. Questions go to the local gateway (egypt/backend/app.py), which runs a
// scope gate, an instant router (no tokens), or Gemini with the 7 DAX tools, then checks every
// figure against the rows the tools returned. The card shows the route, each tool call with its
// DAX, how many figures were traced, and the trace id that finds the call in the log.

const API = "http://localhost:8765";

interface Bar { label: string; v: number; color?: string; }
interface Chart { kind: "bars" | "lines"; fmt: string; bars?: Bar[]; lines?: { name: string; color: string; pts: [string, number][] }[]; band?: { x: string; lo: number; hi: number }[]; }
interface Chip { label: string; value: string; dir: "up" | "down" | "flat"; }
interface CallOut { tool: string; args: Record<string, unknown>; dax: string[]; rows: number; ms: number; error?: string; }
interface Reply {
    trace_id: string; route: string; intent?: string; confidence?: number; reasons?: string[]; model?: string;
    title: string; text: string; chips: Chip[]; chart?: Chart | null; try_instead?: string[];
    calls: CallOut[]; tokens: { prompt: number; output: number; total: number }; naive_tokens: number;
    checked?: number; untraced?: string[]; sources?: string[]; latency_ms: number; cached_from?: string;
    conv?: string; question?: string; rating?: number | null;
}
interface Conv { conv: string; first: string; n: number; started: string; last: string; }

const FMT: Record<string, (v: number) => string> = {
    pct: v => `${(v * 100).toFixed(0)}%`,
    usd_m: v => `$${v.toFixed(0)}M`,
    egp_m: v => `${(v / 1000).toFixed(1)}B`,
    m: v => `${v.toFixed(1)}M`,
    num: v => v.toFixed(0),
    index: v => v.toFixed(0),
};

function miniChart(host: HTMLElement, c: Chart, w: number, rtl: boolean) {
    const svg = d3.select(host).append("svg").attr("class", "ep-ai-chart").attr("direction", "ltr").style("direction", "ltr");
    const fmt = FMT[c.fmt] || String;
    if (c.kind === "bars" && c.bars) {
        const H = c.bars.length * 26 + 6;
        svg.attr("width", w).attr("height", H);
        const lw = 112, x = d3.scaleLinear().domain([0, d3.max(c.bars, b => b.v) || 1]).range([0, w - lw - 70]);
        const base = rtl ? w - lw - 6 : lw;
        c.bars.forEach((b, i) => {
            const g = svg.append("g").attr("transform", `translate(0,${i * 26 + 4})`);
            g.append("text").attr("class", "ep-ai-bl").attr("y", 14).attr("text-anchor", "end").attr("x", rtl ? w - 4 : lw - 8).text(b.label);
            const bw = Math.max(2, x(b.v));
            g.append("rect").attr("y", 3).attr("height", 15).attr("rx", 4).attr("fill", b.color || T.nile)
                .attr("x", base).attr("width", 0)
                .transition().delay(i * 70).duration(600).ease(d3.easeCubicOut).attr("width", bw).attr("x", rtl ? base - bw : base);
            g.append("text").attr("class", "ep-ai-bv").attr("y", 15).attr("x", rtl ? base - bw - 6 : base + bw + 6).attr("text-anchor", rtl ? "end" : "start")
                .text(fmt(b.v)).attr("opacity", 0).transition().delay(380 + i * 70).attr("opacity", 1);
        });
        return;
    }
    if (c.kind === "lines" && c.lines) {
        const H = c.lines.length > 2 ? 190 : 160, m = { l: 40, r: 12, t: 10, b: 20 };
        svg.attr("width", w).attr("height", H);
        const per = [...new Set(c.lines.flatMap(l => l.pts.map(p => p[0])).concat((c.band || []).map(b => b.x)))].sort();
        const x = d3.scalePoint<string>().domain(per).range([m.l, w - m.r]);
        const top = d3.max(c.lines.flatMap(l => l.pts.map(p => p[1])).concat((c.band || []).map(b => b.hi))) || 1;
        const y = d3.scaleLinear().domain([0, top]).nice(4).range([H - m.b, m.t]);
        y.ticks(4).forEach(t => {
            svg.append("line").attr("x1", m.l).attr("x2", w - m.r).attr("y1", y(t)).attr("y2", y(t)).attr("stroke", T.line).attr("stroke-dasharray", t ? "2 4" : "");
            svg.append("text").attr("class", "ep-axis").attr("x", m.l - 6).attr("y", y(t) + 4).attr("text-anchor", "end").text(c.fmt === "egp_m" ? `${t / 1000}B` : String(t));
        });
        [per[0], per[Math.floor(per.length / 2)], per[per.length - 1]].forEach(p => svg.append("text").attr("class", "ep-axis").attr("x", x(p)!).attr("y", H - 4).attr("text-anchor", "middle").text(p));
        if (c.band && c.band.length) {
            svg.append("path").datum(c.band).attr("fill", T.gold).attr("opacity", 0)
                .attr("d", d3.area<{ x: string; lo: number; hi: number }>().x(d => x(d.x)!).y0(d => y(d.lo)).y1(d => y(d.hi)).curve(d3.curveMonotoneX))
                .transition().delay(500).duration(600).attr("opacity", 0.18);
        }
        c.lines.forEach((l, i) => {
            const p = svg.append("path").datum(l.pts).attr("fill", "none").attr("stroke", l.color).attr("stroke-width", 2.4)
                .attr("stroke-dasharray", i === 1 && c.band ? "5 4" : null)
                .attr("d", d3.line<[string, number]>().x(d => x(d[0])!).y(d => y(d[1])).curve(d3.curveMonotoneX));
            const len = (p.node() as SVGPathElement).getTotalLength();
            if (!(i === 1 && c.band)) p.attr("stroke-dasharray", `${len} ${len}`).attr("stroke-dashoffset", len).transition().delay(i * 250).duration(800).attr("stroke-dashoffset", 0);
            const last = l.pts[l.pts.length - 1];
            if (last) svg.append("text").attr("class", "ep-ai-bv").attr("fill", l.color === "#C6BDAD" ? T.ink2 : l.color).attr("x", Math.min(w - 60, x(last[0])! - 4)).attr("y", y(last[1]) - 8 + (i === 3 ? 22 : 0)).attr("text-anchor", "end").text(l.name);
        });
    }
}

function reveal(el: HTMLElement, text: string, done: () => void) {
    const words = text.split(" ");
    let i = 0;
    const tick = () => {
        i += 2;
        el.textContent = words.slice(0, i).join(" ");
        if (i < words.length) window.setTimeout(tick, 22); else done();
    };
    tick();
}

const ROUTE: Record<string, [string, string, string]> = {   // label, icon, css
    instant: ["Instant route · no LLM", "bolt", "is-instant"],
    llm: ["Gemini tool calling", "spark", "is-llm"],
    cache: ["Cached today · no LLM", "bolt", "is-instant"],
    out_of_scope: ["Out of scope · refused", "shield", "is-refused"],
    not_held: ["Not in the model · refused", "shield", "is-refused"],
    not_covered: ["Brand not covered · refused", "shield", "is-refused"],
    security: ["Blocked by the scope gate", "shield", "is-refused"],
    error: ["Gateway error", "shield", "is-refused"],
};

const SUGGEST = [
    "مين بيكبر ومين بيتراجع في تطبيقات التوصيل؟",
    "Compare Pepsi and Coca-Cola in Cairo vs Alexandria",
    "مين أكتر تطبيق توصيل بيدوّروا عليه في القاهرة؟",
    "Is Domty's forecast reliable enough to plan on?",
    "توقع إيرادات جهينة 2027",
    "What is Juhayna's profit margin?",
];

const chat: { q: string; a: Reply }[] = [];
// the conversation lives in the gateway (traces.db), so every Ask AI popup on every page shows the same thread
const state = { conv: "", fresh: false, convs: [] as Conv[] };

function argText(a: Record<string, unknown>) {
    return Object.entries(a).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ");
}

export function renderAI(ctx: Ctx, _d: DataLike) {
    clear(ctx.el);
    const root = h("div", "ep-ai", undefined, ctx.el);
    const side = h("div", "ep-ai-side", undefined, root);
    const main = h("div", "ep-ai-main", undefined, root);

    const brand = h("div", "ep-ai-brand", undefined, side);
    const ic = h("span", "ep-ai-logo", undefined, brand);
    ic.appendChild(icon("spark", 22, "#fff", 2));
    const bt = h("div", "", undefined, brand);
    h("div", "ep-ai-title", "Ask AI", bt);
    h("div", "ep-ai-sub", "English or Egyptian Arabic · بالعربي أو بالإنجليزي", bt);
    h("div", "ep-ai-h", "Try asking · جرّب تسأل", side);
    const sug = h("div", "ep-ai-sug", undefined, side);
    SUGGEST.forEach(s => { const b = h("button", "ep-ai-chip", s, sug); b.dir = "auto"; b.onclick = () => ask(s); });

    const tb = h("div", "ep-ai-tb", undefined, main);
    const histBtn = h("button", "ep-ai-tbb", undefined, tb);
    histBtn.appendChild(icon("box", 12, T.nile, 2));
    h("span", "", "History", histBtn);
    const histN = h("span", "ep-ai-tbn", "0", histBtn);
    const newBtn = h("button", "ep-ai-tbb", "+ New chat", tb);
    const turnInfo = h("span", "ep-ai-tbt", "", tb);
    const histPanel = h("div", "ep-ai-hist", undefined, main);
    histBtn.onclick = () => histPanel.classList.toggle("on");

    if (ctx.page === "drawer" || ctx.width < 640) {
        root.classList.add("is-drawer");
        const chips = h("div", "ep-ai-chips", undefined, main);
        SUGGEST.slice(0, 4).forEach(s => { const b = h("button", "ep-ai-chip", s, chips); b.dir = "auto"; b.onclick = () => ask(s); });
    }
    const log = h("div", "ep-ai-log", undefined, main);
    const bar = h("div", "ep-ai-bar", undefined, main);
    const input = h("input", "ep-ai-input", undefined, bar);
    input.placeholder = "Ask about Egypt's market… اسأل بالعربي";
    input.dir = "auto";
    const sendBtn = h("button", "ep-ai-send", undefined, bar);
    sendBtn.appendChild(icon("rocket", 18, "#fff", 2));

    const empty = () => {
        if (chat.length) return;
        const e = h("div", "ep-ai-empty", undefined, log);
        const ii = h("div", "ep-ai-empty-ic", undefined, e);
        ii.appendChild(icon("spark", 34, T.nile, 1.6));
        h("div", "ep-ai-empty-t", "What do you want to know about the Egyptian market?", e);
        h("div", "ep-ai-empty-ar", "ماذا تريد أن تعرف عن السوق المصري؟", e);
    };
    const scroll = () => { log.scrollTop = log.scrollHeight; };

    // a card that waits for the gateway, then fills in
    const addTurn = (q: string, pending: Promise<Reply> | Reply, animate: boolean) => {
        log.querySelector(".ep-ai-empty")?.remove();
        const rtl = isArabic(q);
        const u = h("div", "ep-ai-q" + (rtl ? " rtl" : ""), q, log);
        u.dir = "auto";
        const card = h("div", "ep-ai-a" + (rtl ? " rtl" : "") + (animate ? " is-live" : ""), undefined, log);
        card.dir = rtl ? "rtl" : "ltr";
        const route = h("div", "ep-ai-route", undefined, card);
        route.dir = "ltr";
        route.appendChild(icon("box", 13, T.nile, 2));
        h("span", "", "Routing…", route);
        const think = h("span", "ep-ai-dots", undefined, route);
        h("i", "", undefined, think); h("i", "", undefined, think); h("i", "", undefined, think);
        const callsEl = h("div", "ep-ai-calls", undefined, card);
        callsEl.dir = "ltr";
        const ttl = h("div", "ep-ai-ttl", "", card);
        const txt = h("div", "ep-ai-text", "", card);
        const chipsEl = h("div", "ep-ai-kpis", undefined, card);
        const ch = h("div", "ep-ai-ch", undefined, card);
        const tryEl = h("div", "ep-ai-try", undefined, card);
        const foot = h("div", "ep-ai-foot", undefined, card);
        foot.dir = "ltr";
        scroll();

        Promise.resolve(pending).then(a => {
            think.remove();
            const [label, ico, css] = ROUTE[a.route] || ROUTE.error;
            route.className = "ep-ai-route " + css;
            route.replaceChildren();
            route.appendChild(icon(ico, 13, a.route === "llm" ? T.gold : a.route.startsWith("instant") || a.route === "cache" ? T.nile : "#C0412C", 2));
            const extra = a.route === "llm" ? ` · ${a.model}` : a.confidence != null && a.route === "instant" ? ` · confidence ${a.confidence.toFixed(2)}` : "";
            h("span", "", label + extra, route);
            h("span", "ep-ai-ms", `${(a.latency_ms / 1000).toFixed(a.latency_ms < 1000 ? 2 : 1)} s`, route);
            a.calls.forEach((c, i) => {
                const row = h("div", "ep-ai-call", undefined, callsEl);
                row.style.animationDelay = `${i * 90}ms`;
                h("b", "", c.tool, row);
                h("span", "", `(${argText(c.args)})`, row);
                h("small", "", c.error ? "bad arguments, retried" : `${c.dax.length} DAX · ${c.rows} rows · ${c.ms.toFixed(0)} ms`, row);
                if (c.dax.length) {
                    const t = h("button", "ep-ai-dax-b", "DAX", row);
                    const pre = h("pre", "ep-ai-dax", c.dax.join("\n\n"), callsEl);
                    t.onclick = () => { pre.classList.toggle("on"); scroll(); };
                }
            });
            const finish = () => {
                (a.chips || []).forEach((c, i) => {
                    const k = h("div", "ep-ai-kpi " + c.dir, undefined, chipsEl);
                    k.style.animationDelay = `${i * 80}ms`;
                    h("b", "", c.value, k);
                    h("span", "", c.label, k);
                });
                if (a.chart) miniChart(ch, a.chart, Math.min(520, main.clientWidth - 60), rtl);
                (a.try_instead || []).forEach(s => { const b = h("button", "ep-ai-chip", s, tryEl); b.dir = "auto"; b.onclick = () => ask(s); });
                if (a.route === "llm" || a.route === "cache") {
                    const bad = (a.untraced || []).length;
                    h("span", bad ? "ep-ai-guard bad" : "ep-ai-guard", bad ? `⚠ ${bad} figure(s) not found in tool results` : `✓ ${a.checked || 0}/${a.checked || 0} figures traced to DAX rows`, foot);
                }
                if (a.sources && a.sources.length) h("span", "", `Source: ${a.sources.join("; ")}`, foot);
                const tk = a.tokens.total;
                h("span", "ep-ai-tk", tk ? `${tk.toLocaleString()} tokens · pasting the workbook would cost ${a.naive_tokens.toLocaleString()} per question`
                    : `0 tokens · pasting the workbook would cost ${a.naive_tokens.toLocaleString()}`, foot);
                const fb = h("span", "ep-ai-trace", undefined, foot);
                h("span", "", `trace #${a.trace_id}`, fb);
                ["▲", "▼"].forEach((s, i) => {
                    const b = h("button", "ep-ai-fb" + (a.rating === (i ? -1 : 1) ? " on" : ""), s, fb);
                    b.onclick = () => {
                        fetch(`${API}/api/feedback`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ trace_id: a.trace_id, rating: i ? -1 : 1 }) })
                            .then(() => { fb.querySelectorAll(".ep-ai-fb").forEach(x => x.classList.remove("on")); b.classList.add("on"); }).catch(() => undefined);
                    };
                });
                scroll();
                window.setTimeout(scroll, 700);
            };
            if (animate) { ttl.textContent = a.title; reveal(txt, a.text, finish); }
            else { ttl.textContent = a.title; txt.textContent = a.text; finish(); }
            scroll();
        });
    };

    const view = () => (ctx.el.closest(".ep-page")?.querySelector(".ep-pg-content") as HTMLElement | null)?.dataset.view || ctx.page || "";

    const info = () => {
        histN.textContent = String(state.convs.length);
        turnInfo.textContent = chat.length ? `${chat.length} in this chat · follow-ups keep context` : "New chat";
    };
    const redraw = () => {
        log.replaceChildren();
        chat.forEach(t => addTurn(t.q, t.a, false));
        empty();
        info();
    };
    const drawHist = () => {
        histPanel.replaceChildren();
        h("div", "ep-ai-hh", "Recent chats · المحادثات الأخيرة", histPanel);
        if (!state.convs.length) h("div", "ep-ai-hrow", "No chats yet", histPanel);
        state.convs.forEach(c => {
            const b = h("button", "ep-ai-hrow" + (c.conv === state.conv ? " on" : ""), undefined, histPanel);
            const t = h("b", "", c.first || "…", b);
            t.dir = "auto";
            h("small", "", `${c.n} question${c.n > 1 ? "s" : ""} · ${(c.last || "").replace("T", " ").slice(0, 16)}`, b);
            b.onclick = () => { histPanel.classList.remove("on"); state.fresh = false; load(c.conv, true); };
        });
        info();
    };
    const load = (id: string, force = false) =>
        fetch(`${API}/api/history?conv=${encodeURIComponent(id)}`)
            .then(r => r.json() as Promise<{ conv: string; turns: Reply[]; conversations: Conv[] }>)
            .then(hst => {
                state.convs = hst.conversations || [];
                if (state.fresh && !force) { drawHist(); return; }
                const last = chat.length ? chat[chat.length - 1].a.trace_id : "";
                const same = hst.conv === state.conv && hst.turns.length === chat.length && (!hst.turns.length || hst.turns[hst.turns.length - 1].trace_id === last);
                state.conv = hst.conv;
                if (!same) {
                    chat.length = 0;
                    hst.turns.forEach(t => chat.push({ q: t.question || "", a: t }));
                    redraw();
                    scroll();
                }
                drawHist();
            })
            .catch(() => undefined);
    newBtn.onclick = () => {
        histPanel.classList.remove("on");
        state.conv = "";
        state.fresh = true;
        chat.length = 0;
        redraw();
        drawHist();
        input.focus();
    };

    const call = (q: string): Promise<Reply> => {
        const history = chat.slice(-3).map(t => ({ q: t.q, title: t.a.title, text: t.a.text, tools: t.a.calls.map(c => `${c.tool}(${argText(c.args)})`) }));
        return fetch(`${API}/api/ask`, { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: q, history, page: view(), conv: state.conv, source: "pbi" }) })
            .then(r => r.json() as Promise<Reply>)
            .then(a => {
                if (a.conv) { state.conv = a.conv; state.fresh = false; }
                return a;
            })
            .catch(() => ({
                trace_id: "-", route: "error", title: isArabic(q) ? "المساعد مش شغال" : "The assistant gateway is offline",
                text: isArabic(q) ? "شغّل egypt/backend/app.py على الجهاز ده وجرّب تاني." : "Start egypt/backend/app.py on this machine and ask again.",
                chips: [], calls: [], tokens: { prompt: 0, output: 0, total: 0 }, naive_tokens: 32190, latency_ms: 0
            } as Reply));
    };

    const ask = (q: string) => {
        q = q.trim();
        if (!q) return;
        input.value = "";
        histPanel.classList.remove("on");
        const p = call(q);
        p.then(a => { chat.push({ q, a }); info(); load(state.conv); });
        addTurn(q, p, true);
    };
    if (!ctx.interactive) {   // dashboard tiles and other read-only hosts: show the thread, no typing
        input.disabled = true;
        input.placeholder = ctx.t("Static_Note", "Open the report to ask a question");
    }
    input.onkeydown = (e) => { if (e.key === "Enter") ask(input.value); };
    sendBtn.onclick = () => ask(input.value);
    redraw();
    scroll();
    load(state.conv);
}
