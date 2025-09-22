# database.py
"""
Database module for SQLite operations.
Handles initialization, storing/retrieving plans and queries.
Uses ISO timestamps for consistency.
"""

import sqlite3
import os
from datetime import datetime

DB_FILE = "task_plans.db"

def init_db():
    """
    Initialize SQLite database with plans and queries tables.
    Creates tables if they don't exist.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS plans
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  goal TEXT NOT NULL,
                  plan TEXT NOT NULL,
                  timestamp TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS queries
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  query TEXT NOT NULL,
                  results TEXT NOT NULL,
                  timestamp TEXT NOT NULL)''')
    conn.commit()
    conn.close()

def store_plan(goal: str, plan: str):
    """
    Store a generated plan in the database.
    :param goal: User's input goal.
    :param plan: Generated plan text (Markdown).
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute("INSERT INTO plans (goal, plan, timestamp) VALUES (?, ?, ?)",
              (goal, plan, timestamp))
    conn.commit()
    conn.close()

def store_query(query: str, results: str):
    """
    Store a search query and its results in the database.
    :param query: Search query string.
    :param results: JSON/stringified results from search.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    c.execute("INSERT INTO queries (query, results, timestamp) VALUES (?, ?, ?)",
              (query, results, timestamp))
    conn.commit()
    conn.close()

def get_all_plans():
    """
    Retrieve all plans ordered by timestamp descending.
    :return: List of tuples (goal, plan, timestamp).
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT goal, plan, timestamp FROM plans ORDER BY timestamp DESC")
    plans = c.fetchall()
    conn.close()
    return plans