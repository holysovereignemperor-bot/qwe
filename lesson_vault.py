import sqlite3
import json
import os
from typing import List, Dict, Any

class LessonVault:
    """Stores generalized task patterns synthesized from successful experiences."""
    def __init__(self, db_path="knowledge/lessons.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    strategy TEXT,
                    success_rate FLOAT,
                    usage_count INTEGER DEFAULT 1,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_topic ON lessons(topic)")
            conn.commit()
        finally:
            conn.close()

    def add_lesson(self, topic: str, strategy: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id, usage_count FROM lessons WHERE topic = ?", (topic,))
            row = cursor.fetchone()
            if row:
                conn.execute(
                    "UPDATE lessons SET usage_count = ? WHERE id = ?",
                    (row[1] + 1, row[0])
                )
            else:
                conn.execute(
                    "INSERT INTO lessons (topic, strategy, success_rate) VALUES (?, ?, ?)",
                    (topic, strategy, 1.0)
                )

    def get_lessons(self, goal: str, limit=3) -> List[Dict[str, Any]]:
        words = goal.lower().split()
        if not words: return []
        conditions = " OR ".join(["topic LIKE ?" for _ in words])
        query = f"SELECT topic, strategy FROM lessons WHERE {conditions} ORDER BY usage_count DESC LIMIT ?"
        params = [f"%{w}%" for w in words] + [limit]

        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                for row in cursor:
                    results.append({"topic": row[0], "strategy": row[1]})
        except sqlite3.OperationalError: pass
        return results
