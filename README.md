# SQL AI Analyst

**Ask questions in plain English. Get SQL, interactive charts, and AI insights — instantly.**

A full-stack AI analytics platform that converts natural language into executable SQL queries, auto-generates Plotly visualizations, and produces LLM-driven data insights. Built for non-technical users to explore databases conversationally, and for engineers who want a showcase of production-grade LLM integration patterns.



## What it does

| Feature | Detail |
|---|---|
| **Natural Language → SQL** | LangChain chain with Claude Sonnet converts plain English to validated SQLite queries |
| **Interactive charts** | A second LLM call selects the optimal chart type; Plotly renders bar, line, pie, scatter, and table |
| **AI-generated insights** | Third chain synthesizes results into a 3-point analysis with an actionable recommendation |
| **Demo Mode** | Works without an API key using pre-baked queries — great for live demos and portfolio showcasing |
| **Context-aware conversation** | Rolling 4-turn history keeps follow-up questions like "now filter by region" working naturally |
| **Schema introspection** | Reads live DB schema at runtime — portable to any SQLite database |
| **SQL safety validation** | Regex guard blocks DDL/DML (DROP, DELETE, INSERT, etc.) before any query executes |
| **Dual interface** | Streamlit dashboard (`app.py`) for rich interactivity; FastAPI + web UI (`backend/main.py`) for API access |

---

## Architecture

```
User question (natural language)
          │
          ▼
┌─────────────────────────────────────────┐
│   FastAPI Backend  /  Streamlit App     │
│                                         │
│  Stage 1 ─── SQL Generation Chain      │
│    LangChain + Claude Sonnet            │
│    Input:  question + live schema +     │
│            rolling conversation history │
│    Output: raw SQL string               │
│                    │                    │
│         SQL Safety Validator            │
│         (regex DDL/DML block)           │
│                    │                    │
│            SQLite Execution             │
│                    │                    │
│       ┌────────────┴────────────┐       │
│       ▼                         ▼       │
│  Stage 2a                  Stage 2b     │
│  Chart Config Chain        Insight Chain│
│  → JSON (type, x, y, title)→ 3-point   │
│  → Plotly figure               narrative│
└─────────────────────────────────────────┘
          │
          ▼
   Streamlit UI (Plotly charts, tabbed results)
   or FastAPI → frontend/index.html (Chart.js)
```

**The two-stage LLM pattern** is the core architectural decision: Stage 1 is optimized for strict, deterministic SQL output; Stages 2a/2b run in parallel and are optimized for freeform reasoning. Mixing them in a single prompt degrades both.

---

## Tech stack

| Layer | Technology |
|---|---|
| **AI / LLM** | Claude Sonnet 4.6 via Anthropic API, orchestrated with LangChain |
| **Backend** | Python, FastAPI, LangChain, `langchain-anthropic` |
| **Dashboard** | Streamlit 1.32+, Plotly 5.20+ |
| **Web UI** | Vanilla JS, Chart.js 4, custom dark-mode CSS |
| **Database** | SQLite — e-commerce seed dataset (4 tables, ~5,000 sales records) |
| **Config** | `.streamlit/config.toml` for dark theme, `.env` for secrets |

---

## Project structure

```
sql-ai-analyst/
├── app.py                      # Streamlit dashboard (main entry point)
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app + all 3 LangChain chains
│   └── visualization.py        # Plotly chart builder (bar, line, pie, scatter, table)
├── data/
│   ├── seed.py                 # Seeds analytics.db; auto-runs if DB missing
│   └── analytics.db            # SQLite database (git-ignored, generated on first run)
├── frontend/
│   └── index.html              # Single-page Chart.js UI for the FastAPI interface
├── .streamlit/
│   └── config.toml             # Dark theme config for Streamlit
├── requirements.txt
├── .env.example
└── README.md
```

---

## Local setup

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/sql-ai-analyst.git
cd sql-ai-analyst
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Open .env and set:
# ANTHROPIC_API_KEY=sk-ant-...
```

> **No API key?** The app runs in **Demo Mode** automatically — six pre-built queries work out of the box, and you can also type raw `SELECT` statements. Perfect for a live portfolio demo.

### 3. Seed the database

The database seeds itself automatically on first run. To seed manually:

```bash
python data/seed.py
# ✅ ~5,000 sales | 200 customers | 15 products | 7 marketing campaigns
```

### 4. Run

**Streamlit dashboard (recommended):**

```bash
streamlit run app.py
# → http://localhost:8501
```

**FastAPI + web UI:**

```bash
uvicorn backend.main:app --reload
# → http://localhost:8000
```

---

## Deploy to Streamlit Cloud

1. Push this repo to GitHub (make sure `data/analytics.db` is in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select your repo → set **Main file path** to `app.py`
3. Under **Advanced settings → Secrets**, add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
4. Deploy — the app reads `st.secrets` automatically, and `ensure_database()` seeds the DB on cold start

---

## Example queries to try

```
What were the top 5 products by total revenue last year?
Show monthly sales trend for 2024
Which region has the highest average order value?
Compare revenue by sales channel
Which marketing campaign had the best ROI?
Show customer segment distribution
Show me customers who spent more than $500 in Q4 2024
How did Electronics category perform vs last year?
```
## License

MIT
