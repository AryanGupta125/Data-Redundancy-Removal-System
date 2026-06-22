"""
Flask Web API — Data Redundancy Removal System
Database: AWS RDS MySQL
Run: python app.py
"""

from flask import Flask, request, jsonify, send_from_directory
from redundancy_system import init_db, add_entry, get_all_records, get_logs, get_stats

import os
app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "..", "static"))

init_db()


@app.route("/")
def index():
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    return send_from_directory(static_dir, "index.html")


@app.route("/api/add", methods=["POST"])
def api_add():
    data = request.get_json()
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "Content cannot be empty"}), 400
    result = add_entry(content)
    return jsonify(result)


@app.route("/api/records", methods=["GET"])
def api_records():
    return jsonify(get_all_records())


@app.route("/api/logs", methods=["GET"])
def api_logs():
    return jsonify(get_logs())


@app.route("/api/stats", methods=["GET"])
def api_stats():
    return jsonify(get_stats())

