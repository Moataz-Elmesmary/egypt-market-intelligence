"use strict";

import powerbi from "powerbi-visuals-api";
import { FormattingSettingsService } from "powerbi-visuals-utils-formattingmodel";
import "./../style/visual.less";

import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;
import IVisual = powerbi.extensibility.visual.IVisual;

import { VisualFormattingSettingsModel } from "./settings";
import { Ctx, Rows, applyPalette, clear, h, logoMark } from "./core";
import { renderHeader, renderInsights, renderKpis, renderNotes } from "./simple";
import { renderCarousel } from "./carousel";
import { renderTrend } from "./trend";
import { renderMap } from "./map";
import { renderForecast } from "./forecast";
import { renderAI } from "./ai";
import { renderPage } from "./page";

// One visual, several modes; each report page places instances with a mode set in the format pane.
export class Visual implements IVisual {
    private root: HTMLElement;
    private host: powerbi.extensibility.visual.IVisualHost;
    private selection: powerbi.extensibility.ISelectionManager;
    private fmt: VisualFormattingSettingsModel;
    private fmtService = new FormattingSettingsService();
    private lastKey = "";
    private lastSize = "";
    private loc: powerbi.extensibility.ILocalizationManager;

    constructor(options: VisualConstructorOptions) {
        this.host = options.host;
        this.selection = this.host.createSelectionManager();
        this.loc = this.host.createLocalizationManager();
        this.root = document.createElement("div");
        this.root.className = "ep-root";
        options.element.appendChild(this.root);
        options.element.addEventListener("contextmenu", (e: MouseEvent) => {
            this.selection.showContextMenu({}, { x: e.clientX, y: e.clientY });
            e.preventDefault();
        });
    }

    public update(options: VisualUpdateOptions) {
        const events = this.host.eventService;
        events.renderingStarted(options);
        try {
            const dv = options.dataViews && options.dataViews[0];
            this.fmt = this.fmtService.populateFormattingSettingsModel(VisualFormattingSettingsModel, dv);
            const v = this.fmt.view;
            const mode = String(v.mode.value?.value || "kpis");
            const rows = new Rows(dv);
            const hc = applyPalette(this.host.colorPalette);
            const interactive = this.host.hostCapabilities.allowInteractions !== false;
            const key = mode + "|" + hc + "|" + interactive + "|" + v.page.value + "|" + rows.rows.length + "|" + JSON.stringify(rows.rows.slice(0, 3)) + JSON.stringify(rows.rows.slice(-2));
            const size = `${Math.round(options.viewport.width)}x${Math.round(options.viewport.height)}`;
            // re-render only when data, mode or size change; animate when the data changes
            if (key === this.lastKey && size === this.lastSize && options.type !== powerbi.VisualUpdateType.Data) { events.renderingFinished(options); return; }
            const first = key !== this.lastKey;
            this.lastKey = key;
            this.lastSize = size;
            this.root.dataset.mode = mode;
            this.root.classList.toggle("is-hc", hc);
            this.root.classList.toggle("is-static", !interactive);
            if (hc) {
                const p = this.host.colorPalette;
                this.root.style.setProperty("--hc-fg", p.foreground.value);
                this.root.style.setProperty("--hc-bg", p.background.value);
                this.root.style.setProperty("--hc-sel", p.foregroundSelected.value);
            }
            const t = (k: string, fallback: string) => { const s = this.loc.getDisplayName(k); return s && s !== k ? s : fallback; };
            const ctx: Ctx = {
                el: this.root, host: this.host, selection: this.selection,
                width: options.viewport.width, height: options.viewport.height,
                page: v.page.value, title: v.title.value, subtitle: v.subtitle.value, first, interactive, t
            };
            if (!rows.names.length && mode !== "ai" && mode !== "header") {   // landing page until fields are bound
                renderLanding(ctx, mode);
                events.renderingFinished(options);
                return;
            }
            switch (mode) {
                case "page": renderPage(ctx, rows); break;
                case "header": renderHeader(ctx); break;
                case "carousel": renderCarousel(ctx, rows); break;
                case "trend": renderTrend(ctx, rows); break;
                case "map": renderMap(ctx, rows); break;
                case "forecast": renderForecast(ctx, rows); break;
                case "insights": renderInsights(ctx, rows); break;
                case "notes": renderNotes(ctx, rows); break;
                case "ai": renderAI(ctx, rows); break;
                default: renderKpis(ctx, rows);
            }
            events.renderingFinished(options);
        } catch (err) {
            this.root.textContent = "Egypt Pulse error: " + String(err);
            events.renderingFailed(options, String(err));
        }
    }

    public getFormattingModel(): powerbi.visuals.FormattingModel {
        return this.fmtService.buildFormattingModel(this.fmt);
    }
}

function renderLanding(ctx: Ctx, mode: string) {
    clear(ctx.el);
    const w = h("div", "ep-landing", undefined, ctx.el);
    w.appendChild(logoMark(Math.min(48, ctx.height / 4)));
    h("b", "", ctx.t("Landing_Title", "Egypt Market Intelligence"), w);
    h("span", "", ctx.t("Landing_Body", "Add the fields for this mode to start.") + " · " + mode, w);
}
