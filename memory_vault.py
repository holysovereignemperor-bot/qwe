import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

class MemoryVault:
    """SQLite-based long-term memory for task patterns with improved retrieval."""
    def __init__(self, db_path="memory_vault.db"):
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
                    score FLOAT DEFAULT 1.0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goal ON experiences(goal)")
            conn.commit()
        finally:
            conn.close()

    def save_experience(self, goal: str, plan: List[Dict[str, Any]], success: bool, score: float = 1.0):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO experiences (goal, plan, success, score) VALUES (?, ?, ?, ?)",
                (goal, json.dumps(plan), success, score)
            )

    def retrieve_similar(self, goal: str, limit=5) -> List[Dict[str, Any]]:
        """Weighted keyword search for better pattern matching."""
        words = goal.lower().split()
        if not words:
            return []

        # Ranking results based on number of matching keywords
        conditions = " OR ".join(["goal LIKE ?" for _ in words])
        query = f"""
            SELECT goal, plan, score,
            ({" + ".join(["(CASE WHEN goal LIKE ? THEN 1 ELSE 0 END)" for _ in words])}) as match_count
            FROM experiences
            WHERE success = 1 AND ({conditions})
            ORDER BY match_count DESC, score DESC
            LIMIT ?
        """

        # We need params for both conditions and the match_count sum
        params = [f"%{w}%" for w in words] * 2 + [limit]

        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                for row in cursor:
                    results.append({
                        "goal": row[0],
                        "plan": json.loads(row[1]),
                        "score": row[2],
                        "relevance": row[3]
                    })
        except sqlite3.OperationalError as e:
            print(f"Memory retrieval error: {e}")

        return results
