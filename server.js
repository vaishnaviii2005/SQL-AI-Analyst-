require("dotenv").config();
const express = require("express");
const Database = require("better-sqlite3");
const cors = require("cors");
const path = require("path");

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static("public"));

// ─── Database setup ───────────────────────────────────────────────────────────
const db = new Database(":memory:");

db.exec(`
  CREATE TABLE hospitals (
    id INTEGER PRIMARY KEY,
    name TEXT,
    city TEXT,
    beds INTEGER,
    occupied INTEGER,
    icu_beds INTEGER,
    icu_occupied INTEGER,
    department TEXT,
    revenue_q1 REAL
  );

  CREATE TABLE admissions (
    id INTEGER PRIMARY KEY,
    hospital_id INTEGER,
    month TEXT,
    year INTEGER,
    count INTEGER,
    avg_los_days REAL,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
  );

  CREATE TABLE staff (
    id INTEGER PRIMARY KEY,
    hospital_id INTEGER,
    role TEXT,
    count INTEGER,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
  );

  CREATE TABLE patients (
    id INTEGER PRIMARY KEY,
    hospital_id INTEGER,
    age INTEGER,
    gender TEXT,
    diagnosis TEXT,
    admission_date TEXT,
    discharge_date TEXT,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
  );
`);

// Seed data
const hospitals = [
  [1,"Apollo Multispecialty","Mumbai",620,581,80,74,"Multispecialty",42.1],
  [2,"Fortis General","Delhi",450,409,60,55,"General",31.8],
  [3,"AIIMS Trauma Centre","Delhi",800,704,120,114,"Trauma",18.2],
  [4,"Narayana Heart Inst.","Bangalore",340,272,50,38,"Cardiology",55.4],
  [5,"Max Super Specialty","Gurgaon",510,480,70,67,"Multispecialty",38.9],
  [6,"Ruby Hall Clinic","Pune",290,232,40,29,"General",22.1],
  [7,"Manipal Hospital","Bangalore",600,534,90,80,"Multispecialty",47.6],
  [8,"CMC Vellore","Vellore",2000,1840,200,168,"Teaching",29.3],
];
const insertHospital = db.prepare(
  "INSERT INTO hospitals VALUES (?,?,?,?,?,?,?,?,?)"
);
hospitals.forEach((h) => insertHospital.run(...h));

const admissionsData = [
  [1,1,"Jan",2024,410,4.2],[2,1,"Feb",2024,390,4.1],[3,1,"Mar",2024,450,4.4],
  [4,2,"Jan",2024,310,5.1],[5,2,"Feb",2024,295,5.0],[6,2,"Mar",2024,330,4.9],
  [7,3,"Jan",2024,680,6.2],[8,3,"Feb",2024,640,6.0],[9,3,"Mar",2024,710,6.3],
  [10,4,"Jan",2024,250,3.8],[11,4,"Feb",2024,240,3.7],[12,4,"Mar",2024,275,3.9],
  [13,5,"Jan",2024,460,4.5],[14,5,"Feb",2024,440,4.3],[15,5,"Mar",2024,490,4.6],
  [16,6,"Jan",2024,210,4.0],[17,6,"Feb",2024,200,3.9],[18,6,"Mar",2024,225,4.1],
  [19,7,"Jan",2024,510,4.7],[20,7,"Feb",2024,490,4.6],[21,7,"Mar",2024,540,4.8],
  [22,8,"Jan",2024,1760,5.5],[23,8,"Feb",2024,1680,5.4],[24,8,"Mar",2024,1840,5.6],
];
const insertAdm = db.prepare("INSERT INTO admissions VALUES (?,?,?,?,?,?)");
admissionsData.forEach((a) => insertAdm.run(...a));

const staffData = [
  [1,1,"Doctor",180],[2,1,"Nurse",420],[3,1,"Admin",85],
  [4,2,"Doctor",130],[5,2,"Nurse",310],[6,2,"Admin",60],
  [7,3,"Doctor",240],[8,3,"Nurse",580],[9,3,"Admin",110],
  [10,4,"Doctor",100],[11,4,"Nurse",240],[12,4,"Admin",45],
  [13,5,"Doctor",155],[14,5,"Nurse",370],[15,5,"Admin",75],
  [16,6,"Doctor",85],[17,6,"Nurse",200],[18,6,"Admin",40],
  [19,7,"Doctor",175],[20,7,"Nurse",410],[21,7,"Admin",80],
  [22,8,"Doctor",620],[23,8,"Nurse",1480],[24,8,"Admin",290],
];
const insertStaff = db.prepare("INSERT INTO staff VALUES (?,?,?,?)");
staffData.forEach((s) => insertStaff.run(...s));

const patientsData = [];
let pid = 1;
hospitals.forEach(([hid,,,,beds]) => {
  const diagnoses = ["Hypertension","Diabetes","Fracture","Pneumonia","Appendicitis","Cardiac Arrest","Stroke","Kidney Stone"];
  for (let i = 0; i < Math.min(beds / 10, 20); i++) {
    patientsData.push([
      pid++, hid,
      20 + Math.floor(Math.random() * 70),
      Math.random() > 0.5 ? "M" : "F",
      diagnoses[Math.floor(Math.random() * diagnoses.length)],
      "2024-0" + (1 + Math.floor(Math.random() * 3)) + "-" + String(1 + Math.floor(Math.random() * 28)).padStart(2,"0"),
      "2024-0" + (3 + Math.floor(Math.random() * 3)) + "-" + String(1 + Math.floor(Math.random() * 28)).padStart(2,"0"),
    ]);
  }
});
const insertPatient = db.prepare("INSERT INTO patients VALUES (?,?,?,?,?,?,?)");
patientsData.forEach((p) => insertPatient.run(...p));

// ─── Schema introspection (sent to Claude) ────────────────────────────────────
const SCHEMA = `
hospitals(id, name, city, beds, occupied, icu_beds, icu_occupied, department, revenue_q1)
  -- beds: total capacity | occupied: current patients | revenue_q1: revenue in crores INR

admissions(id, hospital_id, month, year, count, avg_los_days)
  -- count: monthly admissions | avg_los_days: average length of stay

staff(id, hospital_id, role, count)
  -- role: 'Doctor' | 'Nurse' | 'Admin'

patients(id, hospital_id, age, gender, diagnosis, admission_date, discharge_date)
  -- gender: 'M' | 'F' | diagnosis: free text
`;

// ─── API: Natural language → SQL → results ────────────────────────────────────
app.post("/api/query", async (req, res) => {
  const { question } = req.body;
  if (!question) return res.status(400).json({ error: "question is required" });

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return res.status(500).json({ error: "ANTHROPIC_API_KEY not set in .env" });

  // Step 1: Generate SQL from natural language
  let sql;
  try {
    const nlResponse = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-6",
        max_tokens: 500,
        system: `You are a SQL expert. Given a natural language question and a SQLite schema, 
return ONLY the raw SQL query with no explanation, no markdown, no backticks. 
The query must be valid SQLite syntax. Do not use ILIKE (use LIKE instead).

Schema:
${SCHEMA}`,
        messages: [{ role: "user", content: question }],
      }),
    });
    const nlData = await nlResponse.json();
    sql = nlData.content[0].text.trim().replace(/```sql|```/gi, "").trim();
  } catch (err) {
    return res.status(500).json({ error: "SQL generation failed", detail: err.message });
  }

  // Step 2: Execute SQL against SQLite
  let rows, columns;
  try {
    const stmt = db.prepare(sql);
    rows = stmt.all();
    columns = rows.length > 0 ? Object.keys(rows[0]) : [];
  } catch (err) {
    return res.status(400).json({ error: "SQL execution failed", sql, detail: err.message });
  }

  // Step 3: Generate insight from results
  let insight = "";
  try {
    const insightResponse = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-6",
        max_tokens: 200,
        system: "You are a healthcare data analyst. Given query results, write a 2-sentence insight. Be specific with numbers. No bullet points, plain prose only.",
        messages: [{
          role: "user",
          content: `Question: "${question}"\nResults: ${JSON.stringify(rows.slice(0, 10))}`,
        }],
      }),
    });
    const insightData = await insightResponse.json();
    insight = insightData.content[0].text.trim();
  } catch (_) {
    insight = "Insight generation unavailable.";
  }

  res.json({ sql, columns, rows, insight });
});

// ─── API: Get schema for frontend display ─────────────────────────────────────
app.get("/api/schema", (req, res) => {
  const tables = ["hospitals", "admissions", "staff", "patients"];
  const schema = {};
  tables.forEach((t) => {
    const info = db.prepare(`PRAGMA table_info(${t})`).all();
    schema[t] = info.map((c) => ({ name: c.name, type: c.type }));
  });
  res.json(schema);
});

// ─── Start ────────────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`\n🏥 SQL AI Analyst running at http://localhost:${PORT}\n`);
});
