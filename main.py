import os
import json
import sqlite3
import re
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from backend.visualization import build_plotly_figure, figure_to_json

load_dotenv()

app = FastAPI(title="SQL AI Analyst")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB ──────────────────────────────────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent / "data" / "analytics.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_schema() -> str:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    schema_parts = []
    for t in tables:
        cur.execute(f"PRAGMA table_info({t})")
        cols = cur.fetchall()
        col_defs = ", ".join(f"{c[1]} {c[2]}" for c in cols)
        schema_parts.append(f"Table {t}: ({col_defs})")
    conn.close()
    return "\n".join(schema_parts)

# ── LangChain chains ────────────────────────────────────────────────────────
api_key = os.environ.get("ANTHROPIC_API_KEY")

if api_key:
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

    SQL_SYSTEM = """You are an expert SQL analyst. Given a SQLite database schema and a natural language question, generate a single valid SQLite SQL query.

Rules:
- Return ONLY the raw SQL query — no markdown fences, no explanation, no extra text.
- Use proper SQLite syntax (strftime, CAST, etc.).
- For date grouping, prefer strftime('%Y-%m', date_col).
- Never use DROP, DELETE, UPDATE, INSERT, or any DDL/DML statement.
- If the question cannot be answered from the schema, return: SELECT 'Unable to answer' AS message;

Schema:
{schema}"""

    sql_chain = (
        ChatPromptTemplate.from_messages([
            ("system", SQL_SYSTEM),
            ("human", "Question: {question}\n\nConversation history:\n{history}")
        ])
        | llm
        | StrOutputParser()
    )

    INSIGHT_SYSTEM = """You are a sharp data analyst. Given a SQL query and its result data, provide:
1. A clear 2-3 sentence insight about what the data shows.
2. One actionable recommendation.
3. One interesting pattern or anomaly to watch.

Be specific, reference actual numbers from the data. Keep it concise and business-focused."""

    insight_chain = (
        ChatPromptTemplate.from_messages([
            ("system", INSIGHT_SYSTEM),
            ("human", "SQL Query: {query}\n\nData (first 20 rows): {data}\n\nOriginal question: {question}")
        ])
        | llm
        | StrOutputParser()
    )

    CHART_SYSTEM = """You are a data visualization expert. Given a SQL result and the question, decide the best chart type and config.

Return ONLY valid JSON like:
{{
  "type": "bar"|"line"|"pie"|"scatter"|"table",
  "x_col": "column_name",
  "y_col": "column_name",
  "title": "Chart title",
  "color": "#6366f1"
}}

Rules:
- Use "table" if data has more than 4 columns or is non-aggregated.
- Use "pie" only if rows <= 8 and data shows proportions.
- Use "line" for time-series data.
- Use "bar" for comparisons.
- x_col and y_col must be actual column names from the data."""

    chart_chain = (
        ChatPromptTemplate.from_messages([
            ("system", CHART_SYSTEM),
            ("human", "Question: {question}\nColumns: {columns}\nSample data (3 rows): {sample}")
        ])
        | llm
        | StrOutputParser()
    )
else:
    llm = None
    sql_chain = None
    insight_chain = None
    chart_chain = None


def get_demo_response(question: str):
    q = question.lower().strip()
    
    # 1. Raw SQL detection
    if q.startswith("select ") or q.startswith("with "):
        if not validate_sql(question):
            return None, None, "Demo Mode: Query contains forbidden operations."
        return question, {"type": "table"}, "Executed raw SQL query in Demo Mode."
            
    # 2. Pre-baked questions
    # a. Top 5 products
    if "top 5 products" in q or ("top" in q and "products" in q and "revenue" in q):
        sql = """SELECT p.name, SUM(s.revenue) AS total_revenue
FROM sales s
JOIN products p ON s.product_id = p.product_id
WHERE s.sale_date BETWEEN '2023-01-01' AND '2023-12-31'
GROUP BY p.name
ORDER BY total_revenue DESC
LIMIT 5;"""
        chart = {
            "type": "bar",
            "x_col": "name",
            "y_col": "total_revenue",
            "title": "Top 5 Products by Revenue (2023)"
        }
        insight = "Wireless Headphones was the top product generating the highest revenue, followed by Winter Jacket and Running Shoes. Recommendation: Focus marketing spend on these categories to sustain high sales volume. Anomaly: Books (Python Cookbook, Data Science Handbook) showed lower revenue compared to electronics."
        return sql, chart, insight

    # b. Monthly sales trend
    if "monthly sales trend" in q or "sales trend" in q or ("monthly" in q and "sales" in q):
        sql = """SELECT strftime('%Y-%m', sale_date) AS month, SUM(revenue) AS total_sales
FROM sales
WHERE sale_date BETWEEN '2024-01-01' AND '2024-12-31'
GROUP BY month
ORDER BY month;"""
        chart = {
            "type": "line",
            "x_col": "month",
            "y_col": "total_sales",
            "title": "Monthly Sales Trend (2024)"
        }
        insight = "Monthly sales for 2024 show steady growth, peaking in November and December due to holiday campaigns. Recommendation: Increase inventory levels in early Q4 to meet the holiday sales surge. Anomaly: A sharp drop in sales was observed in February, which is typical for post-holiday periods."
        return sql, chart, insight

    # c. Region average order value
    if "region" in q and ("average order" in q or "aov" in q or "highest average" in q):
        sql = """SELECT c.region, AVG(s.revenue) AS avg_order_value
FROM sales s
JOIN customers c ON s.customer_id = c.customer_id
GROUP BY c.region
ORDER BY avg_order_value DESC;"""
        chart = {
            "type": "bar",
            "x_col": "region",
            "y_col": "avg_order_value",
            "title": "Average Order Value by Region"
        }
        insight = "The East region leads with the highest average order value, closely followed by the West region. Recommendation: Target high-value customer acquisitions in the East and West regions through regional promotions. Anomaly: The Central region shows the lowest average order value despite having a similar customer count."
        return sql, chart, insight

    # d. Revenue by sales channel
    if "channel" in q or "sales channel" in q:
        sql = """SELECT channel, SUM(revenue) AS total_revenue
FROM sales
GROUP BY channel
ORDER BY total_revenue DESC;"""
        chart = {
            "type": "pie",
            "x_col": "channel",
            "y_col": "total_revenue",
            "title": "Revenue Share by Sales Channel"
        }
        insight = "Online and Mobile App channels account for over 65% of the total revenue, with In-Store sales coming in third. Recommendation: Optimize user experience on the Mobile App to leverage its high conversion rate. Anomaly: Partner sales represent the smallest share but have the lowest operational cost."
        return sql, chart, insight

    # e. Marketing campaign ROI
    if "campaign" in q or "marketing" in q or "roi" in q:
        sql = """SELECT name, channel, spend, conversions, ROUND((conversions * 50.0) / spend, 2) AS est_roi
FROM marketing
ORDER BY est_roi DESC;"""
        chart = {
            "type": "bar",
            "x_col": "name",
            "y_col": "est_roi",
            "title": "Estimated Campaign ROI"
        }
        insight = "The 'Black Friday Blitz' campaign yielded the highest ROI of 3.2, driven by high conversion rates during the holiday week. Recommendation: Reallocate budget from underperforming spring campaigns to high-intent event-based campaigns. Anomaly: Mobile app campaigns had lower spend but comparable conversion volume to online channels."
        return sql, chart, insight

    # f. Customer segment distribution
    if "segment" in q or "customer segment" in q:
        sql = """SELECT segment, COUNT(*) AS customer_count
FROM customers
GROUP BY segment
ORDER BY customer_count DESC;"""
        chart = {
            "type": "pie",
            "x_col": "segment",
            "y_col": "customer_count",
            "title": "Customer Segment Distribution"
        }
        insight = "Regular customers make up the largest segment, while Premium customers constitute about 25% of the database. Recommendation: Design a loyalty program to transition Regular customers to the Premium tier. Anomaly: The 'At-Risk' segment is growing, indicating a need for proactive customer retention outreach."
        return sql, chart, insight

    # g. Sidebar table previews
    table_match = re.search(r"sample of the ([a-zA-Z_]+) table", q)
    if table_match:
        table_name = table_match.group(1)
        if table_name in ["sales", "products", "customers", "marketing"]:
            sql = f"SELECT * FROM {table_name} LIMIT 5;"
            chart = {"type": "table"}
            insight = f"Showing the first 5 records from the {table_name} table to inspect table columns and sample values."
            return sql, chart, insight

    # No match
    return None, None, None

# ── Models ──────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    history: Optional[list] = []

# ── Helpers ─────────────────────────────────────────────────────────────────
FORBIDDEN = re.compile(
    r'\b(DROP|DELETE|UPDATE|INSERT|CREATE|ALTER|TRUNCATE|REPLACE)\b',
    re.IGNORECASE
)

def validate_sql(sql: str) -> bool:
    """Allow only single read-only SELECT / WITH queries."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        return False
    if FORBIDDEN.search(cleaned):
        return False
    upper = cleaned.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        return False
    # Block multiple statements (basic injection guard)
    if ";" in cleaned:
        return False
    return True

def execute_sql(sql: str) -> tuple[list[dict], list[str]]:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchmany(200)
        cols = [d[0] for d in cur.description] if cur.description else []
        return [dict(zip(cols, r)) for r in rows], cols
    finally:
        conn.close()

def format_history(history: list) -> str:
    if not history:
        return "None"
    lines = []
    for h in history[-4:]:  # last 4 turns
        lines.append(f"User: {h.get('question','')}")
        lines.append(f"SQL: {h.get('sql','')}")
    return "\n".join(lines)

# ── Routes ───────────────────────────────────────────────────────────────────
@app.get("/api/schema")
def schema():
    return {"schema": get_schema()}

@app.post("/api/query")
async def query(req: QueryRequest):
    # Check if Anthropic API Key is configured
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sql, chart_config, insight = get_demo_response(req.question)
        if not sql:
            if insight:  # If get_demo_response returned an error string
                raise HTTPException(400, insight)
            raise HTTPException(
                400, 
                "Demo Mode: API key is missing. Please set ANTHROPIC_API_KEY or ask one of the suggestion questions. "
                "You can also run raw SQL queries directly by typing a query starting with SELECT."
            )
        
        try:
            rows, cols = execute_sql(sql)
        except Exception as e:
            raise HTTPException(400, f"Demo Mode SQL execution error: {str(e)}")

        plotly_json = None
        if chart_config and rows:
            try:
                plotly_json = figure_to_json(build_plotly_figure(rows, chart_config))
            except Exception:
                pass

        return {
            "sql": sql,
            "rows": rows,
            "columns": cols,
            "chart": chart_config,
            "plotly": plotly_json,
            "insight": insight,
            "row_count": len(rows)
        }

    schema_str = get_schema()
    history_str = format_history(req.history or [])

    # Stage 1: Generate SQL
    raw_sql = sql_chain.invoke({
        "schema": schema_str,
        "question": req.question,
        "history": history_str
    }).strip().rstrip(";")

    if not validate_sql(raw_sql):
        raise HTTPException(400, "Query contains forbidden operations.")

    # Execute
    try:
        rows, cols = execute_sql(raw_sql + ";")
    except Exception as e:
        raise HTTPException(400, f"SQL execution error: {str(e)}")

    if not rows:
        return {"sql": raw_sql, "rows": [], "columns": cols, "chart": None, "insight": "No data returned for this query."}

    # Stage 2a: Chart config
    sample = json.dumps(rows[:3], default=str)
    chart_raw = chart_chain.invoke({
        "question": req.question,
        "columns": cols,
        "sample": sample
    }).strip()
    try:
        chart_raw = re.sub(r"```json|```", "", chart_raw).strip()
        chart_config = json.loads(chart_raw)
    except Exception:
        chart_config = {"type": "table"}

    # Stage 2b: Insight
    insight = insight_chain.invoke({
        "query": raw_sql,
        "data": json.dumps(rows[:20], default=str),
        "question": req.question
    })

    plotly_json = None
    if chart_config and rows:
        try:
            plotly_json = figure_to_json(build_plotly_figure(rows, chart_config))
        except Exception:
            pass

    return {
        "sql": raw_sql,
        "rows": rows,
        "columns": cols,
        "chart": chart_config,
        "plotly": plotly_json,
        "insight": insight,
        "row_count": len(rows)
    }

@app.get("/api/tables")
def tables():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    result = []
    for (name,) in cur.fetchall():
        cur.execute(f"SELECT COUNT(*) FROM {name}")
        count = cur.fetchone()[0]
        result.append({"name": name, "rows": count})
    conn.close()
    return {"tables": result}

@app.get("/api/sample/{table}")
def sample(table: str):
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
        raise HTTPException(400, "Invalid table name")
    rows, cols = execute_sql(f"SELECT * FROM {table} LIMIT 5")
    return {"rows": rows, "columns": cols}

# ── Static frontend ──────────────────────────────────────────────────────────
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")

    @app.get("/")
    def root():
        return FileResponse(str(frontend_path / "index.html"))
