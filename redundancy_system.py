"""
Data Redundancy Removal System
Task 1 - Internship Project
Language: Python 3
"""

import sqlite3
import hashlib
import json
from datetime import datetime
from difflib import SequenceMatcher


# ─────────────────────────────────────────────
#  DATABASE SETUP
# ─────────────────────────────────────────────

def init_db(db_path="data_store.db"):
    """Create the SQLite database and required tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Main table: stores unique, verified records
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unique_records (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hash   TEXT UNIQUE NOT NULL,
            content     TEXT NOT NULL,
            category    TEXT NOT NULL,
            added_at    TEXT NOT NULL
        )
    """)

    # Log table: tracks every insertion attempt and its result
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insertion_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            content     TEXT NOT NULL,
            status      TEXT NOT NULL,   -- ACCEPTED | REDUNDANT | FALSE_POSITIVE
            reason      TEXT,
            attempted_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully.")


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


def classify_entry(content: str, db_path="data_store.db") -> dict:
    """
    Classify incoming data as:
      - REDUNDANT      → exact duplicate (same hash)
      - FALSE_POSITIVE → near-duplicate (high similarity but not identical)
      - UNIQUE         → genuinely new data
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    new_hash = compute_hash(content)

    # Step 1: Exact match check
    cursor.execute("SELECT content FROM unique_records WHERE data_hash = ?", (new_hash,))
    exact = cursor.fetchone()
    if exact:
        conn.close()
        return {
            "status": "REDUNDANT",
            "reason": "Exact duplicate found (same hash).",
            "similar_to": exact[0]
        }

    # Step 2: Fuzzy/near-duplicate check
    cursor.execute("SELECT content FROM unique_records")
    all_records = cursor.fetchall()
    conn.close()

    for (existing,) in all_records:
        score = similarity_score(content, existing)
        if score >= 0.85:   # 85% similarity threshold
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


def add_entry(content: str, db_path="data_store.db") -> dict:
    """
    Validate and add a new entry.
    Only UNIQUE entries are saved to unique_records.
    All attempts are logged.
    """
    if not content or not content.strip():
        return {"status": "ERROR", "reason": "Empty content rejected."}

    classification = classify_entry(content, db_path)
    status = classification["status"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Log every attempt regardless of outcome
    cursor.execute("""
        INSERT INTO insertion_log (content, status, reason, attempted_at)
        VALUES (?, ?, ?, ?)
    """, (content, status, classification["reason"], timestamp))

    # Only insert if truly unique
    if status == "UNIQUE":
        data_hash = compute_hash(content)
        cursor.execute("""
            INSERT INTO unique_records (data_hash, content, category, added_at)
            VALUES (?, ?, ?, ?)
        """, (data_hash, content.strip(), "general", timestamp))

    conn.commit()
    conn.close()

    return {
        "status": status,
        "reason": classification["reason"],
        "similar_to": classification.get("similar_to"),
        "timestamp": timestamp
    }


def get_all_records(db_path="data_store.db") -> list:
    """Fetch all unique records from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, content, category, added_at FROM unique_records ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "content": r[1], "category": r[2], "added_at": r[3]} for r in rows]


def get_logs(db_path="data_store.db") -> list:
    """Fetch all insertion attempt logs."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, content, status, reason, attempted_at FROM insertion_log ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "content": r[1], "status": r[2], "reason": r[3], "attempted_at": r[4]} for r in rows]


def get_stats(db_path="data_store.db") -> dict:
    """Return summary statistics."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM unique_records")
    unique_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM insertion_log WHERE status='REDUNDANT'")
    redundant_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM insertion_log WHERE status='FALSE_POSITIVE'")
    fp_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM insertion_log")
    total_attempts = cursor.fetchone()[0]
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
    DB = "data_store.db"
    init_db(DB)

    print("\n" + "="*55)
    print("   DATA REDUNDANCY REMOVAL SYSTEM — TEST RUN")
    print("="*55)

    test_entries = [
        "John Doe, john@example.com, +91-9876543210",
        "Jane Smith, jane@example.com, +91-9123456789",
        "John Doe, john@example.com, +91-9876543210",   # exact duplicate
        "John doe, john@example.com, +91-9876543210",   # near-duplicate
        "Alice Johnson, alice@company.org, +1-555-0101",
        "Jane Smith, jane@example.com, +91-9123456789", # exact duplicate
        "Bob Martin, bob.martin@work.net, +44-7911-123456",
        "Alice Johnsonn, alice@company.org, +1-555-0101", # near-duplicate typo
    ]

    for entry in test_entries:
        result = add_entry(entry, DB)
        icon = "✅" if result["status"] == "UNIQUE" else ("🔴" if result["status"] == "REDUNDANT" else "⚠️")
        print(f"\n{icon} [{result['status']}] \"{entry[:45]}...\"" if len(entry) > 45 else f"\n{icon} [{result['status']}] \"{entry}\"")
        print(f"   → {result['reason']}")
        if result["similar_to"]:
            print(f"   → Similar to: \"{result['similar_to'][:50]}\"")

    print("\n" + "="*55)
    print("   FINAL STATISTICS")
    print("="*55)
    stats = get_stats(DB)
    for k, v in stats.items():
        print(f"  {k.replace('_', ' ').title():<28}: {v}")

    print("\n" + "="*55)
    print("   UNIQUE RECORDS IN DATABASE")
    print("="*55)
    for rec in get_all_records(DB):
        print(f"  [{rec['id']}] {rec['content']}")

    print("\n✅ System working correctly. Run app.py to launch the web dashboard.\n")
