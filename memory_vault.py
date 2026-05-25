import sqlite3
import json
import os
from typing import List, Dict, Any

class MemoryVault:
    """Neural Pattern Discovery with Failure Pattern Avoidance."""
    def __init__(self, db_path="knowledge/memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal TEXT,
                    plan TEXT,
                    success BOOLEAN,
                    reflection TEXT,
                    usage_count INTEGER DEFAULT 1,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goal ON experiences(goal)")
            conn.commit()
        finally:
            conn.close()

    def save_experience(self, goal: str, plan: List[Dict[str, Any]], success: bool, reflection: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO experiences (goal, plan, success, reflection) VALUES (?, ?, ?, ?)",
                (goal, json.dumps(plan), success, reflection)
            )

    def retrieve_similar(self, goal: str, limit=5) -> Dict[str, List[Dict[str, Any]]]:
        """Returns both successful and failure patterns for better planning."""
        words = goal.lower().split()
        if not words: return {"success": [], "fail": []}
        conditions = " OR ".join(["goal LIKE ?" for _ in words])
        params = [f"%{w}%" for w in words]

        results = {"success": [], "fail": []}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(f"SELECT goal, plan, success, reflection FROM experiences WHERE ({conditions}) LIMIT ?", params + [limit])
                for row in cursor:
                    item = {"goal": row[0], "plan": json.loads(row[1]), "reflection": row[3]}
                    if row[2]: results["success"].append(item)
                    else: results["fail"].append(item)
        except sqlite3.OperationalError: pass
        return results
