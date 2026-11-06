"use strict";

import { Ctx, DataLike, T, clear, countUp, esc, h, setMarkup, uid } from "./core";
import { LOGOS } from "./logos";

interface Item { brand: string; ar: string; company: string; origin: string; shape: string; share: number; i21: number; i12: number; }

// Pack art per brand: body, label ink, wave stripe, label lines, and which logo variant sits on the pack.
export const STYLE: Record<string, { body: string; ink: string; wave: string; l1: string; l2: string; logo?: "color" | "white" }> = {
    "Pepsi": { body: "#10398F", ink: "#FFFFFF", wave: "#E3263B", l1: "PEPSI", l2: "COLA", logo: "color" },
    "Coca-Cola": { body: "#C8102E", ink: "#FFFFFF", wave: "#FFFFFF", l1: "COCA-COLA", l2: "ORIGINAL", logo: "white" },
    "Spiro Spathis": { body: "#1E5E40", ink: "#F3E3BC", wave: "#D5A44A", l1: "SPIRO", l2: "SPATHIS · 1920" },
    "Big Cola": { body: "#1B1B1F", ink: "#FFFFFF", wave: "#E31B23", l1: "BIG", l2: "COLA", logo: "color" },
    "V7 Cola": { body: "#15171C", ink: "#E9E4D8", wave: "#C79A3B", l1: "V7", l2: "COLA" },
    "talabat": { body: "#FF5A00", ink: "#FFFFFF", wave: "#FFFFFF", l1: "talabat", l2: "DELIVERY", logo: "white" },
    "Breadfast": { body: "#AA0082", ink: "#FFFFFF", wave: "#FFC93C", l1: "breadfast", l2: "GROCERIES", logo: "white" },
    "instashop": { body: "#FFFFFF", ink: "#ED037C", wave: "#ED037C", l1: "instashop", l2: "GROCERIES", logo: "color" },
    "elmenus": { body: "#F02A00", ink: "#FFFFFF", wave: "#FFFFFF", l1: "elmenus", l2: "FOOD", logo: "white" },
    "Rabbit": { body: "#141414", ink: "#E3FF19", wave: "#E3FF19", l1: "Rabbit", l2: "20 MIN", logo: "color" },
};

function logoImg(name: string, x: number, y: number, w: number, hh: number): string {
    const s = STYLE[name], L = LOGOS[name];
    if (!s || !s.logo || !L) return "";
    return `<image href="${L[s.logo]}" x="${x}" y="${y}" width="${w}" height="${hh}" preserveAspectRatio="xMidYMid meet"/>`;
}

function canSVG(name: string): string {
    const s = STYLE[name] || { body: T.nile, ink: "#FFFFFF", wave: T.gold, l1: name.toUpperCase(), l2: "" };
    const i = uid("c");
    const logo = logoImg(name, 18, 44, 68, 50);
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 104 200">
<defs><linearGradient id="sh${i}" x1="0" x2="1"><stop offset="0" stop-color="#000" stop-opacity=".5"/><stop offset=".16" stop-color="#000" stop-opacity="0"/><stop offset=".3" stop-color="#fff" stop-opacity=".38"/><stop offset=".42" stop-color="#fff" stop-opacity="0"/><stop offset=".78" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".55"/></linearGradient>
<linearGradient id="mt${i}" x1="0" x2="1"><stop offset="0" stop-color="#7f8b98"/><stop offset=".35" stop-color="#eef3f7"/><stop offset=".55" stop-color="#a9b5c2"/><stop offset="1" stop-color="#6c7886"/></linearGradient></defs>
<ellipse cx="52" cy="192" rx="40" ry="6" fill="#000" opacity=".22"/>
<path d="M12 26 Q14 14 30 12 H74 Q90 14 92 26 Z" fill="url(#mt${i})"/>
<ellipse cx="52" cy="12.5" rx="22" ry="4" fill="#d9e1e8" stroke="#8a96a3" stroke-width="1"/>
<rect x="10" y="24" width="84" height="164" rx="10" fill="${s.body}"/>
<path d="M10 112 C34 92 70 136 94 104 V124 C70 156 34 112 10 132 Z" fill="${s.wave}" opacity=".92"/>
${logo || `<text x="52" y="74" text-anchor="middle" font-family="Segoe UI Black, Arial Black, sans-serif" font-weight="900" font-size="14" fill="${s.ink}" textLength="${s.l1.length > 6 ? 72 : Math.max(22, s.l1.length * 11)}" lengthAdjust="spacingAndGlyphs">${esc(s.l1)}</text>`}
<text x="52" y="${logo ? 104 : 90}" text-anchor="middle" font-family="Segoe UI, sans-serif" font-weight="700" font-size="7.5" letter-spacing="1.3" fill="${s.ink}" opacity=".85">${esc(s.l2)}</text>
<rect x="10" y="24" width="84" height="164" rx="10" fill="url(#sh${i})"/>
<path d="M10 180 Q52 192 94 180 V184 Q52 197 10 184 Z" fill="url(#mt${i})" opacity=".9"/></svg>`;
}

// Delivery apps get a paper delivery bag instead of a can.
function bagSVG(name: string): string {
    const s = STYLE[name] || { body: T.nile, ink: "#FFFFFF", wave: T.gold, l1: name, l2: "" };
    const i = uid("b");
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 104 200">
<defs><linearGradient id="bs${i}" x1="0" x2="1"><stop offset="0" stop-color="#000" stop-opacity=".35"/><stop offset=".2" stop-color="#000" stop-opacity="0"/><stop offset=".34" stop-color="#fff" stop-opacity=".22"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/><stop offset=".8" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".4"/></linearGradient></defs>
<ellipse cx="52" cy="192" rx="42" ry="6" fill="#000" opacity=".22"/>
<path d="M34 46 C34 18 70 18 70 46" fill="none" stroke="${s.body === "#FFFFFF" ? "#CFC6B6" : s.body}" stroke-width="5" stroke-linecap="round" opacity=".85"/>
<path d="M12 44 H92 L96 186 H8 Z" fill="${s.body}"/>
<path d="M12 44 H92 L90 58 H14 Z" fill="#000" opacity=".16"/>
<path d="M8 150 C34 132 70 172 96 142 V158 C70 188 34 150 8 168 Z" fill="${s.wave}" opacity=".9"/>
${name === "Breadfast" ? logoImg(name, 40, 62, 24, 40) + `<text x="52" y="120" text-anchor="middle" font-family="Segoe UI, sans-serif" font-weight="800" font-size="15" fill="${s.ink}">${esc(s.l1)}</text>`
        : logoImg(name, 14, 70, 76, 40) || `<text x="52" y="94" text-anchor="middle" font-family="Segoe UI, sans-serif" font-weight="800" font-size="15" fill="${s.ink}" textLength="${Math.min(78, s.l1.length * 9.5)}" lengthAdjust="spacingAndGlyphs">${esc(s.l1)}</text>`}
<text x="52" y="${name === "Breadfast" ? 134 : 122}" text-anchor="middle" font-family="Segoe UI, sans-serif" font-weight="700" font-size="7" letter-spacing="1.4" fill="${s.ink}" opacity=".85">${esc(s.l2)}</text>
<path d="M12 44 H92 L96 186 H8 Z" fill="url(#bs${i})"/></svg>`;
}

const st = { raf: 0, angle: 0, front: -1, next: 0, busy: false, hover: false };

function ease(t: number) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }

export function renderCarousel(ctx: Ctx, d: DataLike) {
    cancelAnimationFrame(st.raf);
    clear(ctx.el);
    const items: Item[] = d.rows.map(r => ({
        brand: d.s(r, "Brand"), ar: d.s(r, "BrandAR"), company: d.s(r, "Company"), origin: d.s(r, "Origin"), shape: d.s(r, "Shape"),
        share: d.n(r, "Share of Search"), i21: d.n(r, "Interest 2021"), i12: d.n(r, "Interest Last 12M")
    })).filter(x => x.brand).sort((a, b) => (b.share || 0) - (a.share || 0));
    const root = h("div", "ep-car", undefined, ctx.el);
    const head = h("div", "ep-car-head", undefined, root);
    h("div", "ep-cardtitle", ctx.title || "Share of search, last 12 months", head);
    h("div", "ep-car-note", ctx.subtitle || "Google Trends, Egypt · share within the category", head);
    if (!items.length) { h("div", "ep-empty", "Add brand fields", root); return; }

    const stage = h("div", "ep-car-stage", undefined, root);
    const floor = h("div", "ep-car-floor", undefined, stage);
    const canH = Math.max(120, Math.min(230, ctx.height - 150));
    stage.style.height = canH + 28 + "px";
    floor.style.top = canH * 0.86 + "px";
    const nodes = items.map((it, i) => {
        const n = h("div", "ep-can", undefined, stage);
        n.style.height = canH + "px";
        n.style.width = canH * 0.52 + "px";
        n.style.marginLeft = -canH * 0.26 + "px";
        setMarkup(n, it.shape === "app" ? bagSVG(it.brand) : canSVG(it.brand), true);
        n.title = `${it.brand}: ${(it.share * 100).toFixed(1)}%`;
        n.onclick = () => rotateTo(i);
        return n;
    });
    const dots = h("div", "ep-car-dots", undefined, root);
    const dd = items.map(() => h("i", "", undefined, dots));

    const cap = h("div", "ep-car-cap2", undefined, root);
    const big = h("div", "ep-car-share2", undefined, cap);
    const meta = h("div", "ep-car-meta", undefined, cap);

    const n = items.length;
    const Rx = Math.min(ctx.width * 0.36, 300);
    const layout = () => {
        let best = -2, bi = 0;
        nodes.forEach((el, i) => {
            const th = st.angle + (i * 2 * Math.PI) / n;
            const z = Math.cos(th), s = 0.5 + 0.5 * ((z + 1) / 2);
            el.style.transform = `translate3d(${Math.sin(th) * Rx}px, ${-(1 - z) * 12}px, 0) scale(${s})`;
            el.style.zIndex = String(Math.round(z * 100) + 100);
            el.style.opacity = String(0.25 + 0.75 * ((z + 1) / 2));
            if (z > best) { best = z; bi = i; }
        });
        if (bi !== st.front) { st.front = bi; caption(items[bi]); dd.forEach((x, k) => x.classList.toggle("on", k === bi)); }
    };
    const caption = (it: Item) => {
        countUp(big, (it.share * 100).toFixed(1) + "%", 550);
        clear(meta);
        const L = LOGOS[it.brand], S = STYLE[it.brand];
        if (L && S) {
            const plate = h("div", "ep-plate", undefined, meta);
            const onBody = S.logo === "white" || it.brand === "Rabbit";
            plate.style.background = onBody ? S.body : "#FFFFFF";
            const img = h("img", "", undefined, plate);
            img.src = L[S.logo === "white" ? "white" : "color"];
            img.alt = it.brand;
        }
        const nm = h("div", "ep-car-name2", undefined, meta);
        h("span", "ep-car-ar2", it.ar, nm);
        h("b", "", it.brand, nm);
        const line = h("div", "ep-car-co2", undefined, meta);
        if (it.origin === "Egyptian") h("span", "ep-badge is-eg", "Egyptian brand", line);
        h("span", "", it.company, line);
        const ratio = it.i21 > 0.05 ? it.i12 / it.i21 : NaN;
        const txt = !isFinite(ratio) ? (it.i12 > 0.05 ? "new since 2021" : "")
            : ratio >= 1.15 ? `${ratio.toFixed(1)}x the search interest of 2021` : ratio <= 0.87 ? `${((1 - ratio) * 100).toFixed(0)}% below its 2021 search interest` : "steady since 2021";
        if (txt) h("div", "ep-car-d2" + (ratio >= 1.15 ? " up" : ratio <= 0.87 ? " down" : ""), txt, meta);
    };
    const rotateTo = (i: number) => {
        const step = (2 * Math.PI) / n, cur = st.angle;
        let target = -i * step;
        target = cur + ((((target - cur) % (2 * Math.PI)) + 3 * Math.PI) % (2 * Math.PI)) - Math.PI;
        const t0 = performance.now();
        st.busy = true;
        const tick = (now: number) => {
            const k = Math.min(1, (now - t0) / 900);
            st.angle = cur + (target - cur) * ease(k);
            if (k < 1) requestAnimationFrame(tick); else { st.busy = false; st.next = performance.now() + 2600; }
        };
        requestAnimationFrame(tick);
    };
    stage.onmouseenter = () => { st.hover = true; };
    stage.onmouseleave = () => { st.hover = false; st.next = performance.now() + 1200; };
    st.angle = 0; st.front = -1; st.busy = false; st.next = performance.now() + 2600;
    const loop = (now: number) => {
        if (!st.hover && !st.busy && now > st.next) rotateTo((st.front + 1) % n);
        layout();
        st.raf = requestAnimationFrame(loop);
    };
    st.raf = requestAnimationFrame(loop);
}
