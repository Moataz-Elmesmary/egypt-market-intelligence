# Putting AI inside Power BI: the full build

This guide follows the full walkthrough video step for step (link at the top of the [README](../README.md)). The rule behind every step is that the language model may ask for data, but never fetches it itself.

## 0. Pick an approach

| # | Approach | What you need | Model | Control and audit |
|---|----------|---------------|-------|-------------------|
| 1 | Copilot in Power BI + Prep data for AI | Fabric F2+ or Premium P1+ capacity; tenant setting | Microsoft's | Low: Copilot writes the DAX |
| 2 | Fabric data agent over the semantic model | Fabric capacity | Microsoft's | Medium: instructions, examples, verified answers |
| 3 | Microsoft Power BI MCP servers (preview) | Admin enables the endpoint; Entra sign-in | Any MCP client | Medium: generated queries |
| 4 | **Custom visual + your own gateway** (this build) | A small server you run | Any (Gemini here) | High: fixed queries, guard, logs |
| 5 | **Your own MCP server** (this build) | The same server | Any agent | High: the same tools |
| 6 | SQL Server path | Read-only login, views or stored procedures, RLS | Any | High with procedures; risky as raw text-to-SQL |

Check licensing and preview status on Microsoft Learn before promising options 1–3 to a client. They change often.

## 1. Data and forecasts (`build_egypt_data.py`, `forecast_plus.py`)
- Sources: quarterly revenue from EGX filings (Juhayna, Edita, Obour Land, Domty) and Google Trends search interest. Each figure carries its source id (S1…S17).
- Models: six forecasters in plain Python with statsmodels: seasonal naive, naive + drift, Holt-Winters (ETS), Theta, SARIMA, and trend + season OLS.
- Rolling-origin backtest: refit up to a cut-off, forecast the next 4 quarters, compare with what really happened. The 3 lowest-error models are blended by inverse error.
- Honest diagnostics: MASE against a seasonal-naive guess, 80% band coverage, error by horizon, and the pound vs inflation-adjusted method.
- The inflation lens deflates by CPI to split growth into real growth and prices, with 9% / 13.9% / 20% scenarios.
- Run `python build_egypt_data.py`. It writes 18 sheets to `data/Egypt_Market_Intelligence_2026.xlsx`.

## 2. The semantic model as code (`build_pbip.py`)
- Tables, types, every DAX measure and the relationships live in one file and are written as **TMDL**.
- Pages and visuals are written as **PBIR** JSON. Popups are bookmarks that show or hide groups of visuals.
- Run `python build_pbip.py dist/EgyptPulse.pbiviz <output folder>`. The output is a `.pbip` project you can diff, review and rebuild.
- The committed [`pbip/`](../pbip) folder is built with `--data-url`, so it reads the workbook from this repo over HTTPS and opens on any machine. CI regenerates it and fails if it no longer matches the code.

## 3. The custom visual (`visual/`)
- TypeScript + D3. One visual with several modes: the portal page, the map, the forecast chart, the numbered notes and the Ask AI chat.
- `capabilities.json` declares the data roles and **one privilege**: `WebAccess` to `http://localhost:8765`. Without that line, the visual cannot call anything.
- `ai.ts` posts `{question, page, conv}` to the gateway and renders the answer with its route, the tool calls with their DAX, the guard result and the trace id.
- In the `visual` folder, `npx pbiviz package --no-stats` lints, compiles and writes the `.pbiviz` to `visual/dist`. The visual also handles high contrast, a landing page, native tooltips, localization (en-US, ar-EG) and read-only hosts.

## 4. Power BI Desktop
- Open the `.pbip`. If tables changed, press **Refresh now**.
- For a report you build by hand: Visualizations → **⋯** → **Import a visual from a file** → pick the `.pbiviz`.
- Model view shows 18 tables, 8 relationships and 78 measures.
- In DAX query view, run the exact query a tool sends. The AI's numbers are rows from queries like this one.

## 5. The AI gateway (`backend/`)
The order of a request:
1. **Scope gate** (`router.py`): refuses anything off-topic or unsafe, or any brand or metric the model doesn't hold. No AI call is made.
2. **Cache**: the same question on the same day costs 0 tokens.
3. **Instant router**: known question shapes are answered in code when confidence ≥ 0.8. They cost 0 tokens and take under 0.5 s.
4. **Gemini with 7 typed tools** (`tools.py`, `llm.py`): the model sees only the function declarations. Each tool runs a **fixed DAX query** with checked arguments against the model that Desktop has open.
5. **Guard** (`guard.py`): every figure in the answer must match a returned row, or the answer is retried or flagged.
6. **Trace log** (`store.py`, `/logs`): route, tokens, latency, and each tool call with its exact DAX.
- **Conversations**: each chat has an id. Follow-ups ("and after inflation?") go to the model with the last turns. A prompt injection is still refused mid-conversation.
- Copy `backend/.env.example` to `backend/.env`, add your key, then `cd backend` and `python app.py`. The API key stays in `backend/.env` on the server and never reaches the report.

## 6. MCP (`mcp/egypt_mcp.py`)
- The same 7 tools are exposed over stdio. `python mcp/demo_client.py` connects like any agent would and gets the same numbers as the report.

## 7. Tests
- `python backend/evals.py` checks routing; `--live` runs the full pipeline: 42 questions in English and Egyptian Arabic, including traps (foreign brands, missing metrics, prompt injection), plus 3 multi-turn conversations.

## 8. The same pattern on SQL Server
- Give the gateway a **read-only** login limited to the schemas it needs.
- Each tool calls a **view or stored procedure** with typed parameters, like the DAX tools here.
- Apply **row-level security** in SQL Server or in the semantic model.
- Text-to-SQL is possible, but never run generated SQL on production directly. Parse it, check it against an allow-list, and run it read-only with a row limit.

## What the model sees, and what it never sees
| Sees | Never sees |
|------|-----------|
| The question and the page in view | The database or the workbook |
| The last three turns of the chat | The connection or the API key |
| Seven function definitions | A whole table |
| The few rows each call returns | Other people's chats |
