"use strict";

import powerbi from "powerbi-visuals-api";
import DataView = powerbi.DataView;

// Design tokens: warm sand canvas, Nile teal accent, gold highlight.
export const T = {
    ink: "#1C2928", ink2: "#4F5F5C", muted: "#87918E", line: "#E8E1D4", line2: "#F1ECE3",
    card: "#FFFFFF", sand: "#F5F0E7", sand2: "#EFE7D9",
    nile: "#0B6E69", nile2: "#12958B", nileTint: "#E3F1EF",
    gold: "#C2922F", goldTint: "#F7EEDA", clay: "#C2552D", clayTint: "#F8E6DE",
    up: "#1E8757", down: "#C0412C",
    font: "'Segoe UI', 'Segoe UI Web (West European)', -apple-system, sans-serif",
    fontAr: "'Segoe UI', 'Tahoma', 'Arial', sans-serif"
};
const DEFAULTS = { ...T };

// High contrast: every token maps to the three colors Windows gives (text, background, accent); otherwise the brand tokens.
export function applyPalette(pal: powerbi.extensibility.ISandboxExtendedColorPalette): boolean {
    Object.assign(T, DEFAULTS);
    if (!pal || !pal.isHighContrast) return false;
    const fg = pal.foreground.value, bg = pal.background.value, sel = pal.foregroundSelected.value;
    Object.assign(T, {
        ink: fg, ink2: fg, muted: fg, line: fg, line2: fg, card: bg, sand: bg, sand2: bg,
        nile: sel, nile2: sel, gold: fg, clay: fg, up: sel, down: fg, nileTint: bg, goldTint: bg, clayTint: bg
    });
    return true;
}

export interface Ctx {
    el: HTMLElement;
    host: powerbi.extensibility.visual.IVisualHost;
    selection: powerbi.extensibility.ISelectionManager;
    width: number;
    height: number;
    page: string;
    title: string;
    subtitle: string;
    first: boolean;
    interactive: boolean;                       // false where the host disallows interaction (e.g. a dashboard tile)
    t: (key: string, fallback: string) => string;   // localized string (stringResources/<locale>/resources.resjson)
}

// What every renderer reads: rows plus typed accessors by column name.
export interface DataLike {
    rows: any[];
    table?: powerbi.DataViewTable;
    has(name: string): boolean;
    s(r: any, name: string): string;
    n(r: any, name: string): number;
    d(r: any, name: string): Date | null;
}

// Plain objects (parsed from the Feed table) behind the same accessors.
export class ObjRows implements DataLike {
    table = undefined;
    constructor(public rows: Record<string, unknown>[]) { }
    has(name: string) { return this.rows.length > 0 && name in this.rows[0]; }
    s(r: Record<string, unknown>, name: string) { const v = r[name]; return v === null || v === undefined ? "" : String(v); }
    n(r: Record<string, unknown>, name: string) { const v = r[name]; return v === null || v === undefined || v === "" ? NaN : Number(v); }
    d(r: Record<string, unknown>, name: string) { const v = r[name]; return v ? (v instanceof Date ? v : new Date(String(v))) : null; }
}

// Table dataView wrapper: columns addressed by their model property name.
export class Rows implements DataLike {
    names: string[] = [];
    rows: powerbi.DataViewTableRow[] = [];
    table: powerbi.DataViewTable | undefined;
    private idx = new Map<string, number>();

    constructor(dv: DataView | undefined) {
        const t = dv?.table;
        if (!t) return;
        this.table = t;
        this.rows = t.rows || [];
        t.columns.forEach((c, i) => {
            const q = c.queryName || c.displayName || "";
            const m = q.match(/([^.(]+)\)?$/);
            const key = (m ? m[1] : q).trim();
            this.names.push(key);
            this.idx.set(key, i);
            this.idx.set(c.displayName, i);
        });
    }
    has(name: string) { return this.idx.has(name); }
    col(name: string) { return this.idx.get(name); }
    s(r: powerbi.DataViewTableRow, name: string): string {
        const i = this.idx.get(name);
        const v = i === undefined ? null : r[i];
        return v === null || v === undefined ? "" : String(v);
    }
    n(r: powerbi.DataViewTableRow, name: string): number {
        const i = this.idx.get(name);
        const v = i === undefined ? null : r[i];
        if (v === null || v === undefined || v === "") return NaN;
        return typeof v === "number" ? v : Number(v);
    }
    d(r: powerbi.DataViewTableRow, name: string): Date | null {
        const i = this.idx.get(name);
        const v = i === undefined ? null : r[i];
        if (v === null || v === undefined) return null;
        return v instanceof Date ? v : new Date(v as string);
    }
}

export function clear(el: HTMLElement) {
    while (el.firstChild) el.removeChild(el.firstChild);
}

export function h<K extends keyof HTMLElementTagNameMap>(tag: K, cls?: string, text?: string, parent?: HTMLElement): HTMLElementTagNameMap[K] {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
}

export const SVGNS = "http://www.w3.org/2000/svg";

export function hexA(hex: string, a: number) {
    const v = hex.replace("#", "");
    const r = parseInt(v.slice(0, 2), 16), g = parseInt(v.slice(2, 4), 16), b = parseInt(v.slice(4, 6), 16);
    return `rgba(${r},${g},${b},${a})`;
}

export function mix(hex: string, to: string, t: number) {
    const p = (x: string) => [1, 3, 5].map(i => parseInt(x.slice(i, i + 2), 16));
    const a = p(hex), b = p(to);
    const c = a.map((v, i) => Math.round(v + (b[i] - v) * t));
    return "#" + c.map(v => v.toString(16).padStart(2, "0")).join("");
}

export function isArabic(s: string) { return /[؀-ۿ]/.test(s); }

export function fmtPct(v: number, d = 0) { return `${(v * 100).toFixed(d)}%`; }

export function fmtNum(v: number) {
    const a = Math.abs(v);
    if (a >= 1e9) return (v / 1e9).toFixed(1) + "B";
    if (a >= 1e6) return (v / 1e6).toFixed(1) + "M";
    if (a >= 1e4) return (v / 1e3).toFixed(0) + "K";
    if (a >= 1e3) return (v / 1e3).toFixed(1) + "K";
    return v.toFixed(a < 10 && v % 1 ? 1 : 0);
}

// Animate the numeric part of a display string ("EGP 30.0B", "+35%", "10x+").
export function countUp(el: HTMLElement, display: string, ms = 1100, delay = 0) {
    const m = display.match(/-?[\d,]*\.?\d+/);
    if (!m) { el.textContent = display; return; }
    const raw = m[0];
    const target = parseFloat(raw.replace(/,/g, ""));
    const dec = (raw.split(".")[1] || "").length;
    const pre = display.slice(0, m.index), post = display.slice((m.index || 0) + raw.length);
    const start = performance.now() + delay;
    el.textContent = pre + (0).toFixed(dec) + post;
    const step = (now: number) => {
        const k = Math.min(1, Math.max(0, (now - start) / ms));
        const e = 1 - Math.pow(1 - k, 3);
        const v = target * e;
        el.textContent = pre + (raw.includes(",") ? Math.round(v).toLocaleString("en-US") : v.toFixed(dec)) + post;
        if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}

// Minimal line icons, 24px grid.
const ICONS: Record<string, string> = {
    people: "M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zm7-1a3 3 0 1 0 0-6M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5M16.5 14.5c2.6.3 4.4 2 4.9 5.5",
    glass: "M6 3h12l-1.6 17.2a1 1 0 0 1-1 .8H8.6a1 1 0 0 1-1-.8zM6.6 9h10.8M10 13.5h.01M13 16h.01",
    target: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zm0-4a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0-4a1 1 0 1 0 0-2 1 1 0 0 0 0 2z",
    bike: "M5.5 18.5a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm13 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM5.5 15.5 9 9h6l3.5 6.5M9 9 8 6H6m9 3 1.5-3H19M12 15.5 9 9",
    pulse: "M3 12h4l2.5-6 4 12L16 9l1.5 3H21",
    store: "M4 10v10h16V10M3 10l1.6-6h14.8L21 10M3 10a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0M10 20v-5h4v5",
    tag: "M3.5 12.5 12 4h7.5a.5.5 0 0 1 .5.5V12l-8.5 8.5a1 1 0 0 1-1.4 0l-6.6-6.6a1 1 0 0 1 0-1.4zM16 8.5h.01",
    cup: "M5 8h11v6a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5zm11 1h1.5a2.5 2.5 0 0 1 0 5H16M8 2.5v2.5M11 2.5v2.5M14 2.5v2.5",
    phone: "M8 2.5h8a1.5 1.5 0 0 1 1.5 1.5v16a1.5 1.5 0 0 1-1.5 1.5H8A1.5 1.5 0 0 1 6.5 20V4A1.5 1.5 0 0 1 8 2.5zM11 18.5h2M9.5 8l2 2 3.5-3.5",
    bag: "M5 8h14l-1 12H6zM9 8V6a3 3 0 0 1 6 0v2",
    pin: "M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21zm0-9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z",
    rocket: "M14 4c3-1 6-1 6-1s0 3-1 6l-6 6-5-5zM9 10l-4 .5L3 13l4 1M14 15l-.5 4L11 21l-1-4M15.5 8.5h.01",
    coins: "M9 11c3.3 0 6-1.1 6-2.5S12.3 6 9 6 3 7.1 3 8.5 5.7 11 9 11zM3 8.5v4C3 13.9 5.7 15 9 15s6-1.1 6-2.5M15 11c3.3 0 6 1 6 2.5s-2.7 2.5-6 2.5M21 13.5v4c0 1.4-2.7 2.5-6 2.5s-6-1.1-6-2.5V15",
    box: "M3.5 7.5 12 3l8.5 4.5v9L12 21l-8.5-4.5zM3.5 7.5 12 12l8.5-4.5M12 12v9",
    up: "M3 17l6-6 4 4 8-8M15 7h6v6",
    bolt: "M13 2.5 4.5 13.5H11l-1 8 8.5-11H12z",
    shield: "M12 3l7.5 3v5.5c0 4.4-3.2 8.3-7.5 9.5-4.3-1.2-7.5-5.1-7.5-9.5V6zM9 12l2 2 4-4",
    dollar: "M12 2.5v19M16.5 6.5C15.8 5 14.2 4.5 12 4.5c-2.6 0-4.5 1.2-4.5 3.3 0 4.7 9 2.6 9 7.4 0 2.1-1.9 3.3-4.5 3.3-2.3 0-4-.6-4.8-2.3",
    spark: "M12 3l1.9 5.6L19.5 10l-5.6 1.9L12 17.5l-1.9-5.6L4.5 10l5.6-1.4zM19 15l.8 2.2 2.2.8-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"
};

export function icon(name: string, size = 22, color = T.nile, stroke = 1.7): SVGSVGElement {
    const s = document.createElementNS(SVGNS, "svg");
    s.setAttribute("viewBox", "0 0 24 24");
    s.setAttribute("width", String(size));
    s.setAttribute("height", String(size));
    const p = document.createElementNS(SVGNS, "path");
    p.setAttribute("d", ICONS[name] || ICONS.spark);
    p.setAttribute("fill", "none");
    p.setAttribute("stroke", color);
    p.setAttribute("stroke-width", String(stroke));
    p.setAttribute("stroke-linecap", "round");
    p.setAttribute("stroke-linejoin", "round");
    s.appendChild(p);
    return s;
}

// Shared floating tooltip inside the visual's own element.
export class Tip {
    private node: HTMLDivElement;
    constructor(private root: HTMLElement) {
        this.node = h("div", "ep-tip", undefined, root);
    }
    show(html: string, ev: MouseEvent) {
        const rb = this.root.getBoundingClientRect();
        const x = ev.clientX - rb.left, y = ev.clientY - rb.top;
        setMarkup(this.node, html);
        this.node.style.opacity = "1";
        const w = this.node.offsetWidth, hh = this.node.offsetHeight;
        const rw = this.root.clientWidth, rh = this.root.clientHeight;
        let left = x + 14, top = y + 14;
        if (left + w > rw - 4) left = x - w - 14;
        if (top + hh > rh - 4) top = y - hh - 14;
        this.node.style.left = Math.max(4, left) + "px";
        this.node.style.top = Math.max(4, top) + "px";
    }
    hide() { this.node.style.opacity = "0"; }
}

let seq = 0;
export function uid(prefix: string) { seq += 1; return prefix + seq; }

// Parse trusted, escaped markup into nodes (avoids innerHTML assignment).
export function setMarkup(el: Element, markup: string, svg = false) {
    while (el.firstChild) el.removeChild(el.firstChild);
    const doc = new DOMParser().parseFromString(svg ? markup : `<body>${markup}</body>`, svg ? "image/svg+xml" : "text/html");
    const src = svg ? [doc.documentElement] : Array.from(doc.body.childNodes);
    src.forEach(n => el.appendChild(document.importNode(n, true)));
}

export function esc(s: string) {
    return s.replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string));
}

// The brand mark: a gold pyramid in stripes (also the A of MARKET in the page backgrounds).
export function logoMark(size = 28): SVGSVGElement {
    const holder = document.createElement("div");
    setMarkup(holder, `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 36" width="${size}" height="${Math.round(size * 0.9)}">`
        + `<defs><linearGradient id="egpg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F6CF7A"/><stop offset="1" stop-color="#D08A1E"/></linearGradient></defs>`
        + `<path d="M20 1 L39 35 H1 Z" fill="url(#egpg)"/><path d="M20 1 L39 35 H24 Z" fill="#000" opacity=".16"/>`
        + `<path d="M9.5 21 H30.5" stroke="#0B6E69" stroke-width="2.2"/><path d="M5 29 H35" stroke="#0B6E69" stroke-width="2.2"/></svg>`, true);
    return holder.firstChild as SVGSVGElement;
}
