"""
SQL AI Analyst — Interactive Streamlit dashboard with Plotly visualizations.

Run: streamlit run app.py
"""

import os
import json
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Streamlit Cloud: load API key from app secrets
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

from data.seed import ensure_database

ensure_database()

from backend.main import (
    get_db,
    get_schema,
    execute_sql,
    validate_sql,
    get_demo_response,
    format_history,
    sql_chain,
    insight_chain,
    chart_chain,
)
from backend.visualization import build_plotly_figure

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SQL AI Analyst",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
    .header-container {
        background: linear-gradient(135deg, #1e1e38 0%, #0d0f14 100%);
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid #2a2f45;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .header-title {
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: -0.05rem;
        background: linear-gradient(90deg, #6366f1, #a5b4fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .header-subtitle { color: #94a3b8; font-size: 1rem; }
    .sidebar-section-title {
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #64748b;
        letter-spacing: 0.05rem;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: #151821;
        border: 1px solid #2a2f45;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .history-item {
        font-size: 0.85rem;
        color: #94a3b8;
        padding: 0.4rem 0;
        border-bottom: 1px solid #2a2f45;
    }
</style>
""",
    unsafe_allow_html=True,
)


def get_sidebar_tables():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        result = []
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            count = cur.fetchone()[0]
            result.append({"name": t, "rows": count})
        conn.close()
        return result
    except Exception:
        return []


def get_dashboard_metrics():
    """Quick KPIs for the overview dashboard."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), COALESCE(SUM(revenue), 0) FROM sales")
        sales_count, total_revenue = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM customers")
        customer_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM products")
        product_count = cur.fetchone()[0]
        conn.close()
        return {
            "sales": sales_count or 0,
            "revenue": total_revenue or 0,
            "customers": customer_count or 0,
            "products": product_count or 0,
        }
    except Exception:
        return {"sales": 0, "revenue": 0, "customers": 0, "products": 0}


def process_question(question, history):
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        sql, chart_config, insight = get_demo_response(question)
        if not sql:
            if insight:
                return None, None, None, None, None, insight
            return (
                None,
                None,
                None,
                None,
                None,
                "Demo Mode: Set ANTHROPIC_API_KEY in .env for full AI, or use a suggested question. "
                "You can also type a raw SELECT query.",
            )
        try:
            rows, cols = execute_sql(sql)
            return sql, rows, cols, chart_config, insight, None
        except Exception as e:
            return None, None, None, None, None, f"Demo Mode SQL error: {e}"

    try:
        schema_str = get_schema()
        history_str = format_history(history)

        raw_sql = sql_chain.invoke({
            "schema": schema_str,
            "question": question,
            "history": history_str,
        }).strip().rstrip(";")

        if not validate_sql(raw_sql):
            return None, None, None, None, None, "Query blocked: only read-only SELECT statements are allowed."

        rows, cols = execute_sql(raw_sql + ";")

        if not rows:
            return raw_sql, [], cols, None, "No data returned for this query.", None

        sample = json.dumps(rows[:3], default=str)
        chart_raw = chart_chain.invoke({
            "question": question,
            "columns": cols,
            "sample": sample,
        }).strip()
        try:
            chart_raw = re.sub(r"```json|```", "", chart_raw).strip()
            chart_config = json.loads(chart_raw)
        except Exception:
            chart_config = {"type": "table"}

        insight = insight_chain.invoke({
            "query": raw_sql,
            "data": json.dumps(rows[:20], default=str),
            "question": question,
        })

        return raw_sql, rows, cols, chart_config, insight, None

    except Exception as e:
        return None, None, None, None, None, f"AI generation error: {e}"


def render_plotly_chart(rows, chart_config):
    fig = build_plotly_figure(rows, chart_config or {"type": "table"})
    st.plotly_chart(fig, use_container_width=True)


# ── Session State ─────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "question_input" not in st.session_state:
    st.session_state.question_input = ""
if "run_trigger" not in st.session_state:
    st.session_state.run_trigger = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### SQL AI Analyst")
    st.caption("LangChain · Claude · Plotly")

    if os.environ.get("ANTHROPIC_API_KEY"):
        st.success("AI Mode: Claude connected")
    else:
        st.info("Demo Mode: pre-built queries active")

    metrics = get_dashboard_metrics()
    st.markdown('<div class="sidebar-section-title">Overview</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("Sales", f"{metrics['sales']:,}")
    c2.metric("Revenue", f"${metrics['revenue']:,.0f}")
    c1.metric("Customers", f"{metrics['customers']:,}")
    c2.metric("Products", metrics["products"])

    st.markdown('<div class="sidebar-section-title">Database Tables</div>', unsafe_allow_html=True)
    icons = {"sales": "💰", "products": "📦", "customers": "👥", "marketing": "📣"}
    for t in get_sidebar_tables():
        icon = icons.get(t["name"], "🗃️")
        if st.button(f"{icon} {t['name']} ({t['rows']:,})", key=f"tbl_{t['name']}", use_container_width=True):
            st.session_state.question_input = f"Show me a sample of the {t['name']} table"
            st.session_state.run_trigger = True

    st.markdown('<div class="sidebar-section-title">Try Asking</div>', unsafe_allow_html=True)
    suggestions = [
        "What were the top 5 products by total revenue last year?",
        "Show monthly sales trend for 2024",
        "Which region has the highest average order value?",
        "Compare revenue by sales channel",
        "Which marketing campaign had the best ROI?",
        "Show customer segment distribution",
    ]
    for s in suggestions:
        if st.button(s, key=f"sug_{hash(s)}", use_container_width=True):
            st.session_state.question_input = s
            st.session_state.run_trigger = True

    if st.session_state.history:
        st.markdown('<div class="sidebar-section-title">Conversation</div>', unsafe_allow_html=True)
        for h in st.session_state.history[-5:]:
            st.markdown(f'<div class="history-item">💬 {h["question"][:60]}…</div>', unsafe_allow_html=True)
        if st.button("Clear history", use_container_width=True):
            st.session_state.history = []
            st.session_state.messages = []
            st.rerun()

# ── Main Layout ───────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="header-container">
    <div class="header-title">SQL AI Analyst</div>
    <div class="header-subtitle">
        Ask questions in plain English — get SQL, interactive Plotly charts, and AI insights instantly.
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# Overview charts (static dashboard)
with st.expander("📈 Dashboard overview", expanded=not st.session_state.messages):
    try:
        conn = get_db()
        monthly = pd.read_sql(
            "SELECT strftime('%Y-%m', sale_date) AS month, SUM(revenue) AS revenue FROM sales GROUP BY month ORDER BY month",
            conn,
        )
        channel = pd.read_sql(
            "SELECT channel, SUM(revenue) AS revenue FROM sales GROUP BY channel ORDER BY revenue DESC",
            conn,
        )
        conn.close()

        col_a, col_b = st.columns(2)
        with col_a:
            if not monthly.empty:
                fig = px.line(monthly, x="month", y="revenue", title="Monthly Revenue Trend", markers=True)
                fig.update_layout(template="plotly_dark", height=300, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)
        with col_b:
            if not channel.empty:
                fig = px.pie(channel, names="channel", values="revenue", title="Revenue by Channel", hole=0.4)
                fig.update_layout(template="plotly_dark", height=300, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.caption("Seed the database with `python data/seed.py` to see overview charts.")

# Chat input
user_query = st.chat_input("Ask a question about your database…")

if user_query:
    st.session_state.question_input = user_query
    st.session_state.run_trigger = True

if st.session_state.run_trigger:
    st.session_state.run_trigger = False
    q = st.session_state.question_input

    with st.spinner(f"Analyzing: {q}"):
        sql, rows, cols, chart_config, insight, error = process_question(q, st.session_state.history)

    if error:
        st.session_state.messages.append({"role": "user", "content": q})
        st.session_state.messages.append({"role": "error", "content": error})
    else:
        st.session_state.history.append({"question": q, "sql": sql})
        st.session_state.messages.append({
            "role": "user",
            "content": q,
        })
        st.session_state.messages.append({
            "role": "assistant",
            "sql": sql,
            "rows": rows,
            "columns": cols,
            "chart": chart_config,
            "insight": insight,
        })

# Render conversation
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    elif msg["role"] == "error":
        with st.chat_message("assistant"):
            st.error(msg["content"])
    else:
        with st.chat_message("assistant"):
            has_chart = msg.get("chart") and msg["chart"].get("type") != "table" and msg.get("rows")
            tabs = st.tabs(
                (["📊 Chart", "📋 Table", "⚡ SQL", "💡 Insight"] if has_chart else ["📋 Table", "⚡ SQL", "💡 Insight"])
            )
            idx = 0
            if has_chart:
                with tabs[idx]:
                    render_plotly_chart(msg["rows"], msg["chart"])
                idx += 1
            with tabs[idx]:
                st.dataframe(pd.DataFrame(msg["rows"]), use_container_width=True)
            idx += 1
            with tabs[idx]:
                st.code(msg["sql"], language="sql")
            idx += 1
            with tabs[idx]:
                st.info(msg["insight"])

if not st.session_state.messages:
    st.markdown(
        """
<div style="text-align:center;margin:3rem auto;max-width:520px;">
    <span style="font-size:3.5rem;">📊</span>
    <h3>Ask anything about your data</h3>
    <p style="color:#64748b;">
        Natural language questions are converted to SQL via LangChain + Claude,
        validated for safety, executed against SQLite, and visualized with Plotly.
    </p>
</div>
""",
        unsafe_allow_html=True,
    )
