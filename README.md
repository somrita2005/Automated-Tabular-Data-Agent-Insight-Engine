# QueryAgent — Natural-Language Data Analysis Agent

> Upload a CSV. Ask anything in plain English. Get answers and charts.

**Built by Somrita Majumdar** — B.Tech CSE, SRM IST · Data Analyst Intern @ Development Alternatives

---

## What It Does

QueryAgent is a full-stack AI agent that lets anyone — no SQL required — have a conversation with their data.

You upload a CSV. The agent:
1. Loads it into an in-memory SQLite database
2. Understands the schema automatically
3. Translates your plain-English questions into SQL, executes them, and interprets the results
4. Generates charts on demand (bar, line, pie, scatter, histogram)
5. Detects statistical anomalies/outliers in numeric columns
6. Remembers conversation context so follow-up questions work naturally

---

## Demo

**Sample questions that work out of the box (with the included NGO survey dataset):**

| Question | What happens |
|---|---|
| "Which region had the highest dropout rate?" | Runs a GROUP BY query, calculates dropout %, returns ranked answer |
| "Show me a bar chart of survey status breakdown" | Runs query + generates dark-themed chart image |
| "What's the average satisfaction score by region?" | Aggregation query + natural-language interpretation |
| "Are there anomalies in monthly income?" | IQR-based outlier detection, returns flagged rows |
| "Show me survey completions by month as a line chart" | Date parsing + trend line chart |
| "How many surveys does each field worker have?" | GROUP BY surveyor with count |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    React Frontend                    │
│  UploadPanel → ChatPanel → SchemaPanel               │
│  (Vite + Space Grotesk + dark data-tool aesthetic)   │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP (REST)
┌──────────────────────▼──────────────────────────────┐
│                  Flask Backend                       │
│  /api/upload  →  parse CSV → SQLite                  │
│  /api/query   →  Agent Loop                          │
│  /api/sample  →  load bundled dataset                │
└──────────────────────┬──────────────────────────────┘
                       │ Anthropic API
┌──────────────────────▼──────────────────────────────┐
│              Claude claude-sonnet-4-6 (Tool-Calling)            │
│                                                      │
│  Tool: run_sql_query    → sqlite3 execution          │
│  Tool: generate_chart   → matplotlib PNG             │
│  Tool: detect_anomalies → IQR outlier detection      │
└─────────────────────────────────────────────────────┘
```

### Agent Loop (backend/app.py)

The agent uses a `while stop_reason != "end_turn"` loop:
1. Send user message + conversation history to Claude with tool definitions
2. If Claude calls a tool → execute it locally → send `tool_result` back
3. Claude may call multiple tools in sequence (e.g. run_sql_query then generate_chart)
4. When Claude stops calling tools, collect its final text response
5. Return text + charts + tool call log to the frontend

This is **real tool-calling / function-calling** — not prompt chaining. Claude decides which tools to call and in what order.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, CSS (no component library) |
| Backend | Python 3.11+, Flask 3, Flask-CORS |
| AI | Anthropic API (`claude-sonnet-4-6`) with tool use |
| Data layer | SQLite (via pandas + sqlite3) |
| Charts | Matplotlib (headless, Agg backend) |
| Deployment | Any Linux/Mac with Python + Node |

---

## Project Structure

```
queryagent/
├── backend/
│   ├── app.py              # Flask app + agent loop + tools
│   └── requirements.txt    # Python deps
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Root — session state + routing
│   │   ├── index.css       # All styles (design tokens + components)
│   │   └── components/
│   │       ├── UploadPanel.jsx   # Drag-drop upload + sample loader
│   │       ├── ChatPanel.jsx     # Messages + chart rendering + input
│   │       └── SchemaPanel.jsx   # Collapsible column / schema sidebar
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── sample_data/
│   ├── generate_sample.py  # Script to regenerate sample CSV
│   └── survey_data.csv     # 300-row NGO survey dataset (bundled)
└── README.md
```

---

## Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+
- An Anthropic API key

### 1. Backend

```bash
cd backend
pip install -r requirements.txt

export ANTHROPIC_API_KEY=sk-ant-...   # or set in .env

python app.py
# → Flask running on http://localhost:5000
```

### 2. Frontend (development)

```bash
cd frontend
npm install
npm run dev
# → Vite running on http://localhost:5173
```

### 3. Frontend (production build)

```bash
cd frontend
npm run build
# → dist/ folder is served automatically by Flask at /
```

---

## How the Agent Tools Work

### `run_sql_query`
```python
# Claude sends:
{ "query": "SELECT region, COUNT(*) as count FROM data WHERE survey_status='Dropout' GROUP BY region ORDER BY count DESC", "label": "Dropout count by region" }

# Tool executes it on the SQLite DB, returns:
{ "ok": true, "rows": 5, "data": [...] }
```

### `generate_chart`
```python
# Claude sends:
{ "query": "SELECT region, ...", "chart_type": "bar", "x_col": "region", "y_col": "dropout_rate", "title": "Dropout Rate by Region" }

# Tool runs the query, generates a dark-themed matplotlib PNG, returns base64
{ "ok": true, "image_base64": "iVBOR..." }
```

### `detect_anomalies`
```python
# Claude sends:
{ "column": "monthly_income_inr", "context_columns": ["region", "survey_id"] }

# Tool computes Q1/Q3/IQR, returns rows outside [Q1-1.5*IQR, Q3+1.5*IQR]
{ "ok": true, "anomaly_count": 12, "bounds": {...}, "anomalies": [...] }
```

---

## Connecting to Your Own Data

Replace the SQLite layer with any database:

```python
# In backend/app.py, swap sqlite3 for:
import mysql.connector  # MySQL
import psycopg2         # PostgreSQL

# Update tool_run_sql_query() to use your connector
```

The agent loop and tool definitions remain identical.

---

## Resume Talking Points

**In interviews, demo live:**
1. Open the app, drag in a CSV (or click "Try sample dataset")
2. Ask: *"Which region had the highest dropout?"* — watch it write SQL in real time
3. Ask: *"Show me that as a bar chart"* — chart appears in the same conversation
4. Ask: *"Are there anomalies in household income?"* — demonstrates the third tool
5. Point out the "tool calls" accordion — shows the actual SQL it wrote

**Key points to articulate:**
- **Real tool-calling**, not prompt chaining — Claude decides which tools to invoke and when
- **Multi-turn context** — follow-up questions work without re-explaining the dataset
- **Three distinct tools** = demonstrates tool orchestration (the core skill in the Microsoft AI Agent cert)
- **End-to-end ownership**: data layer (SQLite), agent logic (Python), API (Flask), UI (React), charts (matplotlib)

---

## Planned Enhancements (Week 3)

- [ ] Trend forecasting tool (linear regression on time series)
- [ ] Export conversation as PDF report
- [ ] Connect to MySQL instead of SQLite (reuse electricity bill project schema)
- [ ] Multi-file support (join two CSVs)
- [ ] Deploy to Render/Railway (free tier)

---

## Sample Dataset

`sample_data/survey_data.csv` — 300 synthetic NGO field survey records modelled on Somrita's internship work at Development Alternatives:

| Column | Type | Description |
|---|---|---|
| survey_id | TEXT | Unique ID (SRV0001–SRV0300) |
| survey_date | DATE | Date of survey |
| region | TEXT | Delhi, Ghaziabad, Noida, Faridabad, Gurugram |
| surveyor | TEXT | Field worker name |
| household_size | INT | Number of people in household |
| monthly_income_inr | INT | Household income (₹) |
| primary_water_source | TEXT | Tap, Borewell, Hand Pump, River, Tanker |
| sanitation_type | TEXT | Flush Toilet, Pit Latrine, etc. |
| distance_to_water_km | FLOAT | Distance to nearest water source |
| satisfaction_score | INT | 1–5 rating |
| survey_status | TEXT | Complete, Partial, Dropout |
| toilet_access | TEXT | Yes/No |
| handwash_facility | TEXT | Yes/No |

Regenerate with: `python sample_data/generate_sample.py`

---

*Built to demonstrate real agentic AI — SQL execution + chart generation + anomaly detection as LLM-callable tools, orchestrated by Claude claude-sonnet-4-6.*
