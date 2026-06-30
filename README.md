# Automated Tabular Data Agent & Insight Engine

Natural-language data analysis app for CSV files. Upload a tabular dataset, ask questions in plain English, and get SQL-backed answers, charts, and anomaly detection through an agentic tool-calling loop.

## Features

- CSV upload with automatic schema discovery
- In-memory SQLite database for fast tabular querying
- Natural-language questions answered with generated SQL
- Chart generation for bar, line, pie, scatter, and histogram views
- IQR-based anomaly detection for numeric columns
- Multi-turn conversation context for follow-up questions
- Bundled sample NGO survey dataset for quick demos

## Tech Stack

| Layer | Tools |
| --- | --- |
| Frontend | React 18, Vite, CSS |
| Backend | Python, Flask, Flask-CORS |
| Data | pandas, SQLite |
| AI | Anthropic API tool calling |
| Charts | Matplotlib |

## Project Structure

```text
queryagent/
├── backend/
│   ├── app.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── components/
│   ├── package.json
│   └── vite.config.js
├── sample_data/
│   ├── generate_sample.py
│   └── survey_data.csv
├── docs/
│   └── BUILD_PLAN.md
└── start_dev.sh
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Anthropic API key

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_api_key_here
python app.py
```

The backend runs on `http://localhost:5000`.

On Windows PowerShell, set the API key with:

```powershell
$env:ANTHROPIC_API_KEY="your_api_key_here"
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173`.

## Production Build

```bash
cd frontend
npm run build
cd ../backend
python app.py
```

After building, Flask serves the compiled frontend from `frontend/dist`.

## API Overview

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/api/upload` | POST | Upload a CSV and create a session |
| `/api/query` | POST | Ask a question about the active dataset |
| `/api/sample` | GET | Load the bundled sample dataset |
| `/api/session/<session_id>` | GET | Fetch session metadata |
| `/api/session/<session_id>/reset` | POST | Clear chat history for a session |

## Agent Tools

The backend exposes three local tools to the model:

- `run_sql_query`: executes read-only SQL `SELECT` statements against the uploaded dataset.
- `generate_chart`: runs a SQL query and renders a Matplotlib chart as a PNG.
- `detect_anomalies`: finds outliers in numeric columns using the IQR method.

SQL execution is guarded so generated queries are limited to single-statement, read-only `SELECT` queries.

## Sample Questions

Try these with the bundled sample dataset:

- Which region has the highest dropout rate?
- Show me a bar chart of survey status breakdown.
- What is the average satisfaction score by region?
- Are there anomalies in monthly income?
- Show survey completions by month as a line chart.

## Sample Data

The project includes `sample_data/survey_data.csv`, a synthetic NGO field survey dataset with 300 rows. Regenerate it with:

```bash
python sample_data/generate_sample.py
```

## Notes

- Do not commit `node_modules`, `.env`, build output, or local Python caches.
- Keep `frontend/package-lock.json` committed so installs are reproducible.
- Uploaded CSV files are converted to temporary SQLite databases at runtime.
