"use strict";

import { Ctx, DataLike, T, clear, countUp, h, icon, logoMark } from "./core";

// Report header: English title, Arabic subtitle, data stamp.
export function renderHeader(ctx: Ctx) {
    clear(ctx.el);
    const w = h("div", "ep-header", undefined, ctx.el);
    const mark = h("div", "ep-mark", undefined, w);
    mark.appendChild(logoMark(30));
    const txt = h("div", "ep-htxt", undefined, w);
    const t = h("div", "ep-htitle", undefined, txt);
    const parts = (ctx.title || "Egypt Consumer Pulse").split("|");
    h("span", "", parts[0], t);
    if (parts[1]) h("span", "ep-htitle-ar", parts[1], t);
    h("div", "ep-hsub", ctx.subtitle || "Public data · Oct 2026", txt);
}

// KPI tiles for one page key, ordered by Ord.
export function renderKpis(ctx: Ctx, d: DataLike) {
    clear(ctx.el);
    const rows = d.rows.filter(r => !ctx.page || d.s(r, "Page") === ctx.page).sort((a, b) => d.n(a, "Ord") - d.n(b, "Ord"));
    const wrap = h("div", "ep-kpis", undefined, ctx.el);
    if (!rows.length) { h("div", "ep-empty", "Add KPI fields", wrap); return; }
    rows.forEach((r, i) => {
        const tile = h("div", "ep-kpi", undefined, wrap);
        tile.style.animationDelay = `${i * 90}ms`;
        const ic = h("div", "ep-kpi-ic", undefined, tile);
        ic.appendChild(icon(d.s(r, "Icon") || "spark", 22, T.nile));
        const body = h("div", "ep-kpi-body", undefined, tile);
        h("div", "ep-kpi-label", d.s(r, "Label"), body);
        const row = h("div", "ep-kpi-row", undefined, body);
        const val = h("div", "ep-kpi-val", undefined, row);
        if (ctx.first) countUp(val, d.s(r, "Display"), 1200, i * 120); else val.textContent = d.s(r, "Display");
        const ar = h("div", "ep-kpi-ar", d.s(r, "LabelAR"), row);
        ar.dir = "rtl";
        const sub = h("div", "ep-kpi-sub", undefined, body);
        h("span", "", d.s(r, "Sub"), sub);
        if (d.s(r, "Source")) h("span", "ep-src", d.s(r, "Source").replace(/;/g, " · "), sub);
    });
}

// Insight cards: English and Egyptian Arabic, with source ids.
export function renderInsights(ctx: Ctx, d: DataLike) {
    clear(ctx.el);
    const rows = d.rows.filter(r => !ctx.page || d.s(r, "Page") === ctx.page).sort((a, b) => d.n(a, "Ord") - d.n(b, "Ord"));
    const wrap = h("div", "ep-ins", undefined, ctx.el);
    if (ctx.title) h("div", "ep-cardtitle", ctx.title, wrap);
    rows.forEach((r, i) => {
        const c = h("div", "ep-in", undefined, wrap);
        c.style.animationDelay = `${150 + i * 140}ms`;
        const head = h("div", "ep-in-head", undefined, c);
        const ic = h("span", "ep-in-ic", undefined, head);
        ic.appendChild(icon("spark", 16, T.gold, 1.8));
        h("span", "ep-in-title", d.s(r, "Title"), head);
        h("div", "ep-in-body", d.s(r, "Body"), c);
        const ar = h("div", "ep-in-ar", undefined, c);
        ar.dir = "rtl";
        h("b", "", d.s(r, "TitleAR") + " ", ar);
        h("span", "", d.s(r, "BodyAR"), ar);
        if (d.s(r, "Source")) h("div", "ep-src", "Source " + d.s(r, "Source").replace(/;/g, " · "), c);
    });
    window.clearInterval(rot.timer);
    if (wrap.scrollHeight > wrap.clientHeight + 2 && rows.length > 1) {
        // not enough room: show one card at a time and cycle
        wrap.classList.add("is-rot");
        const cards = Array.from(wrap.querySelectorAll<HTMLElement>(".ep-in"));
        const dots = h("div", "ep-dots", undefined, wrap);
        const dd = cards.map(() => h("i", "", undefined, dots));
        let k = 0;
        const show = () => { cards.forEach((c, i) => c.classList.toggle("on", i === k)); dd.forEach((x, i) => x.classList.toggle("on", i === k)); };
        show();
        rot.timer = window.setInterval(() => { k = (k + 1) % cards.length; show(); }, 6500);
    }
}

const rot = { timer: 0 };

// Numbered reading notes for the native pages: one row per note, tone sets the badge colour.
// Rows arrive already filtered by the model (Notes[Show Note] is blank for notes of another category or company).
const TONES: Record<string, string> = { lead: "Headline", fact: "Fact", watch: "Watch", method: "How to read" };

export function renderNotes(ctx: Ctx, d: DataLike) {
    clear(ctx.el);
    const rows = d.rows.filter(r => !ctx.page || d.s(r, "Page") === ctx.page).sort((a, b) => d.n(a, "Ord") - d.n(b, "Ord"));
    const wide = ctx.width >= 560;
    const wrap = h("div", "ep-notes" + (wide ? " is-grid" : ""), undefined, ctx.el);
    const list = h("ol", "ep-notes-list", undefined, wrap);
    if (!rows.length) h("div", "ep-notes-empty", ctx.t("Notes_Empty", "Pick a filter to read the notes for it."), list);
    rows.forEach((r, i) => {
        const tone = (d.s(r, "Tone") || "fact").toLowerCase();
        const li = h("li", "ep-note is-" + tone, undefined, list);
        li.style.animationDelay = `${80 + i * 90}ms`;
        h("span", "ep-note-n", String(i + 1).padStart(2, "0"), li);
        const body = h("div", "ep-note-main", undefined, li);
        const head = h("div", "ep-note-head", undefined, body);
        h("b", "ep-note-t", d.s(r, "Title"), head);
        if (wide) h("span", "ep-note-tag", TONES[tone] || tone, head);
        h("div", "ep-note-b", d.s(r, "Body"), body);
        const src = d.s(r, "Source") ? "Source " + d.s(r, "Source").replace(/;/g, " · ") : "";
        if (src && wide) h("div", "ep-note-src", src, body);
        else if (src && ctx.interactive) {
            const tip = (e: MouseEvent) => ({ coordinates: [e.clientX, e.clientY], isTouchEvent: false, identities: [],
                dataItems: [{ displayName: d.s(r, "Title"), value: "" }, { displayName: "Source", value: d.s(r, "Source").replace(/;/g, " · ") }] });
            li.addEventListener("mouseenter", e => ctx.host.tooltipService.show(tip(e)));
            li.addEventListener("mousemove", e => ctx.host.tooltipService.move(tip(e)));
            li.addEventListener("mouseleave", () => ctx.host.tooltipService.hide({ immediately: true, isTouchEvent: false }));
        }
    });
    const key = h("div", "ep-notes-key", undefined, wrap);
    Object.keys(TONES).forEach(t => { const k = h("span", "is-" + t, undefined, key); h("i", "", undefined, k); k.appendChild(document.createTextNode(TONES[t])); });
}
