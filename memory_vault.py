import sqlite3
import json
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MemoryVault:
    """SQLite-based long-term memory with pattern discovery."""

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
                    usage_count INTEGER DEFAULT 1,
                    optimized_plan TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_goal ON experiences(goal)")
            conn.commit()
            logger.info("MemoryVault initialized: %s", self.db_path)
        except sqlite3.Error as e:
            logger.error("MemoryVault DB init failed: %s", e)
            raise
        finally:
            conn.close()

    def save_experience(self, goal: str, plan: List[Dict[str, Any]], success: bool, score: float = 1.0):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT id, usage_count FROM experiences WHERE goal = ?", (goal,))
                row = cursor.fetchone()
                if row:
                    conn.execute(
                        "UPDATE experiences SET usage_count = ?, score = score + ? WHERE id = ?",
                        (row[1] + 1, score, row[0])
                    )
                else:
                    conn.execute(
                        "INSERT INTO experiences (goal, plan, success, score) VALUES (?, ?, ?, ?)",
                        (goal, json.dumps(plan), success, score)
                    )
            logger.info("Experience saved for goal: %s", goal[:50])
        except sqlite3.Error as e:
            logger.error("Failed to save experience: %s", e)

    def retrieve_similar(self, goal: str, limit=5) -> List[Dict[str, Any]]:
        words = goal.lower().split()
        if not words:
            return []
        conditions = " OR ".join(["goal LIKE ?" for _ in words])
        match_expr = " + ".join([f"(CASE WHEN goal LIKE ? THEN 2 ELSE 0 END)" for _ in words])

        query = f"""
            SELECT goal, plan, score, usage_count, optimized_plan,
            ({match_expr}) as relevance
            FROM experiences
            WHERE success = 1 AND ({conditions})
            ORDER BY relevance DESC, score DESC
            LIMIT ?
        """
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
                        "usage": row[3],
                        "discovery": row[4] or "No optimized pattern yet",
                        "relevance": row[5]
                    })
        except sqlite3.OperationalError as e:
            logger.error("Memory retrieval failed: %s", e)
        return results
