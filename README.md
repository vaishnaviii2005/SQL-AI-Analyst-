# SQL AI Analyst

**Ask questions in plain English. Get SQL, charts, and insights — instantly.**

A full-stack AI analytics platform that converts natural language to executable SQL queries, auto-generates visualizations, and produces LLM-driven data insights. Built for non-technical users to explore databases conversationally, and for engineers who want a showcase of production-grade LLM integration patterns.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-0.2-1C3C3C?style=flat-square)
![Claude](https://img.shields.io/badge/Claude-Sonnet_4.6-CC785C?style=flat-square)

---

## What it does

| Feature | Detail |
|---|---|
| **Natural Language → SQL** | LangChain chain converts any English question to a validated SQLite query |
| **Auto-visualization** | LLM selects chart type; interactive Plotly dashboards (Streamlit) and Chart.js (web UI) |
| **AI-generated insights** | Synthesizes the query result into a 3-point business insight with an actionable recommendation |
| **Context-aware conversation** | Maintains a rolling conversation window so follow-up questions reference previous queries |
| **Schema introspection** | Reads live database schema at runtime — works with any SQLite database |
| **SQL safety validation** | Regex guard prevents any DDL/DML (DROP, DELETE, INSERT, etc.) from executing |
| **Tabbed result UI** | Each query result shows Chart / Table / SQL / Insight in a clean dark-mode interface |

---

## Architecture

```
User question
      │
      ▼
┌─────────────────────────────────────┐
│  FastAPI Backend  (backend/main.py) │
│                                     │
│  Stage 1 ── SQL Generation Chain   │
│    LangChain + Claude Sonnet        │
│    Input:  question + schema + hist │
│    Output: validated SQL string     │
│                   │                 │
│                   ▼                 │
│         SQLite Execution            │
│                   │                 │
│         ┌─────────┴────────┐        │
│         ▼                  ▼        │
│  Stage 2a              Stage 2b     │
│  Chart Config          Insight Gen  │
│  (LangChain)           (LangChain)  │
│  → JSON config         → 3-point    │
│  → Chart.js render       narrative  │
└─────────────────────────────────────┘
```

The **two-stage LLM pattern** is the core architectural decision: one chain optimized for structured SQL output, two parallel chains optimized for freeform reasoning. This separation avoids prompt conflicts and produces higher quality output from both.

---

## Tech stack

- **Backend**: Python, FastAPI, LangChain, `langchain-anthropic`
- **AI**: Claude Sonnet via Anthropic API (LangChain orchestration)
- **Database**: SQLite with a realistic e-commerce seed dataset (sales, products, customers, marketing)
- **Dashboard**: Streamlit + Plotly interactive charts (`app.py`)
- **Web UI**: Vanilla JS, Chart.js 4, custom dark-mode CSS (`frontend/index.html`)
- **Deployment**: Antigravity (or any platform that runs Python + Uvicorn)

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
# Edit .env and add your Anthropic API key
```

### 3. Seed the database

```bash
python data/seed.py
# Creates data/analytics.db with ~5,000 sales records
```

### 4. Run

**Option A — Streamlit dashboard (Plotly, recommended):**

```bash
streamlit run app.py
# Open http://localhost:8501
```

**Option B — FastAPI + web UI:**

```bash
uvicorn backend.main:app --reload
# Open http://localhost:8000
```

---

## Deploy to Antigravity

```bash
# Install Antigravity CLI
npm install -g @antigravitydev/cli     # or pip install antigravity

# Login and deploy
antigravity login
antigravity deploy

# Set your secret
antigravity secrets set ANTHROPIC_API_KEY=sk-ant-...
```

The `antigravity.toml` in the repo root handles everything: dependency install, database seed, and server start.

---

## Example queries to try

```
What were the top 5 products by total revenue last year?
Show monthly sales trend for 2024 as a line chart
Which region has the highest average order value?
Compare revenue by sales channel
Which marketing campaign had the best ROI?
Show me customers who spent more than $500 in Q4 2024
How did Electronics category perform vs last year?
```

---

## Project structure

```
sql-ai-analyst/
├── app.py               # Streamlit dashboard (Plotly, conversational UI)
├── backend/
│   ├── main.py          # FastAPI app, LangChain chains, SQL execution
│   └── visualization.py # Plotly chart builder
├── frontend/
│   └── index.html       # Single-page UI (Chart.js, tabbed results)
├── data/
│   ├── seed.py          # Database seed script
│   └── analytics.db     # SQLite database (generated by seed.py)
├── antigravity.toml     # Deployment config
├── requirements.txt
├── .env.example
└── README.md
```

---

## Resume bullet points

> **SQL AI Analyst** | Python, FastAPI, LangChain, Claude API, SQLite, Chart.js

- Built a full-stack AI analytics platform using a **two-stage LangChain pipeline** — one chain for structured SQL generation, parallel chains for chart configuration and insight synthesis — reducing average query-to-insight time to under 3 seconds
- Integrated **Claude Sonnet via LangChain** with schema-aware prompting and conversation history context, enabling natural language database exploration without SQL knowledge
- Implemented **automated chart-type selection** via a secondary LLM call that analyzes query results and returns Chart.js config JSON, eliminating manual visualization decisions
- Enforced **SQL injection prevention** through regex-based DDL/DML validation before execution, with read-only query constraints across all user inputs
- Deployed on Antigravity with environment-based secrets management, a seeded SQLite dataset of 5,000+ records across 4 relational tables, and a responsive dark-mode single-page interface

---

## Interview talking points

**"Walk me through the architecture."**
> The app has a FastAPI backend with three LangChain chains powered by Claude. The first chain takes the user's question plus the live database schema and outputs a raw SQL string. I run that through a validation layer to block any write operations, then execute it against SQLite. The result feeds two parallel chains: one that decides the best chart type and returns Chart.js config as JSON, and one that generates a business insight from the data. The frontend is a single-page app that renders all three — chart, raw data table, the SQL itself, and the insight — in tabs.

**"Why two LLM calls instead of one?"**
> Separation of concerns. SQL generation needs strict, deterministic output — a single query string, nothing else. Insight generation needs the opposite: open-ended reasoning about numbers. Combining them in one prompt causes the model to hedge on both. Splitting them gives me better SQL accuracy and richer insights.

**"How do you prevent SQL injection or destructive queries?"**
> Two layers. First, a regex check before execution that blocks any DDL or DML keywords — DROP, DELETE, UPDATE, INSERT. Second, the system prompt explicitly instructs the model to only generate SELECT statements. The regex is the hard safety gate; the prompt is the soft guide.

**"How does the conversation context work?"**
> I maintain a client-side history array and send the last four question/SQL pairs with every request. The SQL generation chain includes this as a "conversation history" section in the prompt, so follow-up questions like "now filter that by region" work naturally.

---

## License

MIT
