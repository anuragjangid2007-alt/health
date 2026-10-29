import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("healthcheck.db")

DEMO_EVIDENCE = [
(
"Dehydration",
"dehydration thirst water dark urine dizziness fluids",
"Dehydration occurs when the body loses more fluid than it takes in. "
"Thirst, dark urine and dizziness can be warning signs. Severe symptoms "
"need prompt medical attention.",
"NHS",
"https://www.nhs.uk/conditions/dehydration/"
),
(
"Vitamin C and common cold",
"vitamin c cold common cold supplement prevention duration",
"Regular vitamin C supplements do not prevent colds for most people. "
"Regular use may slightly shorten cold duration.",
"NIH Office of Dietary Supplements",
"https://ods.od.nih.gov/factsheets/VitaminC-HealthProfessional/"
),
(
"Diabetes symptoms",
"diabetes thirst urination fatigue blurry vision symptoms",
"Possible diabetes symptoms include increased thirst, frequent urination, "
"fatigue and blurry vision. Symptoms alone cannot confirm diabetes; "
"medical assessment and appropriate tests are needed.",
"CDC",
"https://www.cdc.gov/diabetes/signs-symptoms/index.html"
),
(
"Antibiotics and viral infections",
"antibiotics virus viral infection bacteria cold flu",
"Antibiotics treat certain bacterial infections. They do not treat viral "
"illnesses such as the common cold or flu.",
"CDC",
"https://www.cdc.gov/antibiotic-use/about/index.html"
)
]

def get_connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    with get_connection() as con:
        con.executescript("""
CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT NOT NULL,
email TEXT NOT NULL UNIQUE COLLATE NOCASE,
password_hash TEXT NOT NULL,
age INTEGER,
profile_notes TEXT DEFAULT '',
created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

    CREATE TABLE IF NOT EXISTS evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL UNIQUE,
        keywords TEXT NOT NULL,
        summary TEXT NOT NULL,
        source_name TEXT NOT NULL,
        source_url TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        ai_answer TEXT NOT NULL,
        status TEXT NOT NULL,
        evidence_title TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
        """)

        for item in DEMO_EVIDENCE:
            con.execute("""
            INSERT OR IGNORE INTO evidence
            (title, keywords, summary, source_name, source_url)
            VALUES (?, ?, ?, ?, ?)
            """, item)

def create_user(name, email, password_hash):
    with get_connection() as con:
        cursor = con.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email.lower(), password_hash)
        )
        return cursor.lastrowid

def get_user_by_email(email):
    with get_connection() as con:
        return con.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.lower(),)
        ).fetchone()

def get_user_by_id(user_id):
    with get_connection() as con:
        return con.execute("""
SELECT id, name, email, age, profile_notes, created_at
FROM users WHERE id = ?
        """, (user_id,)).fetchone()

def update_profile(user_id, name, age, notes):
    with get_connection() as con:
        con.execute("""
UPDATE users
SET name = ?, age = ?, profile_notes = ?
WHERE id = ?
        """, (name, age, notes, user_id))

def get_evidence():
    with get_connection() as con:
        return con.execute(
            "SELECT * FROM evidence ORDER BY title"
        ).fetchall()

def save_history(user_id, question, answer, status, evidence_title):
    with get_connection() as con:
        con.execute("""
INSERT INTO search_history
(user_id, question, ai_answer, status, evidence_title)
VALUES (?, ?, ?, ?, ?)
        """, (user_id, question, answer, status, evidence_title))

def get_user_history(user_id, limit=None):
    with get_connection() as con:
        query = """
SELECT * FROM search_history
WHERE user_id = ?
ORDER BY id DESC
        """
        params = [user_id]

        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        return con.execute(query, params).fetchall()

def get_history_item(user_id, history_id):
    with get_connection() as con:
        return con.execute("""
SELECT * FROM search_history
WHERE id = ? AND user_id = ?
        """, (history_id, user_id)).fetchone()
