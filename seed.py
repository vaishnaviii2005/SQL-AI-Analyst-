"""
Seed script — creates a realistic e-commerce analytics database.
Run: python data/seed.py
"""
import sqlite3
import random
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "analytics.db"

CATEGORIES = ["Electronics", "Clothing", "Books", "Home & Garden", "Sports", "Beauty"]
REGIONS = ["North", "South", "East", "West", "Central"]
CHANNELS = ["Online", "In-Store", "Mobile App", "Partner"]
PRODUCTS = [
    ("Wireless Headphones", "Electronics", 79.99),
    ("Laptop Stand", "Electronics", 49.99),
    ("USB-C Hub", "Electronics", 34.99),
    ("Running Shoes", "Sports", 89.99),
    ("Yoga Mat", "Sports", 29.99),
    ("Python Cookbook", "Books", 39.99),
    ("Data Science Handbook", "Books", 44.99),
    ("Coffee Maker", "Home & Garden", 59.99),
    ("Air Purifier", "Home & Garden", 119.99),
    ("Face Serum", "Beauty", 24.99),
    ("Moisturizer SPF50", "Beauty", 19.99),
    ("Winter Jacket", "Clothing", 129.99),
    ("Denim Jeans", "Clothing", 59.99),
    ("Wireless Mouse", "Electronics", 29.99),
    ("Desk Lamp", "Home & Garden", 39.99),
]

def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    DROP TABLE IF EXISTS sales;
    DROP TABLE IF EXISTS products;
    DROP TABLE IF EXISTS customers;
    DROP TABLE IF EXISTS marketing;

    CREATE TABLE products (
        product_id   INTEGER PRIMARY KEY,
        name         TEXT,
        category     TEXT,
        price        REAL,
        cost         REAL,
        stock        INTEGER
    );

    CREATE TABLE customers (
        customer_id  INTEGER PRIMARY KEY,
        name         TEXT,
        region       TEXT,
        segment      TEXT,
        joined_date  TEXT
    );

    CREATE TABLE sales (
        sale_id      INTEGER PRIMARY KEY,
        product_id   INTEGER,
        customer_id  INTEGER,
        sale_date    TEXT,
        quantity     INTEGER,
        revenue      REAL,
        channel      TEXT,
        FOREIGN KEY (product_id)  REFERENCES products(product_id),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );

    CREATE TABLE marketing (
        campaign_id  INTEGER PRIMARY KEY,
        name         TEXT,
        channel      TEXT,
        start_date   TEXT,
        end_date     TEXT,
        spend        REAL,
        impressions  INTEGER,
        clicks       INTEGER,
        conversions  INTEGER
    );
    """)

    # Products
    for i, (name, cat, price) in enumerate(PRODUCTS, 1):
        cur.execute(
            "INSERT INTO products VALUES (?,?,?,?,?,?)",
            (i, name, cat, price, round(price * 0.4, 2), random.randint(50, 500))
        )

    # Customers
    segments = ["Premium", "Regular", "New", "At-Risk"]
    names = ["Alice Chen", "Bob Patel", "Carol Smith", "David Kim", "Eva Jones",
             "Frank Wu", "Grace Lee", "Henry Brown", "Iris Martin", "Jack Wilson",
             "Kate Davis", "Leo Garcia", "Mia Taylor", "Noah Anderson", "Olivia White"]
    start = date(2022, 1, 1)
    for i in range(1, 201):
        name = random.choice(names) + f" {i}"
        joined = start + timedelta(days=random.randint(0, 700))
        cur.execute(
            "INSERT INTO customers VALUES (?,?,?,?,?)",
            (i, name, random.choice(REGIONS), random.choice(segments), str(joined))
        )

    # Sales — 2 years of data
    sale_id = 1
    for day_offset in range(730):
        sale_date = str(date(2023, 1, 1) + timedelta(days=day_offset))
        n_sales = random.randint(3, 25)
        for _ in range(n_sales):
            pid = random.randint(1, len(PRODUCTS))
            cid = random.randint(1, 200)
            qty = random.randint(1, 5)
            price = PRODUCTS[pid - 1][2]
            discount = random.choice([0, 0, 0, 0.05, 0.10, 0.15])
            rev = round(price * qty * (1 - discount), 2)
            cur.execute(
                "INSERT INTO sales VALUES (?,?,?,?,?,?,?)",
                (sale_id, pid, cid, sale_date, qty, rev, random.choice(CHANNELS))
            )
            sale_id += 1

    # Marketing campaigns
    campaigns = [
        ("Summer Splash", "Online", "2023-06-01", "2023-08-31", 12000),
        ("Back to School", "Mobile App", "2023-08-15", "2023-09-15", 8000),
        ("Black Friday Blitz", "Online", "2023-11-20", "2023-11-30", 25000),
        ("New Year Push", "In-Store", "2024-01-01", "2024-01-31", 9000),
        ("Spring Sale", "Partner", "2024-03-01", "2024-04-15", 11000),
        ("Tech Week", "Online", "2024-05-01", "2024-05-07", 15000),
        ("Holiday Season", "Mobile App", "2024-11-01", "2024-12-31", 30000),
    ]
    for i, (name, ch, sd, ed, spend) in enumerate(campaigns, 1):
        imp = random.randint(50000, 500000)
        clicks = int(imp * random.uniform(0.02, 0.08))
        conv = int(clicks * random.uniform(0.05, 0.20))
        cur.execute(
            "INSERT INTO marketing VALUES (?,?,?,?,?,?,?,?,?)",
            (i, name, ch, sd, ed, spend, imp, clicks, conv)
        )

    conn.commit()
    conn.close()
    print(f"Database seeded at {DB_PATH}")
    print(f"   {sale_id-1} sales | 200 customers | {len(PRODUCTS)} products | {len(campaigns)} campaigns")

def ensure_database():
    """Create and seed the database if it does not exist (needed for Streamlit Cloud)."""
    if not DB_PATH.exists():
        seed()


if __name__ == "__main__":
    seed()
