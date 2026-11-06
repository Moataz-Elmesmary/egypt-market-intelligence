"use strict";

import { formattingSettings } from "powerbi-visuals-utils-formattingmodel";

const MODES = [
    { value: "page", displayName: "Full page" },
    { value: "header", displayName: "Header" },
    { value: "kpis", displayName: "KPI tiles" },
    { value: "carousel", displayName: "Product carousel" },
    { value: "trend", displayName: "Trend" },
    { value: "map", displayName: "Governorate map" },
    { value: "forecast", displayName: "Forecast" },
    { value: "insights", displayName: "Insight cards" },
    { value: "notes", displayName: "Numbered notes" },
    { value: "ai", displayName: "Ask AI" }
];

class ViewCard extends formattingSettings.SimpleCard {
    mode = new formattingSettings.ItemDropdown({ name: "mode", displayName: "Visual", items: MODES, value: MODES[1] });
    page = new formattingSettings.TextInput({ name: "page", displayName: "Page / filter key", value: "", placeholder: "overview" });
    title = new formattingSettings.TextInput({ name: "title", displayName: "Title", value: "", placeholder: "" });
    subtitle = new formattingSettings.TextInput({ name: "subtitle", displayName: "Subtitle", value: "", placeholder: "" });

    name = "settings";
    displayName = "Egypt Market";
    slices: formattingSettings.Slice[] = [this.mode, this.page, this.title, this.subtitle];
}

export class VisualFormattingSettingsModel extends formattingSettings.Model {
    view = new ViewCard();
    cards = [this.view];
}
