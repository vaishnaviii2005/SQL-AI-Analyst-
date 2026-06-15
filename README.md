# SQL AI Analyst 🏥

A natural language analytics dashboard that converts plain English questions into SQL queries, executes them against a live database, and returns charts, tables, and AI-generated insights.

## What it does

Type a question like **"Show me the top 5 hospitals with the highest occupancy"** and the app:

1. Sends your question + database schema to the Claude API
2. Receives a valid SQL query back
3. Executes it against a SQLite database
4. Renders the results as a chart, a sortable table, and a written insight

No hand-written SQL. No data wrangling. Just ask.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Node.js + Express |
| Database | SQLite (via `better-sqlite3`) |
| AI / NL→SQL | Anthropic Claude API (`claude-sonnet-4-6`) |
| Charts | Chart.js 4 |
| Frontend | Vanilla HTML/CSS/JS (no framework) |

---

## Project structure

```
sql-ai-analyst/
├── server.js          # Express server, SQLite setup, API routes
├── public/
│   └── index.html     # Full frontend (single file)
├── .env.example       # Environment variable template
├── package.json
└── README.md
```

---

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/sql-ai-analyst.git
cd sql-ai-analyst
```

### 2. Install dependencies

```bash
npm install
```

### 3. Set up your API key

```bash
cp .env.example .env
```

Open `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
PORT=3000
```

Get a key at [console.anthropic.com](https://console.anthropic.com).

### 4. Start the server

```bash
npm start
```

Open [http://localhost:3000](http://localhost:3000).

---

## API endpoints

### `POST /api/query`

Converts a natural language question to SQL, executes it, and returns results with an AI-generated insight.

**Request body:**
```json
{ "question": "Show me the top 5 hospitals with the highest occupancy" }
```

**Response:**
```json
{
  "sql": "SELECT name, ROUND(occupied * 100.0 / beds, 1) AS occupancy_pct FROM hospitals ORDER BY occupancy_pct DESC LIMIT 5",
  "columns": ["name", "occupancy_pct"],
  "rows": [{ "name": "CMC Vellore", "occupancy_pct": 92.0 }, "..."],
  "insight": "CMC Vellore leads with 92% occupancy across 2,000 beds..."
}
```

### `GET /api/schema`

Returns the database schema (table names and column types) for the sidebar display.

---

## Database schema

The app ships with a seeded in-memory SQLite database:

```sql
hospitals(id, name, city, beds, occupied, icu_beds, icu_occupied, department, revenue_q1)
admissions(id, hospital_id, month, year, count, avg_los_days)
staff(id, hospital_id, role, count)
patients(id, hospital_id, age, gender, diagnosis, admission_date, discharge_date)
```

To connect a real database, replace the `better-sqlite3` setup in `server.js` with your preferred driver (PostgreSQL via `pg`, MySQL via `mysql2`, etc.) and update the schema string passed to Claude.

---

## Example queries to try

- `Top 5 hospitals with the highest occupancy`
- `Which hospitals have ICU occupancy above 85%?`
- `Average length of stay per hospital, lowest to highest`
- `Total admissions per hospital in March 2024`
- `Doctor to patient ratio for each hospital`
- `Top 3 hospitals by Q1 revenue`

---

## How the NL→SQL pipeline works

```
User question
     │
     ▼
Claude API (system prompt includes schema)
     │  returns raw SQL string
     ▼
better-sqlite3 executes query
     │  returns rows[]
     ▼
Claude API (insight generation)
     │  returns 2-sentence analysis
     ▼
Frontend renders chart + table + insight
```

The system prompt constrains Claude to return only raw SQL with no markdown or explanation, making the response trivial to execute directly.

---

## Extending this project

- **Real database** — swap the in-memory SQLite with a Postgres/MySQL connection string
- **Auth** — add JWT middleware to protect the `/api/query` endpoint
- **Query history** — persist queries + results to a `history` table
- **Schema explorer** — click a table in the sidebar to preview its first 10 rows
- **CSV export** — add a download button that converts `rows[]` to CSV

---

## License

MIT
