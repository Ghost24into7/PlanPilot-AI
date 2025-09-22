# database.py
"""
Database module for SQLite operations.
Handles storage and retrieval of plans and queries.
"""

import sqlite3
from datetime import datetime
import os

DB_FILE = "task_plans.db"

def init_db():
    """
    Initialize the SQLite database with plans and queries tables.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS plans
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  goal TEXT,
                  plan TEXT,
                  timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS queries
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  query TEXT,
                  results TEXT,
                  timestamp TEXT)''')
    conn.commit()
    conn.close()

def store_plan(goal, plan, timestamp):
    """
    Store a generated plan in the database.
    
    Args:
        goal (str): User's goal.
        plan (str): Generated plan text.
        timestamp (str): ISO timestamp.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO plans (goal, plan, timestamp) VALUES (?, ?, ?)", (goal, plan, timestamp))
    conn.commit()
    conn.close()

def store_query(query, results, timestamp):
    """
    Store a search query and its results.
    
    Args:
        query (str): Search query.
        results (str): JSON string of results.
        timestamp (str): ISO timestamp.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO queries (query, results, timestamp) VALUES (?, ?, ?)", (query, results, timestamp))
    conn.commit()
    conn.close()

def get_all_plans():
    """
    Retrieve all plans ordered by timestamp descending.
    
    Returns:
        list: List of tuples (goal, plan, timestamp).
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT goal, plan, timestamp FROM plans ORDER BY timestamp DESC")
    plans = c.fetchall()
    conn.close()
    return plans