"""
Data Redundancy Removal System
Task 1 - Internship Project
Language: Python 3
Database: AWS RDS MySQL
"""

import hashlib
import os
from datetime import datetime
from difflib import SequenceMatcher
import mysql.connector
from mysql.connector import Error


# ─────────────────────────────────────────────
#  DATABASE CONNECTION
# ─────────────────────────────────────────────

def get_connection():
    """
    Create and return a connection to AWS RDS MySQL.
    Reads credentials from environment variables (never hardcode them).
    """
    try:
        conn = mysql.connector.connect(
            host     = os.environ.get("DB_HOST"),       # AWS RDS endpoint
            port     = int(os.environ.get("DB_PORT", 3306)),
            user     = os.environ.get("DB_USER"),       # master username
            password = os.environ.get("DB_PASSWORD"),   # master password
            database = os.environ.get("DB_NAME"),       # database name
        )
        return conn
    except Error as e:
        print(f"[DB ERROR] Could not connect to AWS RDS: {e}")
        raise


# ─────────────────────────────────────────────
#  DATABASE SETUP
# ─────────────────────────────────────────────

def init_db():
    """Create the required tables in AWS RDS MySQL if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Main table: stores only unique, verified records
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unique_records (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            data_hash   VARCHAR(64) UNIQUE NOT NULL,
            content     TEXT NOT NULL,
            category    VARCHAR(100) NOT NULL,
            added_at    DATETIME NOT NULL
        )
    """)

    # Log table: tracks every insertion attempt and its outcome
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insertion_log (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            content      TEXT NOT NULL,
            status       VARCHAR(20) NOT NULL,
            reason       TEXT,
            attempted_at DATETIME NOT NULL
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("[DB] AWS RDS MySQL — Tables initialized successfully.")


# ─────────────────────────────────────────────
#  CORE FUNCTIONS
# ─────────────────────────────────────────────

def compute_hash(content: str) -> str:
    """Generate a SHA-256 hash for a given string (normalized)."""
    normalized = content.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def similarity_score(a: str, b: str) -> float:
    """Return a 0.0–1.0 similarity ratio between two strings."""
    return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()


def classify_entry(content: str) -> dict:
    """
    Classify incoming data as:
      - REDUNDANT      → exact duplicate (same hash)
      - FALSE_POSITIVE → near-duplicate (similarity >= 85%)
      - UNIQUE         → genuinely new data
    """
    conn = get_connection()
    cursor = conn.cursor()

    new_hash = compute_hash(content)

    # Step 1: Exact hash match check
    cursor.execute(
        "SELECT content FROM unique_records WHERE data_hash = %s", (new_hash,)
    )
    exact = cursor.fetchone()
    if exact:
        cursor.close()
        conn.close()
        return {
            "status": "REDUNDANT",
            "reason": "Exact duplicate found (same hash).",
            "similar_to": exact[0]
        }

    # Step 2: Fuzzy / near-duplicate check
    cursor.execute("SELECT content FROM unique_records")
    all_records = cursor.fetchall()
    cursor.close()
    conn.close()

    for (existing,) in all_records:
        score = similarity_score(content, existing)
        if score >= 0.85:
            return {
                "status": "FALSE_POSITIVE",
                "reason": f"Near-duplicate detected (similarity: {score:.0%}).",
                "similar_to": existing
            }

    return {
        "status": "UNIQUE",
        "reason": "Data is unique and verified.",
        "similar_to": None
    }


def add_entry(content: str) -> dict:
    """
    Validate and add a new entry to AWS RDS MySQL.
    Only UNIQUE entries are saved to unique_records.
    All attempts are always logged to insertion_log.
    """
    if not content or not content.strip():
        return {"status": "ERROR", "reason": "Empty content rejected."}

    classification = classify_entry(content)
    status = classification["status"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cursor = conn.cursor()

    # Always log every attempt
    cursor.execute(
        "INSERT INTO insertion_log (content, status, reason, attempted_at) VALUES (%s, %s, %s, %s)",
        (content, status, classification["reason"], timestamp)
    )

    # Only write to unique_records if truly unique
    if status == "UNIQUE":
        data_hash = compute_hash(content)
        cursor.execute(
            "INSERT INTO unique_records (data_hash, content, category, added_at) VALUES (%s, %s, %s, %s)",
            (data_hash, content.strip(), "general", timestamp)
        )

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "status": status,
        "reason": classification["reason"],
        "similar_to": classification.get("similar_to"),
        "timestamp": timestamp
    }


def get_all_records() -> list:
    """Fetch all unique records from AWS RDS MySQL."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, content, category, added_at FROM unique_records ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"id": r[0], "content": r[1], "category": r[2], "added_at": str(r[3])} for r in rows]


def get_logs() -> list:
    """Fetch all insertion attempt logs from AWS RDS MySQL."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, content, status, reason, attempted_at FROM insertion_log ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"id": r[0], "content": r[1], "status": r[2], "reason": r[3], "attempted_at": str(r[4])} for r in rows]


def get_stats() -> dict:
    """Return summary statistics from AWS RDS MySQL."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM unique_records")
    unique_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM insertion_log WHERE status='REDUNDANT'")
    redundant_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM insertion_log WHERE status='FALSE_POSITIVE'")
    fp_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM insertion_log")
    total_attempts = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return {
        "total_attempts": total_attempts,
        "unique_stored": unique_count,
        "redundant_blocked": redundant_count,
        "false_positives_blocked": fp_count,
        "efficiency": f"{((redundant_count + fp_count) / total_attempts * 100):.1f}%" if total_attempts else "0%"
    }


# ─────────────────────────────────────────────
#  DEMO / TEST RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()

    print("\n" + "="*55)
    print("   DATA REDUNDANCY REMOVAL SYSTEM — TEST RUN")
    print("="*55)

    test_entries = [
        "John Doe, john@example.com, +91-9876543210",
        "Jane Smith, jane@example.com, +91-9123456789",
        "John Doe, john@example.com, +91-9876543210",    # exact duplicate
        "John doe, john@example.com, +91-9876543210",    # near-duplicate
        "Alice Johnson, alice@company.org, +1-555-0101",
        "Jane Smith, jane@example.com, +91-9123456789",  # exact duplicate
        "Bob Martin, bob.martin@work.net, +44-7911-123456",
        "Alice Johnsonn, alice@company.org, +1-555-0101", # near-duplicate typo
    ]

    for entry in test_entries:
        result = add_entry(entry)
        icon = "✅" if result["status"] == "UNIQUE" else ("🔴" if result["status"] == "REDUNDANT" else "⚠️")
        print(f"\n{icon} [{result['status']}] \"{entry}\"")
        print(f"   → {result['reason']}")
        if result["similar_to"]:
            print(f"   → Similar to: \"{result['similar_to'][:50]}\"")

    print("\n" + "="*55)
    stats = get_stats()
    for k, v in stats.items():
        print(f"  {k.replace('_',' ').title():<28}: {v}")
    print("\n✅ Done. Run app.py to launch the dashboard.\n")
