"""
Flask Web API — Data Redundancy Removal System
Run: python app.py
Then open: http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
from redundancy_system import init_db, add_entry, get_all_records, get_logs, get_stats
import os

app = Flask(__name__, static_folder="static")
DB_PATH = "data_store.db"

# Initialize DB on startup
init_db(DB_PATH)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/add", methods=["POST"])
def api_add():
    data = request.get_json()
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "Content cannot be empty"}), 400
    result = add_entry(content, DB_PATH)
    return jsonify(result)


@app.route("/api/records", methods=["GET"])
def api_records():
    return jsonify(get_all_records(DB_PATH))


@app.route("/api/logs", methods=["GET"])
def api_logs():
    return jsonify(get_logs(DB_PATH))


@app.route("/api/stats", methods=["GET"])
def api_stats():
    return jsonify(get_stats(DB_PATH))


if __name__ == "__main__":
    print("\n🚀 Server starting at http://localhost:5000\n")
    app.run(debug=True, port=5000)
