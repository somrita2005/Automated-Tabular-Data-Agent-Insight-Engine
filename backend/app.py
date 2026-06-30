"""
QueryAgent – Flask Backend
Natural-language data query agent with tool-calling loop.
"""

import os
import json
import re
import sqlite3
import tempfile
import traceback
import base64
import io
import uuid
from pathlib import Path
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import anthropic

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────
app = Flask(__name__, static_folder="../frontend/dist", static_url_path="/")
CORS(app)

# Enforce the upload limit the UI already advertises ("Up to ~50MB").
# Without this, Flask happily buffers an arbitrarily large file into memory.
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB


@app.errorhandler(413)
def too_large(_e):
    return jsonify({"error": "File too large. Maximum upload size is 50MB."}), 413

UPLOAD_DIR = Path(tempfile.gettempdir()) / "queryagent_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env var

# In-memory session store: session_id → {db_path, df_summary, conversation}
SESSIONS: dict[str, dict] = {}

# ─────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────

def df_to_sqlite(df: pd.DataFrame, db_path: str, table_name: str = "data") -> None:
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()


# ─────────────────────────────────────────────
# SQL safety
# ─────────────────────────────────────────────
# The model writes its own SQL, so this boundary — not the system prompt —
# is what actually stops a destructive or multi-statement query from running.
_FORBIDDEN_KEYWORDS = (
    "drop ", "delete ", "update ", "insert ", "alter ",
    "attach ", "detach ", "pragma ", "create ", "replace ",
)


def ensure_select_only(query: str) -> str:
    """Raises ValueError unless `query` is a single, read-only SELECT statement."""
    q = query.strip()
    if q.endswith(";"):
        q = q[:-1].strip()
    if ";" in q:
        raise ValueError("Multiple SQL statements are not allowed.")
    if not re.match(r"(?is)^\s*select\b", q):
        raise ValueError("Only SELECT queries are allowed.")
    lowered = q.lower()
    for kw in _FORBIDDEN_KEYWORDS:
        if kw in lowered:
            raise ValueError(f"Query contains disallowed keyword: '{kw.strip()}'.")
    return q


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def ensure_valid_column(db_path: str, column: str, table_name: str = "data") -> str:
    """Raises ValueError unless `column` is a real column on the table.

    Guards detect_anomalies, which builds SQL via an f-string rather than
    parameter binding (sqlite3 has no placeholder syntax for identifiers).
    """
    if not _IDENTIFIER_RE.match(column):
        raise ValueError(f"Invalid column name: '{column}'.")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    valid = {row[1] for row in cursor.fetchall()}
    conn.close()
    if column not in valid:
        raise ValueError(f"Unknown column: '{column}'.")
    return column


def get_schema(db_path: str, table_name: str = "data") -> str:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = cursor.fetchall()
    conn.close()
    lines = [f"  {c[1]} ({c[2]})" for c in cols]
    return f"Table '{table_name}':\n" + "\n".join(lines)


def df_summary(df: pd.DataFrame) -> str:
    lines = [
        f"Rows: {len(df):,}  |  Columns: {len(df.columns)}",
        f"Columns: {', '.join(df.columns.tolist())}",
        "",
        "Sample (first 3 rows):",
        df.head(3).to_string(index=False),
    ]
    return "\n".join(lines)


def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


# ─────────────────────────────────────────────
# Agent Tools  (run_sql_query, generate_chart, detect_anomalies)
# ─────────────────────────────────────────────

TOOLS = [
    {
        "name": "run_sql_query",
        "description": (
            "Execute a SQL SELECT query on the uploaded dataset (SQLite). "
            "Always use the table name 'data'. "
            "Returns up to 200 rows as JSON. "
            "Use this to answer questions about counts, sums, averages, comparisons, or filtering."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The SQL SELECT query to run"},
                "label": {"type": "string", "description": "Short human-readable label for what this query computes"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "generate_chart",
        "description": (
            "Generate a chart (bar, line, pie, scatter, histogram) from a SQL query result. "
            "First run run_sql_query to get the data, then call this tool with the query and chart config. "
            "Returns a base64 PNG image."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL SELECT query whose results will be charted"},
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter", "histogram"],
                    "description": "Type of chart to generate",
                },
                "x_col": {"type": "string", "description": "Column name for X axis (or labels for pie)"},
                "y_col": {"type": "string", "description": "Column name for Y axis (or values for pie)"},
                "title": {"type": "string", "description": "Chart title"},
                "color": {"type": "string", "description": "Hex color for bars/line, e.g. '#4F81C7'"},
            },
            "required": ["query", "chart_type", "title"],
        },
    },
    {
        "name": "detect_anomalies",
        "description": (
            "Detect outliers/anomalies in a numeric column using IQR method. "
            "Returns rows that are statistical outliers, plus a summary. "
            "Useful for questions like 'are there any unusual values in X?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "column": {"type": "string", "description": "Numeric column name to analyse"},
                "context_columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Extra columns to include in the anomaly output for context",
                },
            },
            "required": ["column"],
        },
    },
]


def tool_run_sql_query(db_path: str, query: str, label: str = "") -> dict:
    try:
        safe_query = ensure_select_only(query)
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(safe_query, conn)
        conn.close()
        records = df.head(200).to_dict(orient="records")
        return {
            "ok": True,
            "label": label or query[:60],
            "rows": len(df),
            "columns": df.columns.tolist(),
            "data": records,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_generate_chart(db_path: str, query: str, chart_type: str, title: str,
                         x_col: str = None, y_col: str = None, color: str = "#4F81C7") -> dict:
    try:
        safe_query = ensure_select_only(query)
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(safe_query, conn)
        conn.close()

        if df.empty:
            return {"ok": False, "error": "Query returned no data"}

        # Auto-detect columns if not specified
        if not x_col and len(df.columns) >= 1:
            x_col = df.columns[0]
        if not y_col and len(df.columns) >= 2:
            y_col = df.columns[1]

        fig, ax = plt.subplots(figsize=(9, 5))
        fig.patch.set_facecolor("#0F1117")
        ax.set_facecolor("#181926")
        ax.tick_params(colors="#C0C8E0")
        ax.xaxis.label.set_color("#C0C8E0")
        ax.yaxis.label.set_color("#C0C8E0")
        ax.title.set_color("#FFFFFF")
        for spine in ax.spines.values():
            spine.set_edgecolor("#2A2D3E")

        accent = color or "#4F81C7"

        if chart_type == "bar":
            bars = ax.bar(df[x_col].astype(str), df[y_col], color=accent, edgecolor="#0F1117", linewidth=0.5)
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            plt.xticks(rotation=30, ha="right")
            # Value labels
            for bar in bars:
                h = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, h + h * 0.01,
                        f"{h:,.0f}", ha="center", va="bottom", fontsize=8, color="#C0C8E0")

        elif chart_type == "line":
            ax.plot(df[x_col].astype(str), df[y_col], color=accent,
                    marker="o", markersize=5, linewidth=2)
            ax.fill_between(range(len(df)), df[y_col], alpha=0.15, color=accent)
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            plt.xticks(rotation=30, ha="right", ticks=range(len(df)), labels=df[x_col].astype(str))

        elif chart_type == "pie":
            wedge_colors = ["#4F81C7", "#E07B4F", "#6AC174", "#C96DD8", "#E0C34F"]
            ax.pie(df[y_col], labels=df[x_col].astype(str),
                   autopct="%1.1f%%", colors=wedge_colors[:len(df)],
                   textprops={"color": "#C0C8E0"}, startangle=90)

        elif chart_type == "scatter":
            ax.scatter(df[x_col], df[y_col], color=accent, alpha=0.7, edgecolors="#0F1117", linewidth=0.4)
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)

        elif chart_type == "histogram":
            col = y_col or x_col
            ax.hist(df[col].dropna(), bins=20, color=accent, edgecolor="#0F1117")
            ax.set_xlabel(col)
            ax.set_ylabel("Frequency")

        ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
        plt.tight_layout()

        img_b64 = fig_to_base64(fig)
        return {"ok": True, "image_base64": img_b64, "chart_type": chart_type, "title": title}

    except Exception as e:
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}


def tool_detect_anomalies(db_path: str, column: str, context_columns: list = None) -> dict:
    try:
        context_columns = context_columns or []
        safe_column = ensure_valid_column(db_path, column)
        safe_context = [ensure_valid_column(db_path, c) for c in context_columns]

        conn = sqlite3.connect(db_path)
        select_cols = ", ".join([safe_column] + safe_context)
        df = pd.read_sql_query(f"SELECT {select_cols} FROM data", conn)
        conn.close()

        series = pd.to_numeric(df[safe_column], errors="coerce").dropna()
        Q1, Q3 = series.quantile(0.25), series.quantile(0.75)
        IQR = Q3 - Q1
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR

        mask = (pd.to_numeric(df[safe_column], errors="coerce") < lower) | \
               (pd.to_numeric(df[safe_column], errors="coerce") > upper)
        anomalies = df[mask].head(50)

        return {
            "ok": True,
            "column": safe_column,
            "total_rows": len(df),
            "anomaly_count": int(mask.sum()),
            "bounds": {"lower": round(lower, 2), "upper": round(upper, 2)},
            "Q1": round(Q1, 2), "Q3": round(Q3, 2), "IQR": round(IQR, 2),
            "anomalies": anomalies.to_dict(orient="records"),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def dispatch_tool(tool_name: str, tool_input: dict, db_path: str) -> dict:
    if tool_name == "run_sql_query":
        return tool_run_sql_query(db_path, tool_input["query"], tool_input.get("label", ""))
    elif tool_name == "generate_chart":
        return tool_generate_chart(
            db_path,
            tool_input["query"],
            tool_input["chart_type"],
            tool_input["title"],
            tool_input.get("x_col"),
            tool_input.get("y_col"),
            tool_input.get("color", "#4F81C7"),
        )
    elif tool_name == "detect_anomalies":
        return tool_detect_anomalies(db_path, tool_input["column"], tool_input.get("context_columns", []))
    return {"ok": False, "error": f"Unknown tool: {tool_name}"}


# ─────────────────────────────────────────────
# Agent Loop
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are QueryAgent, an expert data analyst AI assistant. The user has uploaded a dataset that has been loaded into a SQLite database with a single table called 'data'.

Your job is to answer the user's questions about their data by:
1. Writing and executing precise SQL queries using the run_sql_query tool
2. Generating insightful charts using the generate_chart tool when visualisation helps
3. Detecting anomalies when asked using the detect_anomalies tool

Guidelines:
- Always run_sql_query first to understand what data exists before generating charts
- For trend questions, use line charts; for comparisons, use bar charts; for proportions, use pie charts
- When the user asks "show me" or "visualize", always generate a chart
- Provide concise, insightful natural-language interpretations of your findings — act like a data analyst presenting to stakeholders
- If a query fails, fix it and try again
- Use column names exactly as they appear in the schema
- Never make up data; always base answers on actual query results
- Format numbers clearly (e.g., "2,450 records" not "2450")

{schema}
{summary}
"""


def run_agent(session: dict, user_message: str) -> dict:
    """Run the agentic loop and return the final response."""
    db_path = session["db_path"]
    schema = session["schema"]
    summary = session["summary"]

    system = SYSTEM_PROMPT.format(schema=schema, summary=summary)

    # Build messages: prior conversation + new user message
    messages = list(session["conversation"])
    messages.append({"role": "user", "content": user_message})

    tool_calls_log = []
    charts = []
    final_text = ""

    MAX_ITERATIONS = 8
    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        # Collect text content
        text_blocks = [b.text for b in response.content if b.type == "text"]
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if text_blocks:
            final_text = "\n".join(text_blocks)

        if response.stop_reason == "end_turn" or not tool_use_blocks:
            break

        # Append assistant turn
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool call
        tool_results = []
        for tu in tool_use_blocks:
            result = dispatch_tool(tu.name, tu.input, db_path)
            tool_calls_log.append({
                "tool": tu.name,
                "input": tu.input,
                "ok": result.get("ok", False),
            })

            # Extract chart if present
            if tu.name == "generate_chart" and result.get("ok") and result.get("image_base64"):
                charts.append({
                    "title": tu.input.get("title", "Chart"),
                    "image_base64": result["image_base64"],
                })
                # Don't pass huge base64 back into the model context
                result_for_model = {k: v for k, v in result.items() if k != "image_base64"}
                result_for_model["image_generated"] = True
            else:
                result_for_model = result

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(result_for_model),
            })

        messages.append({"role": "user", "content": tool_results})

    # Save updated conversation (trim to last 20 turns to avoid bloat)
    session["conversation"] = messages[-20:]

    return {
        "text": final_text,
        "charts": charts,
        "tool_calls": tool_calls_log,
    }


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Accept a CSV upload, create SQLite DB, return session_id + schema."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    if not f.filename.lower().endswith(".csv"):
        return jsonify({"error": "Only CSV files are supported"}), 400

    session_id = str(uuid.uuid4())
    db_path = str(UPLOAD_DIR / f"{session_id}.db")

    try:
        df = pd.read_csv(f)
        df_to_sqlite(df, db_path)
        schema = get_schema(db_path)
        summary = df_summary(df)

        SESSIONS[session_id] = {
            "db_path": db_path,
            "schema": schema,
            "summary": summary,
            "conversation": [],
            "filename": f.filename,
            "uploaded_at": datetime.utcnow().isoformat(),
        }

        return jsonify({
            "session_id": session_id,
            "filename": f.filename,
            "rows": len(df),
            "columns": df.columns.tolist(),
            "schema": schema,
            "preview": df.head(5).to_dict(orient="records"),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/query", methods=["POST"])
def query():
    """Send a natural-language question to the agent."""
    body = request.get_json()
    session_id = body.get("session_id")
    message = body.get("message", "").strip()

    if not session_id or session_id not in SESSIONS:
        return jsonify({"error": "Invalid or expired session. Please re-upload your file."}), 400
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    try:
        result = run_agent(SESSIONS[session_id], message)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/session/<session_id>", methods=["GET"])
def get_session(session_id):
    sess = SESSIONS.get(session_id)
    if not sess:
        return jsonify({"error": "Session not found"}), 404
    return jsonify({
        "session_id": session_id,
        "filename": sess["filename"],
        "schema": sess["schema"],
        "turns": len(sess["conversation"]) // 2,
    })


@app.route("/api/session/<session_id>/reset", methods=["POST"])
def reset_session(session_id):
    """Clear conversation history but keep the dataset."""
    if session_id in SESSIONS:
        SESSIONS[session_id]["conversation"] = []
    return jsonify({"ok": True})


@app.route("/api/sample", methods=["GET"])
def get_sample():
    """Load the bundled sample dataset and return a session."""
    sample_path = Path(__file__).parent.parent / "sample_data" / "survey_data.csv"
    if not sample_path.exists():
        return jsonify({"error": "Sample data not found"}), 404

    session_id = "sample-" + str(uuid.uuid4())[:8]
    db_path = str(UPLOAD_DIR / f"{session_id}.db")

    df = pd.read_csv(sample_path)
    df_to_sqlite(df, db_path)

    SESSIONS[session_id] = {
        "db_path": db_path,
        "schema": get_schema(db_path),
        "summary": df_summary(df),
        "conversation": [],
        "filename": "survey_data.csv (sample)",
        "uploaded_at": datetime.utcnow().isoformat(),
    }

    return jsonify({
        "session_id": session_id,
        "filename": "survey_data.csv (sample)",
        "rows": len(df),
        "columns": df.columns.tolist(),
        "schema": get_schema(db_path),
        "preview": df.head(5).to_dict(orient="records"),
    })


# Serve React frontend
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path and (Path(app.static_folder) / path).exists():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
