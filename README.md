# Data-Redundancy-Removal-System
A cloud-hosted data deduplication system that protects database integrity by filtering out redundant records through a multi-layered verification pipeline. It combines SHA-256 cryptographic hashing for exact-match blocking with fuzzy matching logic to detect and eliminate near-duplicate entries in real-time.

Live Public URL of this Project - https://data-redundancy-removal-system.vercel.app/

# Data Redundancy Removal System

---

## 1. LANGUAGE USED

**Python 3** — with:
* `flask` &rarr; lightweight web framework for the dashboard UI
* `mysql-connector-python` &rarr; connects to AWS RDS MySQL cloud database
* `hashlib` &rarr; SHA-256 hashing for exact duplicate detection
* `difflib` &rarr; fuzzy/near-duplicate detection
* `os` &rarr; reads environment variables for credentials

---

## 2. OVERVIEW OF THE CODE

The system has **3 layers**:

### Layer 1 — Hashing (Exact Duplicate Detection)
Every incoming entry is converted to a SHA-256 hash.  
If that hash already exists in the DB &rarr; it is flagged as **REDUNDANT** and blocked.

### Layer 2 — Fuzzy Matching (Near-Duplicate / False Positive Detection)
If no exact match is found, the new entry is compared against all existing records using Python's `SequenceMatcher`.  
If similarity &ge; 85% &rarr; flagged as **FALSE_POSITIVE** and blocked.

### Layer 3 — Database Write (Unique Data Only)
Only entries that pass both checks get written to the `unique_records` table.  
Every attempt (pass or fail) is logged in the `insertion_log` table.

---

## Classification Logic Summary

| Situation | Status | Action |
| :--- | :--- | :--- |
| Hash already in DB | **REDUNDANT** | Blocked — not saved |
| Similarity &ge; 85% with any record | **FALSE_POSITIVE** | Blocked — not saved |
| Passes both checks | **UNIQUE** | Saved to database |

---

## Cloud Architecture

| Component | Technology |
| :--- | :--- |
| **Web Framework** | Flask (Python) |
| **Database** | AWS RDS MySQL |
| **Hosting** | Render.com |
| **Code Storage** | GitHub |

---

Built with Python + Flask + AWS RDS MySQL.
