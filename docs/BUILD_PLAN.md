# QueryAgent — 3-Week Build Plan

## Week 1: Data Layer + Agent Core (Days 1–7)

**Goal:** Working agent loop in the terminal. No UI yet.

### Day 1–2: Project scaffold + data layer
- [ ] Create project structure (done — see README)
- [ ] Install Python deps: `pip install -r backend/requirements.txt`
- [ ] Generate sample dataset: `python sample_data/generate_sample.py`
- [ ] Test CSV → SQLite pipeline manually
- [ ] Verify `get_schema()` output looks right

**Checkpoint:** `python -c "import pandas, matplotlib, anthropic, flask; print('all good')`

### Day 3–4: Tool functions
- [ ] Test `tool_run_sql_query()` standalone with a hardcoded query
- [ ] Test `tool_generate_chart()` — does it produce a valid PNG?
- [ ] Test `tool_detect_anomalies()` — verify IQR logic on sample data
- [ ] Print tool outputs to confirm correctness

**Checkpoint:** All three tools produce correct output in isolation.

### Day 5–7: Agent loop
- [ ] Wire up `run_agent()` in `backend/app.py`
- [ ] Test from terminal (comment out Flask routes, call `run_agent()` directly)
- [ ] Ask: "Which region has the most dropouts?" — does Claude write correct SQL?
- [ ] Ask: "Show me a bar chart" — does it call generate_chart?
- [ ] Verify multi-tool orchestration (SQL then chart in one response)
- [ ] Fix any SQL errors (common: wrong column names, wrong table name)

**Checkpoint:** Terminal demo works end-to-end for 5 different questions.

---

## Week 2: Flask API + React UI (Days 8–14)

**Goal:** Full working web app. Polish the experience.

### Day 8–9: Flask API
- [ ] Run `python backend/app.py` — Flask starts on port 5000
- [ ] Test `/api/sample` with curl: `curl http://localhost:5000/api/sample`
- [ ] Test `/api/upload` with a CSV file
- [ ] Test `/api/query` with a session_id from upload
- [ ] Verify conversation history persists across queries

**Checkpoint:** All 4 API routes work via curl/Postman.

### Day 10–11: React frontend
- [ ] `cd frontend && npm install && npm run dev`
- [ ] Upload panel: drag-drop + "Try sample" button
- [ ] Chat panel: messages render, user/agent bubbles styled correctly
- [ ] Schema panel: columns and schema show correctly
- [ ] Charts render from base64 (check browser console for errors)
- [ ] Tool call accordion expands/collapses

**Checkpoint:** Full flow works in browser — upload → ask → see chart.

### Day 12–13: Polish & error handling
- [ ] Test bad/malformed CSV — does the error message show clearly?
- [ ] Test ambiguous question — does Claude handle it gracefully?
- [ ] Test very large result set — does the app stay responsive?
- [ ] Mobile responsiveness (schema panel hides on small screens)
- [ ] Loading states work (typing indicator while agent runs)
- [ ] "Clear chat" and "New file" buttons work

### Day 14: Integration test
- [ ] Run the full demo flow 3 times end-to-end
- [ ] Fix any bugs found
- [ ] Build the frontend: `npm run build` (Flask serves the dist/)
- [ ] Test production build at http://localhost:5000

---

## Week 3: Enhancements + Polish + Demo Prep (Days 15–21)

**Goal:** Add one more tool, prep for interviews.

### Day 15–16: Trend forecasting tool (optional)
Add a 4th tool to `backend/app.py`:

```python
{
    "name": "forecast_trend",
    "description": "Forecast a numeric metric over time using linear regression",
    "input_schema": {
        "type": "object",
        "properties": {
            "date_column": {"type": "string"},
            "value_column": {"type": "string"},
            "periods_ahead": {"type": "integer"}
        },
        "required": ["date_column", "value_column"]
    }
}
```

Implement with `numpy.polyfit()` — no extra deps needed.

### Day 17–18: MySQL integration (optional)
Connect to your Electricity Bill Management System MySQL database:

```python
# In app.py, add:
import mysql.connector

def connect_mysql(host, user, password, database):
    return mysql.connector.connect(host=host, user=user, password=password, database=database)
```

Add a `/api/connect-db` route that accepts connection string. Now you can demo with real production data from your existing project.

### Day 19: README + demo GIF
- [ ] Write clear README (done — edit as needed)
- [ ] Record a demo GIF with [Kap](https://getkap.co) (Mac) or ShareX (Windows)
  - Show: upload CSV → ask question → SQL executes → chart appears
  - Keep it under 30 seconds
- [ ] Add GIF to README: `![Demo](demo.gif)`
- [ ] Push to GitHub: `git push origin main`

### Day 20–21: Deploy (optional but impressive)
**Render (free tier):**
1. Push to GitHub
2. Create new Web Service on render.com
3. Build command: `cd frontend && npm install && npm run build`
4. Start command: `cd backend && python app.py`
5. Add env var: `ANTHROPIC_API_KEY=sk-ant-...`

**Or Railway:**
Similar — Railway auto-detects Python + sets up the service.

---

## Interview Demo Script (60 seconds)

1. **Open browser** → "This is QueryAgent — an AI agent that lets you talk to your data in plain English"
2. **Click "Try sample dataset"** → schema loads in sidebar
3. **Type:** "Which region had the highest dropout rate?" → *SQL runs, answer appears*
4. **Type:** "Show me that as a bar chart" → *chart appears in same conversation*
5. **Click tool calls accordion** → "Here's the actual SQL it wrote and executed — it's not faking anything"
6. **Type:** "Are there any anomalies in household income?" → *anomaly detection runs*
7. **Summary:** "Three tools — SQL execution, chart generation, anomaly detection — all called by the model itself. This validates exactly what the Microsoft AI Agent cert covers: real tool orchestration, not just prompting."

---

## Debugging Common Issues

| Issue | Fix |
|---|---|
| `anthropic.APIError` | Check `ANTHROPIC_API_KEY` env var is set |
| `no such column: X` | Claude hallucinated a column — add column list to system prompt |
| Chart is blank/white | Check matplotlib Agg backend is set before import |
| CORS error in browser | Ensure `flask-cors` is installed and `CORS(app)` is called |
| Session expired | Session is in-memory; restart Flask to clear all sessions |
| CSV parse error | Check CSV encoding (try `encoding='latin-1'` in pd.read_csv) |

---

## Extending for Production

- **Auth:** Add Flask-Login or JWT tokens for user accounts
- **Persistence:** Replace in-memory SESSIONS dict with Redis or PostgreSQL
- **File limit:** Add file size validation (current: unlimited)
- **Rate limiting:** Use Flask-Limiter to prevent API cost runaway
- **Multiple tables:** Allow uploading multiple CSVs, agent can JOIN them
