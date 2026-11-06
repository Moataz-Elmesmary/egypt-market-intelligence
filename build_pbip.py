"""Generate the Power BI project (PBIP): TMDL semantic model over the Excel file + PBIR report.

Run after build_egypt_data.py and after packaging the custom visual:
    python build_pbip.py <path-to-.pbiviz> [output folder] [--data-url URL]

Without --data-url the workbook is copied next to the project and Power Query reads it from disk.
With --data-url (the committed pbip/ folder uses the workbook's raw GitHub URL) the model reads it
over HTTPS, so a fresh clone opens and refreshes with no path to edit.
Keep the output folder short on Windows (MAX_PATH). Open "Egypt Market Intelligence.pbip" and refresh once.
"""
import json
import shutil
import sys
import uuid
import zipfile
from pathlib import Path

HERE = Path(__file__).absolute().parent  # absolute, not resolve: keeps a short junction path short
NAME = "Egypt Market Intelligence"
SRC_XLSX = HERE / "data" / "Egypt_Market_Intelligence_2026.xlsx"
_ARGS = [a for a in sys.argv[1:]]
DATA_URL = _ARGS.pop(_ARGS.index("--data-url") + 1) if "--data-url" in _ARGS else ""
_ARGS = [a for a in _ARGS if a != "--data-url"]
OUT = Path(_ARGS[1]).absolute() if len(_ARGS) > 1 else HERE / "pbip"
SM = OUT / f"{NAME}.SemanticModel"
RP = OUT / f"{NAME}.Report"
XLSX = OUT / "Egypt_Market_Intelligence_2026.xlsx"
GUID = "egyptPulse8AAD5EB20DBA4B41B73872D4B222801B"
BASE_THEME = HERE / "pbip_assets" / "CY24SU10.json"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"

# ------------------------------------------------------------------ semantic model
TABLES = {
    "Brand": [("Brand", "string"), ("BrandAR", "string"), ("Category", "string"), ("Company", "string"), ("Origin", "string"),
              ("Color", "string"), ("Shape", "string"), ("Sort", "int64"), ("CategoryAR", "string"),
              ("ShareOfSearch12M", "double"), ("Interest2021", "double"), ("InterestLast12M", "double"), ("CategorySort", "int64"), ("Tone", "string")],
    "Governorate": [("GovCode", "string"), ("Governorate", "string"), ("GovernorateAR", "string"), ("Region", "string"),
                    ("Population", "int64"), ("UrbanPct", "double"), ("RegionAR", "string"), ("UrbanPop", "double"), ("Lat", "double"), ("Lon", "double")],
    "Months": [("Month", "dateTime"), ("Year", "int64"), ("MonthLabel", "string"), ("EventCola", "string"), ("EventColaAR", "string"), ("EventApps", "string"), ("EventAppsAR", "string")],
    "SearchTrend": [("Month", "dateTime"), ("Brand", "string"), ("Category", "string"), ("Interest", "int64"), ("Last12M", "boolean")],
    "SearchGeo": [("GovCode", "string"), ("Brand", "string"), ("Category", "string"), ("Share", "double")],
    "Revenue_Q": [("Company", "string"), ("Quarter", "string"), ("QuarterEnd", "dateTime"), ("Year", "int64"), ("RevenueEGP", "double"), ("BacktestEGP", "double"),
                  ("ForecastEGP", "double"), ("Lo80", "double"), ("Hi80", "double"), ("FX", "double"), ("ActualUSD", "double"), ("ForecastUSD", "double"),
                  ("Seasonal naive", "double"), ("Seasonal naive + drift", "double"), ("Holt-Winters (ETS)", "double"), ("Theta", "double"),
                  ("SARIMA", "double"), ("Trend + season OLS", "double"),
                  ("CPI", "double"), ("RealEGP", "double"), ("ForecastLow", "double"), ("ForecastHigh", "double")],
    "TrendMetric": [("Metric", "string"), ("Ord", "int64")],
    "Company": [("Company", "string"), ("CompanyAR", "string"), ("Ticker", "string"), ("Segment", "string"), ("SegmentAR", "string"),
                ("Revenue2025", "double"), ("Forecast2026", "double"), ("Forecast2027", "double"), ("Growth2026", "double"), ("Growth2027", "double"),
                ("Revenue2025USD", "double"), ("Forecast2027USD", "double"), ("EnsembleMAPE", "double"), ("BestModel", "string"), ("BestModelMAPE", "double"),
                ("Blend", "string"), ("Reliability", "string"), ("ReliabilityAR", "string"), ("InsightEN", "string"), ("InsightAR", "string"), ("Sort", "int64"),
                ("RealGrowth2027", "double"), ("InflationPart", "double"), ("Forecast2027Low", "double"), ("Forecast2027High", "double"),
                ("MASE", "double"), ("CoverageIn", "int64"), ("CoverageN", "int64"), ("Coverage", "string"),
                ("ErrH1", "double"), ("ErrH2", "double"), ("ErrH3", "double"), ("ErrH4", "double"),
                ("BacktestMAPE", "double"), ("RealMethodMAPE", "double"), ("MethodNote", "string")],
    "Backtest": [("Company", "string"), ("Origin", "string"), ("Horizon", "int64"), ("Quarter", "string"), ("Actual", "double"),
                 ("Forecast", "double"), ("Lo80", "double"), ("Hi80", "double"), ("Inside", "int64"), ("APE", "double")],
    "Scenario": [("Scenario", "string"), ("Ord", "int64"), ("Inflation", "double"), ("FX2027", "double"), ("Note", "string")],
    "Revenue_FY": [("Company", "string"), ("Year", "int64"), ("RevenueEGP", "double"), ("FX", "double"), ("Basis", "string"), ("RevenueUSD", "double")],
    "Models": [("Company", "string"), ("Model", "string"), ("MAPE_Select", "double"), ("MAPE_Holdout", "double"), ("Weight", "double")],
    "KPI": [("Page", "string"), ("Ord", "int64"), ("Key", "string"), ("Label", "string"), ("LabelAR", "string"), ("Value", "double"),
            ("Display", "string"), ("Sub", "string"), ("SubAR", "string"), ("Icon", "string"), ("Source", "string")],
    "Insight": [("Page", "string"), ("Ord", "int64"), ("Title", "string"), ("TitleAR", "string"), ("Body", "string"), ("BodyAR", "string"), ("Source", "string")],
    "Notes": [("Page", "string"), ("Category", "string"), ("Company", "string"), ("Ord", "int64"), ("Tone", "string"), ("Title", "string"),
              ("TitleAR", "string"), ("Body", "string"), ("Source", "string")],
    "Knowledge": [("Id", "int64"), ("Dataset", "string"), ("Entity", "string"), ("EntityAR", "string"), ("Attr", "string"), ("Period", "string"),
                  ("Value", "double"), ("Unit", "string"), ("Source", "string")],
    "Sources": [("Id", "string"), ("Title", "string"), ("URL", "string")],
    "Feed": [("Dataset", "string"), ("Seq", "int64"), ("Json", "string")],
}
M_TYPE = {"string": "type text", "int64": "Int64.Type", "double": "type number", "dateTime": "type date", "boolean": "type logical"}
SORT_BY = {("Brand", "Brand"): "Sort", ("Brand", "Category"): "CategorySort", ("Company", "Company"): "Sort", ("Scenario", "Scenario"): "Ord", ("TrendMetric", "Metric"): "Ord"}
FORMAT = {("Governorate", "Population"): "#,0", ("Governorate", "UrbanPop"): "#,0", ("SearchGeo", "Share"): "0%",
          ("Months", "Month"): "mmm yyyy", ("SearchTrend", "Month"): "mmm yyyy", ("Revenue_Q", "QuarterEnd"): "yyyy-mm-dd",
          ("Models", "MAPE_Holdout"): "0.00", ("Models", "MAPE_Select"): "0.00", ("Models", "Weight"): "0%"}

MEASURES = {
    "SearchTrend": [
        ("Search Interest", "SUM ( SearchTrend[Interest] )", "0"),
        ("Share of Search", """VAR cat = SELECTEDVALUE ( Brand[Category] )
VAR b = CALCULATE ( SUM ( SearchTrend[Interest] ), SearchTrend[Last12M] = TRUE () )
VAR c = CALCULATE ( SUM ( SearchTrend[Interest] ), SearchTrend[Last12M] = TRUE (), REMOVEFILTERS ( Brand ), Brand[Category] = cat )
RETURN DIVIDE ( b, c )""", "0.0%"),
        ("Interest 2021", "CALCULATE ( AVERAGE ( SearchTrend[Interest] ), YEAR ( SearchTrend[Month] ) = 2021 )", "0.0"),
        ("Interest Last 12M", "CALCULATE ( AVERAGE ( SearchTrend[Interest] ), SearchTrend[Last12M] = TRUE () )", "0.0"),
        ("Event", """VAR c = SELECTEDVALUE ( Brand[Category] )
RETURN SWITCH ( c, "Soft drinks", SELECTEDVALUE ( Months[EventCola] ), "Delivery apps", SELECTEDVALUE ( Months[EventApps] ) )""", None),
        ("Brand Color", "SELECTEDVALUE ( Brand[Tone], \"#0B6E69\" )", None),
        ("Breadfast Interest", "CALCULATE ( [Search Interest], Brand[Brand] = \"Breadfast\" )", "0"),
        ("Trend Value", """VAR m = SELECTEDVALUE ( 'TrendMetric'[Ord], 1 )
VAR base2021 = CALCULATE ( AVERAGE ( SearchTrend[Interest] ), REMOVEFILTERS ( Months ), YEAR ( SearchTrend[Month] ) = 2021 )
RETURN SWITCH ( m,
    1, [Search Interest],
    2, DIVIDE ( [Search Interest], base2021 ) * 100,
    3, DIVIDE ( [Search Interest], CALCULATE ( [Search Interest], ALLEXCEPT ( Brand, Brand[Category] ) ) ) * 100 )""", "0"),
    ],
    "SearchGeo": [
        ("Geo Share", "AVERAGE ( SearchGeo[Share] )", "0%"),
        ("Leader Share", "MAXX ( VALUES ( Brand[Brand] ), [Geo Share] )", "0%"),
        ("Leader", """VAR t = FILTER ( ADDCOLUMNS ( VALUES ( Brand[Brand] ), "@s", [Geo Share] ), NOT ISBLANK ( [@s] ) )
RETURN MAXX ( TOPN ( 1, t, [@s], DESC ), Brand[Brand] )""", None),
        ("Leader Color", "LOOKUPVALUE ( Brand[Tone], Brand[Brand], [Leader] )", None),
        ("Runner Share", """VAR t = ADDCOLUMNS ( VALUES ( Brand[Brand] ), "@s", [Geo Share] )
VAR best = MAXX ( t, [@s] )
RETURN MAXX ( FILTER ( t, [@s] < best ), [@s] )""", "0%"),
        ("Runner Up", """VAR t = ADDCOLUMNS ( VALUES ( Brand[Brand] ), "@s", [Geo Share] )
VAR r = [Runner Share]
RETURN MAXX ( FILTER ( t, [@s] = r ), Brand[Brand] )""", None),
        ("Focus Brand", "IF ( HASONEVALUE ( Brand[Brand] ), VALUES ( Brand[Brand] ) )", None),
        ("Focus Share", "IF ( HASONEVALUE ( Brand[Brand] ), [Geo Share] )", "0%"),
        ("Focus Color", "IF ( HASONEVALUE ( Brand[Brand] ), VALUES ( Brand[Tone] ) )", None),
        ("Lead Margin", "[Leader Share] - [Runner Share]", "+0%;-0%"),
        ("talabat Share", "CALCULATE ( [Geo Share], Brand[Brand] = \"talabat\" )", "0%"),
        ("Breadfast Share", "CALCULATE ( [Geo Share], Brand[Brand] = \"Breadfast\" )", "0%"),
    ],
    "Governorate": [
        ("Urban Consumers (M)", "DIVIDE ( SUM ( Governorate[UrbanPop] ), 1000000 )", "0.0"),
        ("Population (M)", "DIVIDE ( SUM ( Governorate[Population] ), 1000000 )", "0.0"),
    ],
    "Brand": [
        ("Category Leader", """VAR t = ADDCOLUMNS ( VALUES ( Brand[Brand] ), "@s", [Share of Search] )
RETURN MAXX ( TOPN ( 1, t, [@s], DESC ), Brand[Brand] )""", None),
        ("Leader National Share", "MAXX ( VALUES ( Brand[Brand] ), [Share of Search] )", "0.0%"),
        ("Governorates Led", """VAR top1 = [Category Leader]
RETURN COUNTROWS ( FILTER ( VALUES ( Governorate[GovCode] ), [Leader] = top1 ) ) & " of 27\"""", None),
        ("Search Growth", "DIVIDE ( [Interest Last 12M], [Interest 2021] )", "0.0"),
        ("Category Leader Color", "LOOKUPVALUE ( Brand[Tone], Brand[Brand], [Category Leader] )", None),
        ("Category Runner", """VAR t = ADDCOLUMNS ( VALUES ( Brand[Brand] ), "@s", [Share of Search] )
RETURN MINX ( TOPN ( 1, TOPN ( 2, t, [@s], DESC ), [@s], ASC ), Brand[Brand] )""", None),
        ("Fastest Grower", """VAR t = FILTER ( ADDCOLUMNS ( VALUES ( Brand[Brand] ), "@g", [Search Growth] ), NOT ISBLANK ( [@g] ) )
RETURN MAXX ( TOPN ( 1, t, [@g], DESC ), Brand[Brand] ) & " · " & FORMAT ( MAXX ( t, [@g] ), "0.0" ) & "x\"""", None),
        ("Search Insight", """VAR s = [Leader National Share]
RETURN [Category Leader] & " holds " & FORMAT ( s, "0%" ) & " of Google searches in its category over the last 12 months and leads "
    & [Governorates Led] & " governorates; " & [Category Runner] & " is the runner-up. Search share measures attention, not sales.\"""", None),
    ],
    "KPI": [
        ("talabat Lead", "CALCULATE ( SELECTEDVALUE ( 'KPI'[Display] ), 'KPI'[Key] = \"talabat\" )", None),
        ("talabat GMV 2025", "CALCULATE ( SELECTEDVALUE ( 'KPI'[Display] ), 'KPI'[Key] = \"gmv\" )", None),
        ("Breadfast vs talabat", "CALCULATE ( SELECTEDVALUE ( 'KPI'[Display] ), 'KPI'[Key] = \"bfratio\" )", None),
        ("Breadfast Funding", "CALCULATE ( SELECTEDVALUE ( 'KPI'[Display] ), 'KPI'[Key] = \"bfraise\" )", None),
    ],
    "Company": [
        ("Company Name", "SELECTEDVALUE ( 'Company'[Company], \"All four companies\" )", None),
        ("Revenue 2025 (EGP B)", "DIVIDE ( SUM ( 'Company'[Revenue2025] ), 1000 )", "0.0"),
        ("Forecast 2027 (EGP B)", "DIVIDE ( SUM ( 'Company'[Forecast2027] ), 1000 )", "0.0"),
        ("Growth 2027", "DIVIDE ( SUM ( 'Company'[Forecast2027] ), SUM ( 'Company'[Forecast2026] ) ) - 1", "+0.0%;-0.0%"),
        ("Forecast Error", "DIVIDE ( AVERAGE ( 'Company'[EnsembleMAPE] ), 100 )", "0.0%"),
        ("Confidence", "SELECTEDVALUE ( 'Company'[Reliability], \"Pick a company\" )", None),
        ("Confidence Color", "SWITCH ( SELECTEDVALUE ( 'Company'[Reliability] ), \"High\", \"#0B6E69\", \"Medium\", \"#C2922F\", \"Low\", \"#8A6516\", \"#4F5F5C\" )", None),
        ("Best Model", "SELECTEDVALUE ( 'Company'[BestModel], \"Pick a company\" )", None),
        ("Model Blend", "SELECTEDVALUE ( 'Company'[Blend], \"Pick a company\" )", None),
        ("Real Growth 2027", "AVERAGE ( 'Company'[RealGrowth2027] )", "+0.0%;-0.0%"),
        ("MASE Score", "AVERAGE ( 'Company'[MASE] )", "0.00"),
        ("Band Coverage", "SELECTEDVALUE ( 'Company'[Coverage], \"Pick a company\" )", None),
        ("Method Note", "SELECTEDVALUE ( 'Company'[MethodNote], \"Pick a company to see how its forecast was tested.\" )", None),
        ("Accuracy Note", "\"How it is scored: each model is refit on the history up to a cut-off, forecasts the next 4 quarters, and is compared with what actually happened (rolling-origin backtest). The 3 lowest-error models are blended by inverse error. The 80% band is the 80th percentile of the ensemble's own past misses at each horizon, so it widens with the horizon.\"", None),
        ("Forecast Insight", "SELECTEDVALUE ( 'Company'[InsightEN], \"Pick a company above: its forecast, how the ensemble is built and how far off it was on quarters it never saw.\" )", None),
    ],
    "Revenue_Q": [
        ("Actual (EGP M)", "SUM ( Revenue_Q[RevenueEGP] )", "#,0"),
        ("Ensemble Forecast", "SUM ( Revenue_Q[ForecastEGP] )", "#,0"),
        ("Low 80%", "SUM ( Revenue_Q[Lo80] )", "#,0"),
        ("High 80%", "SUM ( Revenue_Q[Hi80] )", "#,0"),
        ("Backtest (EGP M)", "SUM ( Revenue_Q[BacktestEGP] )", "#,0"),
        ("Real (2021 prices)", "SUM ( Revenue_Q[RealEGP] )", "#,0"),
        ("Forecast Low", "SUM ( Revenue_Q[ForecastLow] )", "#,0"),
        ("Forecast High", "SUM ( Revenue_Q[ForecastHigh] )", "#,0"),
        ("Scenario Forecast", """SWITCH ( SELECTEDVALUE ( 'Scenario'[Ord], 2 ), 1, [Forecast Low], 3, [Forecast High], [Ensemble Forecast] )""", "#,0"),
        ("Scenario 2027 (EGP B)", "DIVIDE ( CALCULATE ( [Scenario Forecast], Revenue_Q[Year] = 2027 ), 1000 )", "0.0"),
        ("Actual (backtest quarters)", "IF ( NOT ISBLANK ( [Backtest (EGP M)] ), [Actual (EGP M)] )", "#,0"),
        ("Backtest Error", "DIVIDE ( [Backtest (EGP M)] - [Actual (backtest quarters)], [Actual (backtest quarters)] )", "+0.0%;-0.0%"),
        ("Seasonal naive path", "SUM ( Revenue_Q[Seasonal naive] )", "#,0"),
        ("Naive + drift path", "SUM ( Revenue_Q[Seasonal naive + drift] )", "#,0"),
        ("Holt-Winters path", "SUM ( Revenue_Q[Holt-Winters (ETS)] )", "#,0"),
        ("Theta path", "SUM ( Revenue_Q[Theta] )", "#,0"),
        ("SARIMA path", "SUM ( Revenue_Q[SARIMA] )", "#,0"),
        ("OLS path", "SUM ( Revenue_Q[Trend + season OLS] )", "#,0"),
    ],
    "Insight": [
        ("Delivery Insight", """CALCULATE ( SELECTEDVALUE ( 'Insight'[Title] ) & ". " & SELECTEDVALUE ( 'Insight'[Body] ), 'Insight'[Page] = "delivery", 'Insight'[Ord] = 1 )""", None),
    ],
    "Notes": [
        ("Show Note", """VAR cat = SELECTEDVALUE ( Brand[Category] )
VAR co = SELECTEDVALUE ( 'Company'[Company] )
VAR nc = SELECTEDVALUE ( 'Notes'[Category] )
VAR nco = SELECTEDVALUE ( 'Notes'[Company] )
RETURN IF ( ( nc = "" || nc = cat ) && ( nco = "" || nco = co ), 1 )""", "0"),
    ],
    "Backtest": [
        ("Horizon Error", "AVERAGE ( 'Backtest'[APE] )", "0.0%"),
        ("Backtest Actual", "SUM ( 'Backtest'[Actual] )", "#,0"),
        ("Backtest Forecast", "SUM ( 'Backtest'[Forecast] )", "#,0"),
        ("Band Low", "SUM ( 'Backtest'[Lo80] )", "#,0"),
        ("Band High", "SUM ( 'Backtest'[Hi80] )", "#,0"),
        ("In Band", "IF ( HASONEVALUE ( 'Backtest'[Quarter] ), IF ( SUM ( 'Backtest'[Inside] ) = 1, \"✓ inside\", \"✗ outside\" ) )", None),
    ],
    "Models": [
        ("Holdout Error", "DIVIDE ( SUM ( 'Models'[MAPE_Holdout] ), 100 )", "0.0%"),
        ("Selection Error", "DIVIDE ( SUM ( 'Models'[MAPE_Select] ), 100 )", "0.0%"),
        ("Ensemble Weight", "SUM ( 'Models'[Weight] )", "0%"),
    ],
}
RELATIONSHIPS = [("SearchTrend", "Brand", "Brand", "Brand"), ("SearchTrend", "Month", "Months", "Month"),
                 ("SearchGeo", "Brand", "Brand", "Brand"), ("SearchGeo", "GovCode", "Governorate", "GovCode"),
                 ("Revenue_Q", "Company", "Company", "Company"), ("Revenue_FY", "Company", "Company", "Company"),
                 ("Models", "Company", "Company", "Company"), ("Backtest", "Company", "Company", "Company")]


def q(name):
    return f"'{name}'" if any(c in name for c in " ()-") else name


def lt(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "egypt-pulse/" + "/".join(parts)))


def tmdl_table(t, cols):
    out = [f"table {q(t)}", f"\tlineageTag: {lt(t)}", ""]
    for name, expr, fmt in MEASURES.get(t, []):
        lines = expr.split("\n")
        if len(lines) == 1:
            out.append(f"\tmeasure {q(name)} = {expr}")
        else:
            out.append(f"\tmeasure {q(name)} =")
            out += [f"\t\t\t{ln}" for ln in lines]
        if fmt:
            out.append(f"\t\tformatString: {fmt}")
        out += [f"\t\tlineageTag: {lt(t, 'm', name)}", ""]
    for c, dt in cols:
        out.append(f"\tcolumn {q(c)}")
        out.append(f"\t\tdataType: {dt}")
        if (t, c) in FORMAT:
            out.append(f"\t\tformatString: {FORMAT[(t, c)]}")
        out.append("\t\tsummarizeBy: none")
        out.append(f"\t\tsourceColumn: {c}")
        if (t, c) in SORT_BY:
            out.append(f"\t\tsortByColumn: {SORT_BY[(t, c)]}")
        out.append(f"\t\tlineageTag: {lt(t, c)}")
        out.append("")
        out.append("\t\tannotation SummarizationSetBy = User")
        out.append("")
    types = ", ".join(f'{{"{c}", {M_TYPE[dt]}}}' for c, dt in cols)
    m = [
        "let",
        '    Bytes = if Text.StartsWith(XlsxPath, "http") then Web.Contents(XlsxPath) else File.Contents(XlsxPath),',
        "    Source = Excel.Workbook(Bytes, null, true),",
        f'    Data = Source{{[Item="{t}",Kind="Sheet"]}}[Data],',
        "    Promoted = Table.PromoteHeaders(Data, [PromoteAllScalars=true]),",
        f"    Typed = Table.TransformColumnTypes(Promoted, {{{types}}})",
        "in",
        "    Typed",
    ]
    out.append(f"\tpartition {q(t)} = m")
    out.append("\t\tmode: import")
    out.append("\t\tsource =")
    out += [f"\t\t\t\t{ln}" for ln in m]
    out.append("")
    out.append("\tannotation PBI_ResultType = Table")
    out.append("")
    return "\n".join(out)


def write_model():
    d = SM / "definition"
    (d / "tables").mkdir(parents=True, exist_ok=True)
    (SM / "definition.pbism").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {}}, indent=2), encoding="utf-8")
    (SM / ".platform").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": NAME}, "config": {"version": "2.0", "logicalId": lt("sm")}}, indent=2), encoding="utf-8")
    (d / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1606\n", encoding="utf-8")
    model = ["model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3", "\tsourceQueryCulture: en-US",
             "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
             f"annotation PBI_QueryOrder = {json.dumps(['XlsxPath'] + list(TABLES))}", "",
             "annotation __PBI_TimeIntelligenceEnabled = 0", ""]
    model += [f"ref table {q(t)}" for t in TABLES]
    (d / "model.tmdl").write_text("\n".join(model) + "\n", encoding="utf-8")
    xl = (DATA_URL or str(XLSX)).replace('"', '""')
    (d / "expressions.tmdl").write_text(
        f'expression XlsxPath = "{xl}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {lt('XlsxPath')}\n\n\tannotation PBI_ResultType = Text\n", encoding="utf-8")
    rel = []
    for ft, fc, tt, tc in RELATIONSHIPS:
        rel += [f"relationship {lt('rel', ft, fc)}", f"\tfromColumn: {q(ft)}.{q(fc)}", f"\ttoColumn: {q(tt)}.{q(tc)}", ""]
    (d / "relationships.tmdl").write_text("\n".join(rel), encoding="utf-8")
    for t, cols in TABLES.items():
        (d / "tables" / f"{t}.tmdl").write_text(tmdl_table(t, cols), encoding="utf-8")


# ------------------------------------------------------------------ report helpers
def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, int):
        return {"expr": {"Literal": {"Value": f"{v}L"}}}
    if isinstance(v, float):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}


def color(hexv):
    return {"solid": {"color": lit(hexv)}}


def col(entity, prop):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def meas(entity, prop):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def proj(field):
    k = "Column" if "Column" in field else "Measure"
    e = field[k]["Expression"]["SourceRef"]["Entity"]
    p = field[k]["Property"]
    return {"field": field, "queryRef": f"{e}.{p}", "nativeQueryRef": p}


def F(spec):
    """'Table.Col' -> column, 'Table.[Measure]' -> measure."""
    t, p = spec.split(".", 1)
    return meas(t, p[1:-1]) if p.startswith("[") else col(t, p)


def container(title=None, bare=False, pad=0):
    o = {
        "title": [{"properties": {"show": lit(bool(title)), **({"text": lit(title), "fontSize": lit(12.0), "fontColor": color("#1C2928"), "bold": lit(True)} if title else {})}}],
        "padding": [{"properties": {"top": lit(float(pad)), "bottom": lit(float(pad)), "left": lit(float(pad)), "right": lit(float(pad))}}],
    }
    if bare:
        o["background"] = [{"properties": {"show": lit(False)}}]
        o["border"] = [{"properties": {"show": lit(False)}}]
        o["dropShadow"] = [{"properties": {"show": lit(False)}}]
    return o


def visual(name, pos, z, body):
    x, y, w, h = pos
    return {"$schema": f"{SCHEMA}/visualContainer/2.4.0/schema.json", "name": name,
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z}, "visual": body}


def custom(name, pos, z, mode, fields, values=(), page="", title="", subtitle="", bare=False):
    qs = {"fields": {"projections": [proj(F(s)) for s in fields]}}
    if values:
        qs["values"] = {"projections": [proj(F(s)) for s in values]}
    body = {"visualType": GUID, "query": {"queryState": qs},
            "objects": {"settings": [{"properties": {"mode": lit(mode), "page": lit(page), "title": lit(title), "subtitle": lit(subtitle)}}]},
            "visualContainerObjects": container(None, bare=bare, pad=0), "drillFilterOtherVisuals": True}
    return visual(name, pos, z, body)


def bar(name, pos, z, cat, val, title, color_measure=None, fill="#0B6E69", top=None, bare=False):
    objs = {
        "categoryAxis": [{"properties": {"showAxisTitle": lit(False), "fontSize": lit(10.0), "labelColor": color("#4F5F5C"), "innerPadding": lit(28.0)}}],
        "valueAxis": [{"properties": {"show": lit(False), "gridlineShow": lit(False), "showAxisTitle": lit(False)}}],
        "labels": [{"properties": {"show": lit(True), "fontSize": lit(10.0), "color": color("#1C2928")}}],
        "dataPoint": [{"properties": {"fill": color(fill)}}],
    }
    if color_measure:
        objs["dataPoint"].append({"properties": {"fill": {"solid": {"color": {"expr": F(color_measure)}}}},
                                  "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}})
    body = {"visualType": "barChart",
            "query": {"queryState": {"Category": {"projections": [{**proj(F(cat)), "active": True}]}, "Y": {"projections": [proj(F(val))]}},
                      "sortDefinition": {"sort": [{"field": F(val), "direction": "Descending"}]}},
            "objects": objs, "visualContainerObjects": container(title, bare=bare, pad=6), "drillFilterOtherVisuals": True}
    return visual(name, pos, z, body)


def tproj(s):
    spec, _, nm = s.partition("|")
    pr = proj(F(spec))
    if nm:
        pr["displayName"] = nm
    return pr


def table(name, pos, z, cols_, title, sort=1, desc=False, bare=False):
    body = {"visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": [tproj(s) for s in cols_]}},
                      "sortDefinition": {"sort": [{"field": F(cols_[sort].split("|")[0]), "direction": "Descending" if desc else "Ascending"}]}},
            "objects": {"columnHeaders": [{"properties": {"fontColor": color("#4F5F5C"), "backColor": color("#FBF7F0"), "fontSize": lit(10.0)}}],
                        "values": [{"properties": {"fontSize": lit(10.5), "fontColorPrimary": color("#1C2928")}}],
                        "total": [{"properties": {"totals": lit(False)}}],
                        "grid": [{"properties": {"gridHorizontal": lit(True), "gridHorizontalColor": color("#EFE8DC"), "rowPadding": lit(5)}}]},
            "visualContainerObjects": container(title, bare=bare, pad=6), "drillFilterOtherVisuals": True}
    return visual(name, pos, z, body)


def slicer(name, pos, z, field, selected, cols, sync=None):
    entity, prop = field.split(".")
    flt = {"Version": 2, "From": [{"Name": "s", "Entity": entity, "Type": 0}],
           "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": prop}}],
                                           "Values": [[lit(selected)["expr"]]]}}}]}
    body = {"visualType": "advancedSlicerVisual",
            "query": {"queryState": {"Values": {"projections": [{**proj(col(entity, prop)), "active": True}]}}},
            "objects": {
                "general": [{"properties": {"filter": {"filter": flt}}}],
                "selection": [{"properties": {"singleSelect": lit(True), "strictSingleSelect": lit(True)}}],
                "layout": [{"properties": {"rowCount": lit(1), "columnCount": lit(cols), "cellPadding": lit(4.0)}}],
                "shapeCustomRectangle": [{"properties": {"tileShape": lit("rectangleRoundedByPixel"), "rectangleRoundedCurve": lit(10)}, "selector": {"id": "default"}}],
                "fillCustom": [{"properties": {"show": lit(True), "fillColor": color("#FFFFFF"), "transparency": lit(0.0)}, "selector": {"id": "default"}},
                               {"properties": {"fillColor": color("#0B6E69"), "transparency": lit(0.0)}, "selector": {"id": "selection:selected"}},
                               {"properties": {"fillColor": color("#E3F1EF"), "transparency": lit(0.0)}, "selector": {"id": "interaction:hover"}}],
                "outline": [{"properties": {"show": lit(True), "lineColor": color("#E2D9C9"), "weight": lit(1.0)}, "selector": {"id": "default"}},
                            {"properties": {"lineColor": color("#0B6E69")}, "selector": {"id": "selection:selected"}}],
                "value": [{"properties": {"fontColor": color("#1C2928"), "fontSize": lit(11.0), "bold": lit(True),
                                          "fontFamily": lit("'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif")}, "selector": {"id": "default"}},
                          {"properties": {"fontColor": color("#FFFFFF")}, "selector": {"id": "selection:selected"}}],
                "label": [{"properties": {"show": lit(False)}, "selector": {"id": "default"}}],
                "accentBar": [{"properties": {"show": lit(False)}, "selector": {"id": "default"}}],
            },
            "visualContainerObjects": container(None, bare=True), "drillFilterOtherVisuals": True}
    if sync:
        body["syncGroup"] = {"groupName": sync, "fieldChanges": True, "filterChanges": True}
    return visual(name, pos, z, body)


def button(name, pos, z, text, target, primary=True):
    fg, bg, hv = ("#FFFFFF", "#0B6E69", "#12958B") if primary else ("#0B6E69", "#FFFFFF", "#E3F1EF")
    body = {"visualType": "actionButton",
            "objects": {
                "icon": [{"properties": {"shapeType": lit("blank")}, "selector": {"id": "default"}}],
                "text": [{"properties": {"show": lit(True)}},
                         {"properties": {"text": lit(text), "fontColor": color(fg), "fontSize": lit(13.0), "bold": lit(True),
                                         "fontFamily": lit("'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif")}, "selector": {"id": "default"}}],
                "fill": [{"properties": {"show": lit(True)}},
                         {"properties": {"fillColor": color(bg), "transparency": lit(0.0)}, "selector": {"id": "default"}},
                         {"properties": {"fillColor": color(hv), "transparency": lit(0.0)}, "selector": {"id": "hover"}}],
                "outline": [{"properties": {"show": lit(not primary), "lineColor": color("#0B6E69"), "weight": lit(1.0)}, "selector": {"id": "default"}}],
                "shape": [{"properties": {"tileShape": lit("rectangleRoundedByPixel"), "rectangleRoundedCurve": lit(12)}}],
            },
            "visualContainerObjects": {**container(None, bare=True),
                                       "visualLink": [{"properties": {"show": lit(True), "type": lit("PageNavigation"), "navigationSection": lit(target)}}]},
            "drillFilterOtherVisuals": True}
    return visual(name, pos, z, body)


KPI_F = ["KPI.Page", "KPI.Ord", "KPI.Label", "KPI.LabelAR", "KPI.Display", "KPI.Sub", "KPI.SubAR", "KPI.Icon", "KPI.Source"]
INS_F = ["Insight.Page", "Insight.Ord", "Insight.Title", "Insight.TitleAR", "Insight.Body", "Insight.BodyAR", "Insight.Source"]
TREND_F = (["Months.Month", "Brand.Brand", "Brand.Color", "Brand.Category"], ["SearchTrend.[Search Interest]", "SearchTrend.[Event]"])
MAP_F = (["Governorate.GovCode", "Governorate.Governorate", "Governorate.GovernorateAR", "Governorate.Region", "Governorate.UrbanPop"],
         ["SearchGeo.[Leader]", "SearchGeo.[Leader Share]", "SearchGeo.[Leader Color]", "SearchGeo.[Runner Up]", "SearchGeo.[Runner Share]",
          "SearchGeo.[Focus Brand]", "SearchGeo.[Focus Share]", "SearchGeo.[Focus Color]"])


def header(page, title, sub):
    return custom(f"{page}Header", (16, 10, 740, 66), 10, "header", ["KPI.Page"], title=title, subtitle=sub, bare=True)


FEED_F = ["Feed.Dataset", "Feed.Seq", "Feed.Json"]


def page_visual(page):
    """One full-canvas HTML visual per page; it draws the page and hosts the Ask AI node."""
    return custom("marketPortal", (0, 0, 1280, 720), 10, "page", FEED_F, page=page, bare=True)


# ------------------------------------------------------------------ native Power BI visuals
def card(name, pos, z, measure, title, size=22.0, fg="#0B6E69", fg_measure=None):
    fill = {"solid": {"color": {"expr": F(fg_measure)}}} if fg_measure else color(fg)
    body = {"visualType": "card",
            "query": {"queryState": {"Values": {"projections": [proj(F(measure))]}}},
            "objects": {"labels": [{"properties": {"fontSize": lit(size), "color": fill, "labelDisplayUnits": lit(1.0)}}],
                        "categoryLabels": [{"properties": {"show": lit(False)}}],
                        "wordWrap": [{"properties": {"show": lit(True)}}]},
            "visualContainerObjects": container(title, pad=6), "drillFilterOtherVisuals": True}
    return visual(name, pos, z, body)


def line(name, pos, z, cat, vals, title, series=None, colors=None, series_colors=None, bare=False, widths=None):
    qs = {"Category": {"projections": [{**proj(F(cat)), "active": True}]}, "Y": {"projections": [proj(F(v)) for v in vals]}}
    if series:
        qs["Series"] = {"projections": [proj(F(series))]}
    objs = {
        "categoryAxis": [{"properties": {"showAxisTitle": lit(False), "fontSize": lit(9.0), "labelColor": color("#4F5F5C")}}],
        "valueAxis": [{"properties": {"showAxisTitle": lit(False), "fontSize": lit(9.0), "labelColor": color("#4F5F5C"), "gridlineColor": color("#EFE8DC")}}],
        "legend": [{"properties": {"show": lit(True), "position": lit("Top"), "fontSize": lit(9.0)}}],
        "lineStyles": [{"properties": {"strokeWidth": lit(2)}}],
    }
    if colors:
        objs["dataPoint"] = [{"properties": {"fill": color(c)}, "selector": {"metadata": proj(F(v))["queryRef"]}} for v, c in zip(vals, colors)]
    if widths:
        objs["lineStyles"] += [{"properties": {"strokeWidth": lit(w)}, "selector": {"metadata": proj(F(v))["queryRef"]}} for v, w in zip(vals, widths)]
    if series and series_colors:
        objs["dataPoint"] = [{"properties": {"fill": color(c)}, "selector": {"data": [{"scopeId": {"Comparison": {
            "ComparisonKind": 0, "Left": F(series), "Right": {"Literal": {"Value": "'" + k + "'"}}}}}]}} for k, c in series_colors.items()]
    body = {"visualType": "lineChart",
            "query": {"queryState": qs, "sortDefinition": {"sort": [{"field": F(cat), "direction": "Ascending"}]}},
            "objects": objs, "visualContainerObjects": container(title, bare=bare, pad=6), "drillFilterOtherVisuals": True}
    return visual(name, pos, z, body)


def textbox(name, pos, z, title, sub=""):
    paras = [{"textRuns": [{"value": title, "textStyle": {"fontWeight": "bold", "fontSize": "17pt", "color": "#1C2928"}}]}]
    if sub:
        paras.append({"textRuns": [{"value": sub, "textStyle": {"fontSize": "9.5pt", "color": "#4F5F5C"}}]})
    body = {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": paras}}]}, "visualContainerObjects": container(None, bare=True)}
    return visual(name, pos, z, body)


import layout as LY  # noqa: E402  (shared with tools/make_backgrounds.py)

TONES = {b["Brand"]: b["Tone"] for b in json.loads((HERE / "data" / "egypt_data.json").read_text(encoding="utf-8"))["Brand"]}
NOTES_F = ["Notes.Page", "Notes.Ord", "Notes.Tone", "Notes.Title", "Notes.TitleAR", "Notes.Body", "Notes.Source", "Notes.Category", "Notes.Company"]
FC_F = ["Revenue_Q.Quarter", "Revenue_Q.QuarterEnd", "Revenue_Q.RevenueEGP", "Revenue_Q.BacktestEGP", "Revenue_Q.ForecastEGP",
        "Revenue_Q.Lo80", "Revenue_Q.Hi80", "Revenue_Q.ActualUSD", "Revenue_Q.ForecastUSD"]
PATHS = ["Revenue_Q.[Actual (EGP M)]", "Revenue_Q.[Ensemble Forecast]", "Revenue_Q.[Seasonal naive path]", "Revenue_Q.[Naive + drift path]",
         "Revenue_Q.[Holt-Winters path]", "Revenue_Q.[Theta path]", "Revenue_Q.[SARIMA path]", "Revenue_Q.[OLS path]"]
# actual ink, ensemble teal, the six single models in quiet teal / gold / sand tints (thin)
PATH_COLORS = ["#1C2928", "#0B6E69", "#D3C9B6", "#B5AA95", "#7FB8B3", "#E0C27A", "#4F8F8A", "#A07F3C"]
PATH_WIDTHS = [3, 3, 1, 1, 1, 1, 1, 1]
IMAGES = []          # registered image resources
BOOKMARKS = []       # (name, display, page, targets, shown)
NO_FILTER = {}
PAGE_FILTERS = {"delivery": ("Brand", "Category", "Delivery apps")}


def in_filter(entity, prop, values):
    return {"Version": 2, "From": [{"Name": "s", "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": prop}}],
                                            "Values": [[lit(v)["expr"]] for v in values]}}}]}


def vfilter(v, field, values):
    e, p = field.split(".")
    v["filterConfig"] = {"filters": [{"name": v["name"] + "F", "field": col(e, p), "type": "Categorical", "filter": in_filter(e, p, values)}]}
    return v


def image(name, pos, z, item):
    if item not in IMAGES:
        IMAGES.append(item)
    body = {"visualType": "image",
            "objects": {"general": [{"properties": {"imageUrl": {"expr": {"ResourcePackageItem": {
                "PackageName": "RegisteredResources", "PackageType": 1, "ItemName": item}}}}}],
                "imageScaling": [{"properties": {"imageScalingType": lit("Fit")}}]},
            "visualContainerObjects": container(None, bare=True)}
    return visual(name, pos, z, body)


def hit(name, pos, z, link, hover=True):
    """An invisible button over something drawn in the background: page link, bookmark or clear-all."""
    fill = [{"properties": {"show": lit(True)}},
            {"properties": {"fillColor": color("#FFFFFF"), "transparency": lit(100.0)}, "selector": {"id": "default"}}]
    if hover:
        fill.append({"properties": {"fillColor": color("#0B6E69"), "transparency": lit(92.0)}, "selector": {"id": "hover"}})
    props = {"show": lit(True)}
    props.update({k: lit(v) for k, v in link.items()})
    body = {"visualType": "actionButton",
            "objects": {"icon": [{"properties": {"shapeType": lit("blank")}, "selector": {"id": "default"}}],
                        "text": [{"properties": {"show": lit(False)}}], "fill": fill,
                        "outline": [{"properties": {"show": lit(False)}}],
                        "shape": [{"properties": {"tileShape": lit("rectangleRoundedByPixel"), "rectangleRoundedCurve": lit(12)}}]},
            "visualContainerObjects": {**container(None, bare=True), "visualLink": [{"properties": props}],
                                       "visualHeader": [{"properties": {"show": lit(False)}}]},   # no hover icons over click targets
            "drillFilterOtherVisuals": True}
    return visual(name, pos, z, body)


def vcard(name, pos, z, measure, size=20.0, fg="#0B6E69", fg_measure=None, wrap=False):
    fill = {"solid": {"color": {"expr": F(fg_measure)}}} if fg_measure else color(fg)
    body = {"visualType": "card",
            "query": {"queryState": {"Values": {"projections": [proj(F(measure))]}}},
            "objects": {"labels": [{"properties": {"fontSize": lit(size), "color": fill, "labelDisplayUnits": lit(1.0),
                                                   "fontFamily": lit("'Segoe UI Semibold'")}}],
                        "categoryLabels": [{"properties": {"show": lit(False)}}],
                        "wordWrap": [{"properties": {"show": lit(wrap)}}]},
            "visualContainerObjects": container(None, bare=True), "drillFilterOtherVisuals": True}
    return visual(name, pos, z, body)


def dropdown(name, pos, z, field, header, single=False, default=None, sync=None):
    e, p = field.split(".")
    gen = {"outlineColor": color("#E1E6E4"), "outlineWeight": lit(1.0)}
    if default:
        gen["filter"] = {"filter": in_filter(e, p, [default])}
    body = {"visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": [{**proj(col(e, p)), "active": True}]}}},
            "objects": {
                "data": [{"properties": {"mode": lit("Dropdown")}}],
                "header": [{"properties": {"show": lit(True), "text": lit(header.upper()), "fontColor": color("#0B6E69"), "textSize": lit(8.0),
                                           "fontFamily": lit("'Segoe UI Semibold'"), "background": color("#FFFFFF")}}],
                "items": [{"properties": {"fontColor": color("#1C2928"), "background": color("#FFFFFF"), "textSize": lit(10.0),
                                          "fontFamily": lit("'Segoe UI'")}}],
                "general": [{"properties": gen}],
                "selection": [{"properties": {"strictSingleSelect": lit(single), "singleSelect": lit(single), "selectAllCheckboxEnabled": lit(not single)}}]},
            "visualContainerObjects": {
                "background": [{"properties": {"show": lit(True), "color": color("#FFFFFF"), "transparency": lit(0.0)}}],
                "border": [{"properties": {"show": lit(True), "color": color("#E8E1D4"), "radius": lit(10.0), "width": lit(1.0)}}],
                "dropShadow": [{"properties": {"show": lit(True), "color": color("#3C2D14"), "position": lit("Outer"), "preset": lit("Custom"),
                                               "shadowSpread": lit(0.0), "shadowBlur": lit(12.0), "angle": lit(90.0), "shadowDistance": lit(3.0),
                                               "transparency": lit(88.0)}}],
                "title": [{"properties": {"show": lit(False)}}], "visualHeader": [{"properties": {"show": lit(False)}}],
                "padding": [{"properties": {"top": lit(2.0), "bottom": lit(2.0), "left": lit(6.0), "right": lit(6.0)}}]},
            "drillFilterOtherVisuals": True}
    if sync:
        body["syncGroup"] = {"groupName": sync, "fieldChanges": True, "filterChanges": True}
    return visual(name, pos, z, body)


def switch(name, pos, z, field, default):
    """A horizontal single-select list (a 'Basic' style slicer) that swaps the measure a chart shows."""
    e, p = field.split(".")
    body = {"visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": [{**proj(col(e, p)), "active": True}]}}},
            "objects": {
                "data": [{"properties": {"mode": lit("Basic")}}],
                "header": [{"properties": {"show": lit(False)}}],
                "items": [{"properties": {"fontColor": color("#0B6E69"), "background": color("#F1F7F5"), "textSize": lit(8.5),
                                          "fontFamily": lit("'Segoe UI Semibold'")}}],
                "general": [{"properties": {"outlineColor": color("#DCE7E4"), "outlineWeight": lit(1.0), "orientation": lit(1.0),
                                            "filter": {"filter": in_filter(e, p, [default])}}}],
                "selection": [{"properties": {"strictSingleSelect": lit(True), "singleSelect": lit(True), "selectAllCheckboxEnabled": lit(False)}}]},
            "visualContainerObjects": container(None, bare=True), "drillFilterOtherVisuals": True}
    return visual(name, pos, z, body)


def drillbar(name, pos, z, cats, val, fill="#0B6E69", column=False, vals=None, colors=None):
    vals = vals or [val]
    qs = {"Category": {"projections": [{**proj(F(cats[0])), "active": True}] + [proj(F(c)) for c in cats[1:]]},
          "Y": {"projections": [proj(F(v)) for v in vals]}}
    objs = {"categoryAxis": [{"properties": {"showAxisTitle": lit(False), "fontSize": lit(9.0), "labelColor": color("#4F5F5C")}}],
            "valueAxis": [{"properties": {"show": lit(False), "gridlineShow": lit(False), "showAxisTitle": lit(False)}}],
            "labels": [{"properties": {"show": lit(True), "fontSize": lit(9.0), "color": color("#1C2928")}}],
            "dataPoint": [{"properties": {"fill": color(fill)}}]}
    if colors:
        objs["dataPoint"] = [{"properties": {"fill": color(c)}, "selector": {"metadata": proj(F(v))["queryRef"]}} for v, c in zip(vals, colors)]
        objs["legend"] = [{"properties": {"show": lit(True), "position": lit("Top"), "fontSize": lit(8.5)}}]
    body = {"visualType": "clusteredColumnChart" if column else "clusteredBarChart",
            "query": {"queryState": qs, "sortDefinition": {"sort": [{"field": F(cats[0]) if column else F(vals[0]), "direction": "Ascending" if column else "Descending"}]}},
            "objects": objs, "visualContainerObjects": container(None, bare=True), "drillFilterOtherVisuals": True}
    return visual(name, pos, z, body)


def matrix(name, pos, z, rows, cols, val):
    body = {"visualType": "pivotTable",
            "query": {"queryState": {"Rows": {"projections": [proj(F(rows))]}, "Columns": {"projections": [proj(F(cols))]},
                                     "Values": {"projections": [proj(F(val))]}}},
            "objects": {"columnHeaders": [{"properties": {"fontColor": color("#4F5F5C"), "backColor": color("#FBF7F0"), "fontSize": lit(9.5)}}],
                        "rowHeaders": [{"properties": {"fontColor": color("#1C2928"), "fontSize": lit(10.0)}}],
                        "values": [{"properties": {"fontSize": lit(10.0), "fontColorPrimary": color("#1C2928")}}],
                        "subTotals": [{"properties": {"rowSubtotals": lit(False), "columnSubtotals": lit(False)}}],
                        "grid": [{"properties": {"gridHorizontal": lit(True), "gridHorizontalColor": color("#EFE8DC"), "rowPadding": lit(6)}}]},
            "visualContainerObjects": container(None, bare=True), "drillFilterOtherVisuals": True}
    return visual(name, pos, z, body)


def inner(box, top=46):
    x, y, w, h = box
    return (x + 8, y + top, w - 16, h - top - 8)


def tile_value(box):
    x, y, w, h = box
    return (x + 8, y + 36, w - 16, h - 42)


def no_header(v):
    """Hide Power BI's hover header (filter / focus / more icons): on the chat panel it covers the close button."""
    v["visual"].setdefault("visualContainerObjects", {})["visualHeader"] = [{"properties": {"show": lit(False)}}]
    return v


def hidden(vs):
    for v in vs:
        v["isHidden"] = True
    return vs


# popup bodies, inside layout.POPUP_BODY (264, 132, 752, 528)
def popup_body(page, key, z):
    p = f"{page}_{key}_"
    if (page, key) == ("search", "leader"):
        return [matrix(p + "m", (264, 132, 752, 372), z, "Governorate.Region", "Brand.Brand", "SearchGeo.[Geo Share]"),
                vcard(p + "t", (264, 514, 752, 146), z + 1, "Brand.[Search Insight]", 12.0, "#1C2928", wrap=True)]
    if (page, key) == ("search", "led"):
        return [table(p + "t", (264, 132, 752, 528), z, ["Governorate.Governorate", "SearchGeo.[Leader]", "SearchGeo.[Leader Share]",
                                                       "SearchGeo.[Runner Up]", "SearchGeo.[Runner Share]", "SearchGeo.[Lead Margin]"],
                      None, sort=5, desc=True, bare=True)]
    if (page, key) == ("search", "urban"):
        return [drillbar(p + "b", (264, 132, 470, 528), z, ["Governorate.Governorate"], "Governorate.[Urban Consumers (M)]"),
                vfilter(table(p + "k", (746, 132, 270, 528), z + 1, ["KPI.Label", "KPI.Display", "KPI.Sub"], None, sort=0, bare=True), "KPI.Page", ["where"])]
    if (page, key) == ("delivery", "talabat"):
        return [drillbar(p + "b", (264, 132, 470, 528), z, ["Governorate.Governorate"], "SearchGeo.[talabat Share]", fill="#0B6E69"),
                vfilter(table(p + "k", (746, 132, 270, 528), z + 1, ["KPI.Label", "KPI.Display", "KPI.Sub"], None, sort=0, bare=True), "KPI.Page", ["delivery"])]
    if (page, key) == ("delivery", "breadfast"):
        return [line(p + "l", (264, 132, 752, 250), z, "Months.Month", ["SearchTrend.[Breadfast Interest]"], None, colors=["#C2922F"], bare=True),
                drillbar(p + "b", (264, 394, 470, 266), z + 1, ["Governorate.Governorate"], "SearchGeo.[Breadfast Share]", fill="#C2922F"),
                vcard(p + "t", (746, 394, 270, 266), z + 2, "Insight.[Delivery Insight]", 11.0, "#1C2928", wrap=True)]
    if (page, key) == ("forecast", "f27"):
        return [vfilter(line(p + "l", (264, 132, 752, 250), z, "Revenue_Q.Quarter", PATHS, None, colors=PATH_COLORS, widths=PATH_WIDTHS, bare=True),
                        "Revenue_Q.Year", [2024, 2025, 2026, 2027]),
                vfilter(table(p + "t", (264, 394, 752, 266), z + 1, ["Revenue_Q.Quarter", "Revenue_Q.[Forecast Low]|At 9% inflation",
                                                                   "Revenue_Q.[Ensemble Forecast]|Base (13.9%)", "Revenue_Q.[Forecast High]|At 20% inflation",
                                                                   "Revenue_Q.[Low 80%]|80% band low", "Revenue_Q.[High 80%]|80% band high",
                                                                   "Revenue_Q.[Real (2021 prices)]|In 2021 prices"], None, sort=0, bare=True),
                        "Revenue_Q.Year", [2026, 2027])]
    if (page, key) == ("forecast", "err"):
        return [table(p + "m", (264, 132, 440, 300), z, ["Models.Model", "Models.[Selection Error]", "Models.[Holdout Error]", "Models.[Ensemble Weight]"],
                      None, sort=2, bare=True),
                table(p + "b", (716, 132, 300, 300), z + 1, ["Revenue_Q.Quarter", "Revenue_Q.[Actual (backtest quarters)]", "Revenue_Q.[Backtest (EGP M)]",
                                                           "Revenue_Q.[Backtest Error]"], None, sort=0, bare=True),
                vcard(p + "n", (264, 444, 752, 106), z + 2, "Company.[Method Note]", 11.0, "#1C2928", wrap=True),
                vcard(p + "a", (264, 554, 752, 106), z + 3, "Company.[Accuracy Note]", 10.0, "#4F5F5C", wrap=True)]
    if (page, key) == ("deepdive", "acc"):
        return [drillbar(p + "h", (264, 132, 300, 300), z, ["Backtest.Horizon"], None, column=True, vals=["Backtest.[Horizon Error]"],
                         colors=["#C2922F"]),
                table(p + "t", (576, 132, 440, 300), z + 1, ["Backtest.Origin", "Backtest.Quarter", "Backtest.Horizon", "Backtest.[Backtest Actual]",
                                                           "Backtest.[Backtest Forecast]", "Backtest.[Band Low]", "Backtest.[Band High]", "Backtest.[In Band]"],
                      None, sort=0, bare=True),
                vcard(p + "n", (264, 444, 752, 216), z + 2, "Company.[Method Note]", 12.0, "#1C2928", wrap=True)]
    raise KeyError((page, key))


TILE_POPUP = {"search": ["leader", "leader", "led", "led", "urban"], "delivery": ["talabat", "talabat", "breadfast", "breadfast", "breadfast"],
              "forecast": ["f27", "f27", "f27", "f27", "err"], "deepdive": ["acc"] * 5}


def native_page(page, content, tile_measures):
    """Background, rail links, header buttons, numbered notes, tile values with their popup links, popups and the AI popup."""
    spec = LY.PAGES[page]
    vs = [image(f"{page}Bg", (0, 0, 1280, 720), 0, f"bg_{page}.png")]
    for i, (k, x, y, w, h) in enumerate(LY.nav_boxes()):
        if k != page:
            vs.append(hit(f"{page}Nav{i}", (x, y, w, h), 20000 + i, {"type": "PageNavigation", "navigationSection": k,
                                                                    "tooltip": f"Go to {LY.RAIL[i][1]}"}))
    vs.append(hit(f"{page}Ask", LY.ASK, 20010, {"type": "Bookmark", "bookmark": f"bm{page}AiOn", "tooltip": "Ask AI about this page"}))
    if spec.get("slicers"):
        vs.append(hit(f"{page}Clear", LY.CLEAR, 20011, {"type": "ClearAllSlicers", "tooltip": "Clear all slicers"}))
    vs += content
    vs.append(vfilter(custom(f"{page}Notes", inner(LY.READ, 50), 650, "notes", NOTES_F, values=["Notes.[Show Note]"], page=page, bare=True),
                      "Notes.Page", [page]))
    for i, ((box, _en, _ar, _ic), (measure, kw)) in enumerate(zip(spec["tiles"], tile_measures)):
        vs.append(vcard(f"{page}Tile{i}", tile_value(box), 1000 + i, measure, **{"size": 19.0, "fg": "#1C2928", **kw}))
        key = TILE_POPUP[page][i]
        if key:
            vs.append(hit(f"{page}TileHit{i}", box, 1100 + i, {"type": "Bookmark", "bookmark": f"bm{page}{key.title()}On",
                                                                "tooltip": f"Click for details: {spec['popups'][key]}"}, hover=True))
    groups = {}
    z = 30000
    for key in list(spec["popups"]) + ["ai"]:
        if key == "ai":
            g = [image(f"{page}_ai_bg", (0, 0, 1280, 720), z, "pop_ai.png"),
                 no_header(custom(f"{page}_ai_panel", LY.AI_PANEL, z + 1, "ai", ["Sources.Id"], page=page)),
                 hit(f"{page}_ai_x", LY.AI_CLOSE, z + 2, {"type": "Bookmark", "bookmark": f"bm{page}Off", "tooltip": "Close"})]
        else:
            g = [image(f"{page}_{key}_bg", (0, 0, 1280, 720), z, f"pop_{page}_{key}.png")] + popup_body(page, key, z + 1) + \
                [hit(f"{page}_{key}_x", LY.POPUP_CLOSE, z + 20, {"type": "Bookmark", "bookmark": f"bm{page}Off", "tooltip": "Close"})]
        hidden(g)
        groups[key] = [v["name"] for v in g]
        vs += g
        z += 100
    targets = [n for ns in groups.values() for n in ns]
    BOOKMARKS.append((f"bm{page}Off", f"{spec['title']} · close", page, targets, set()))
    for key, names in groups.items():
        BOOKMARKS.append((f"bm{page}{key.title()}On", f"{spec['title']} · {key}", page, targets, set(names)))
    return vs


def S(page):
    return LY.PAGES[page]


def P(page, i, top=46):
    return inner(S(page)["panels"][i][0], top)


SL = S("search")["slicers"]
SEARCH = native_page("search", [
    dropdown("searchCat", SL[0][2], 500, SL[0][0], SL[0][1], single=True, default="Soft drinks", sync="category"),
    dropdown("searchRegion", SL[1][2], 501, SL[1][0], SL[1][1]),
    dropdown("searchGov", SL[2][2], 502, SL[2][0], SL[2][1]),
    custom("searchMap", P("search", 0), 600, "map", *MAP_F, title=" ", subtitle=" ", bare=True),
    bar("searchBrands", P("search", 1), 601, "Brand.Brand", "SearchTrend.[Share of Search]", None,
        color_measure="SearchTrend.[Brand Color]", bare=True),
    drillbar("searchDrill", P("search", 2), 602, ["Governorate.Region", "Governorate.Governorate"], "SearchGeo.[Leader Share]"),
], [("Brand.[Category Leader]", {"fg_measure": "Brand.[Category Leader Color]"}), ("Brand.[Leader National Share]", {"fg_measure": "Brand.[Category Leader Color]"}),
    ("Brand.[Governorates Led]", {}), ("Brand.[Category Runner]", {"fg": "#C2922F"}), ("Governorate.[Urban Consumers (M)]", {})])

SD = S("delivery")["slicers"]
DELIVERY = native_page("delivery", [
    dropdown("dlvBrand", SD[0][2], 500, SD[0][0], SD[0][1]),
    dropdown("dlvYear", SD[1][2], 501, SD[1][0], SD[1][1]),
    switch("dlvMetric", S("delivery")["switch"], 502, "TrendMetric.Metric", "Interest"),
    line("dlvTrend", P("delivery", 0), 600, "Months.Month", ["SearchTrend.[Trend Value]"], None, series="Brand.Brand",
         series_colors=TONES, bare=True),
    table("dlvMomentum", P("delivery", 1), 601, ["Brand.Brand|App", "SearchTrend.[Interest 2021]|2021 avg", "SearchTrend.[Interest Last 12M]|Last 12M avg",
                                                 "Brand.[Search Growth]|Growth (x)"], None, sort=3, desc=True, bare=True),
    bar("dlvShare", P("delivery", 2), 602, "Brand.Brand", "SearchTrend.[Share of Search]", None,
        color_measure="SearchTrend.[Brand Color]", bare=True),
], [("KPI.[talabat Lead]", {"fg": "#0B6E69"}), ("KPI.[talabat GMV 2025]", {}), ("KPI.[Breadfast vs talabat]", {"fg": "#C2922F"}),
    ("KPI.[Breadfast Funding]", {"fg": "#C2922F"}), ("Brand.[Fastest Grower]", {"size": 15.0})])
NO_FILTER["delivery"] = [("dlvYear", "dlvShare"), ("dlvYear", "dlvMomentum")]

FORECAST = native_page("forecast", [
    switch("fcScenario", S("forecast")["switch"], 499, "Scenario.Scenario", "Base"),
    slicer("forecastCompany", S("forecast")["company"], 500, "Company.Company", "Edita", 4, sync="company"),
    custom("fcChart", P("forecast", 0), 600, "forecast", FC_F, title=" ", subtitle=" ", bare=True),
    table("fcModels", P("forecast", 1), 601, ["Models.Model", "Models.[Holdout Error]|Error", "Models.[Ensemble Weight]|Weight"], None, sort=1, bare=True),
    drillbar("fcAll", P("forecast", 2), 603, ["Company.Company"], None,
             vals=["Company.[Growth 2027]", "Company.[Real Growth 2027]"], colors=["#0B6E69", "#C2922F"]),
], [("Company.[Revenue 2025 (EGP B)]", {}), ("Revenue_Q.[Scenario 2027 (EGP B)]", {"fg": "#0B6E69"}), ("Company.[Growth 2027]", {"fg": "#0B6E69"}),
    ("Company.[Real Growth 2027]", {"fg": "#C2922F"}), ("Company.[Forecast Error]", {"fg_measure": "Company.[Confidence Color]"})])
NO_FILTER["forecast"] = [("forecastCompany", "fcAll"), ("fcScenario", "fcAll"), ("fcAll", "fcChart"), ("fcAll", "fcModels"), ("fcAll", "forecastNotes")] + \
    [("fcAll", f"forecastTile{i}") for i in range(5)]

DEEPDIVE = native_page("deepdive", [
    slicer("deepdiveCompany", S("deepdive")["company"], 500, "Company.Company", "Edita", 4, sync="company"),
    vfilter(line("ddPaths", P("deepdive", 0), 600, "Revenue_Q.Quarter", PATHS, None, colors=PATH_COLORS, widths=PATH_WIDTHS, bare=True),
            "Revenue_Q.Year", [2024, 2025, 2026, 2027]),
    table("ddQuarters", P("deepdive", 1), 601, ["Revenue_Q.Quarter", "Revenue_Q.[Actual (EGP M)]|Actual", "Revenue_Q.[Backtest (EGP M)]|Backtest",
                                                "Revenue_Q.[Ensemble Forecast]|Forecast"], None, sort=0, desc=True, bare=True),
    drillbar("ddYears", P("deepdive", 2), 602, ["Revenue_Q.Year", "Revenue_Q.Quarter"], None, column=True,
             vals=["Revenue_Q.[Actual (EGP M)]", "Revenue_Q.[Ensemble Forecast]"], colors=["#0B6E69", "#C2922F"]),
], [("Company.[Best Model]", {"size": 14.0}), ("Company.[Forecast Error]", {"fg_measure": "Company.[Confidence Color]"}),
    ("Company.[MASE Score]", {"fg": "#0B6E69"}), ("Company.[Band Coverage]", {"fg": "#C2922F"}),
    ("Company.[Confidence]", {"fg_measure": "Company.[Confidence Color]"})])

PAGES = [
    ("market", "Portal", [page_visual("overview")]),
    ("search", "Search & Map", SEARCH),
    ("delivery", "Delivery", DELIVERY),
    ("forecast", "Forecast", FORECAST),
    ("deepdive", "Deep-dive", DEEPDIVE),
]



def theme():
    return {
        "name": "Egypt Market",
        "dataColors": ["#0B6E69", "#C2922F", "#7FB8B3", "#E0C27A", "#4F8F8A", "#A07F3C", "#B5AA95", "#D3C9B6", "#1C2928"],
        "background": "#FFFFFF", "foreground": "#1C2928", "tableAccent": "#0B6E69",
        "good": "#0B6E69", "bad": "#8A6516", "neutral": "#C2922F",
        "textClasses": {
            "title": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": "#1C2928"},
            "label": {"fontFace": "Segoe UI", "fontSize": 10, "color": "#4F5F5C"},
            "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 28, "color": "#1C2928"},
        },
        "visualStyles": {
            "*": {"*": {
                "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
                "border": [{"show": True, "color": {"solid": {"color": "#E8E1D4"}}, "radius": 14}],
                "dropShadow": [{"show": True, "color": {"solid": {"color": "#3C2D14"}}, "position": "Outer", "preset": "Custom",
                                "shadowSpread": 0, "shadowBlur": 16, "angle": 90, "shadowDistance": 4, "transparency": 86}],
                "title": [{"fontColor": {"solid": {"color": "#1C2928"}}, "fontSize": 12, "fontFamily": "Segoe UI Semibold"}],
                "visualHeader": [{"background": {"solid": {"color": "#FFFFFF"}}, "foreground": {"solid": {"color": "#4F5F5C"}}, "border": {"solid": {"color": "#E8E1D4"}}}],
            }},
            "page": {"*": {
                "background": [{"color": {"solid": {"color": "#F5F0E7"}}, "transparency": 0}],
                "outspace": [{"color": {"solid": {"color": "#ECE4D6"}}, "transparency": 0}],
            }},
        },
    }


def write_report(pbiviz):
    d = RP / "definition"
    (d / "pages").mkdir(parents=True, exist_ok=True)
    (RP / "definition.pbir").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}}, indent=2), encoding="utf-8")
    (RP / ".platform").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": NAME}, "config": {"version": "2.0", "logicalId": lt("rp")}}, indent=2), encoding="utf-8")
    (d / "version.json").write_text(json.dumps({"$schema": f"{SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}, indent=2), encoding="utf-8")

    # resources: base theme, custom theme, private custom visual
    sr = RP / "StaticResources" / "SharedResources" / "BaseThemes"
    sr.mkdir(parents=True, exist_ok=True)
    shutil.copy(BASE_THEME, sr / "CY24SU10.json")
    rr = RP / "StaticResources" / "RegisteredResources"
    rr.mkdir(parents=True, exist_ok=True)
    (rr / "EgyptPulseTheme.json").write_text(json.dumps(theme(), indent=2), encoding="utf-8")
    for r in IMAGES:
        shutil.copy(HERE / "pbip_assets" / r, rr / r)
    cv = RP / "CustomVisuals" / GUID
    if cv.exists():
        shutil.rmtree(cv)
    cv.mkdir(parents=True)
    with zipfile.ZipFile(pbiviz) as z:
        z.extractall(cv)

    report = {
        "$schema": f"{SCHEMA}/report/3.0.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": "CY24SU10", "reportVersionAtImport": {"visual": "1.8.95", "report": "2.0.95", "page": "1.3.95"}, "type": "SharedResources"},
            "customTheme": {"name": "EgyptPulseTheme.json", "reportVersionAtImport": {"visual": "2.4.0", "report": "3.0.0", "page": "2.0.0"}, "type": "RegisteredResources"},
        },
        "objects": {"outspacePane": [{"properties": {"expanded": lit(False)}}], "section": [{"properties": {"verticalAlignment": lit("Middle")}}]},
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources", "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources", "items": [{"name": "EgyptPulseTheme.json", "path": "EgyptPulseTheme.json", "type": "CustomTheme"}]
             + [{"name": r, "path": r, "type": "Image"} for r in IMAGES]},
            # private visual: one metadata item, path = bare file name under CustomVisuals/<GUID>/resources/
            {"name": GUID, "type": "CustomVisual", "items": [
                {"name": f"{GUID}.pbiviz.json", "path": f"{GUID}.pbiviz.json", "type": "CustomVisualMetadata"}]},
        ],
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized", "defaultDrillFilterOtherVisuals": True,
                     "allowChangeFilterTypes": True, "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True},
    }
    (d / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    order = []
    if (d / "pages").exists():
        shutil.rmtree(d / "pages")
    (d / "pages").mkdir(parents=True)
    for pname, display, visuals in PAGES:
        order.append(pname)
        pd_ = d / "pages" / pname
        if pd_.exists():
            shutil.rmtree(pd_)
        (pd_ / "visuals").mkdir(parents=True)
        page = {"$schema": f"{SCHEMA}/page/2.0.0/schema.json", "name": pname, "displayName": display,
                "displayOption": "FitToPage", "height": 720, "width": 1280,
                "objects": {"background": [{"properties": {"color": color("#F5F0E7"), "transparency": lit(0.0)}}],
                            "outspace": [{"properties": {"color": color("#ECE4D6"), "transparency": lit(0.0)}}]}}
        if pname in NO_FILTER:
            page["visualInteractions"] = [{"source": s, "target": t, "type": "NoFilter"} for s, t in NO_FILTER[pname]]
        if pname in PAGE_FILTERS:
            e, p, v = PAGE_FILTERS[pname]
            page["filterConfig"] = {"filters": [{
                "name": f"{pname}PageFilter", "field": col(e, p), "type": "Categorical",
                "filter": {"Version": 2, "From": [{"Name": "b", "Entity": e, "Type": 0}],
                           "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "b"}}, "Property": p}}],
                                                           "Values": [[lit(v)["expr"]]]}}}]},
                "howCreated": "User"}]}
        (pd_ / "page.json").write_text(json.dumps(page, indent=2, ensure_ascii=False), encoding="utf-8")
        for v in visuals:
            vd = pd_ / "visuals" / v["name"]
            vd.mkdir()
            (vd / "visual.json").write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")
    bm = d / "bookmarks"
    if bm.exists():
        shutil.rmtree(bm)
    bm.mkdir()
    types = {pn: {v["name"]: v["visual"]["visualType"] for v in vs} for pn, _, vs in PAGES}
    for name, display, pn, targets, shown in BOOKMARKS:
        vc = {}
        for vn, vt in types[pn].items():
            sv = {"visualType": vt, "objects": {}}
            if vn in targets and vn not in shown:
                sv["display"] = {"mode": "hidden"}
            vc[vn] = {"singleVisual": sv}
        (bm / f"{name}.bookmark.json").write_text(json.dumps({
            "$schema": f"{SCHEMA}/bookmark/2.1.0/schema.json", "displayName": display, "name": name,
            "options": {"targetVisualNames": targets, "suppressData": True, "applyOnlyToTargetVisuals": True, "suppressActiveSection": True},
            "explorationState": {"version": "1.0", "activeSection": pn, "sections": {pn: {"visualContainers": vc}}}}, indent=1, ensure_ascii=False), encoding="utf-8")
    (bm / "bookmarks.json").write_text(json.dumps({"$schema": f"{SCHEMA}/bookmarksMetadata/1.0.0/schema.json",
                                                   "items": [{"name": b[0]} for b in BOOKMARKS]}, indent=1), encoding="utf-8")
    (d / "pages" / "pages.json").write_text(json.dumps({"$schema": f"{SCHEMA}/pagesMetadata/1.0.0/schema.json",
                                                        "pageOrder": order, "activePageName": order[0]}, indent=2), encoding="utf-8")
    (OUT / f"{NAME}.pbip").write_text(json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}], "settings": {"enableAutoRecovery": True}}, indent=2), encoding="utf-8")
    (OUT / ".gitignore").write_text("**/.pbi/localSettings.json\n**/.pbi/cache.abf\n", encoding="utf-8")

    # layout for the local browser harness, when it is present
    if (HERE / "harness").is_dir():
        (HERE / "harness" / "layout.json").write_text(json.dumps([{"name": p, "display": dsp, "visuals": vs} for p, dsp, vs in PAGES], ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    pbiviz = Path(_ARGS[0])
    OUT.mkdir(parents=True, exist_ok=True)
    if not DATA_URL:
        shutil.copy(SRC_XLSX, XLSX)
    write_model()
    write_report(pbiviz)
    print("wrote", OUT)
