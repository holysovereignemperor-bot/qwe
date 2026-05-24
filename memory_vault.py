import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

class MemoryVault:
    """SQLite-based long-term memory for task patterns."""
    def __init__(self, db_path="memory_vault.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        # Use a context manager to ensure the connection is closed
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal TEXT,
                    plan TEXT,
                    success BOOLEAN,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goal ON experiences(goal)")
            conn.commit()
        finally:
            conn.close()

    def save_experience(self, goal: str, plan: List[Dict[str, Any]], success: bool):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO experiences (goal, plan, success) VALUES (?, ?, ?)",
                (goal, json.dumps(plan), success)
            )

    def retrieve_similar(self, goal: str, limit=3) -> List[Dict[str, Any]]:
        words = goal.lower().split()
        if not words:
            return []

        query = "SELECT goal, plan FROM experiences WHERE success = 1 AND (" + \
                " OR ".join(["goal LIKE ?" for _ in words]) + ") LIMIT ?"
        params = [f"%{w}%" for w in words] + [limit]

        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                for row in cursor:
                    results.append({"goal": row[0], "plan": json.loads(row[1])})
        except sqlite3.OperationalError:
            pass

        return results
