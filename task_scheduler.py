import time
import json
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Goal queue and time-based execution."""

    def __init__(self, schedule_path="knowledge/schedule.json"):
        self.schedule_path = schedule_path
        self.queue: List[Dict] = []
        self._load_schedule()

    def _load_schedule(self):
        if os.path.exists(self.schedule_path):
            try:
                with open(self.schedule_path, 'r') as f:
                    self.queue = json.load(f)
            except Exception as e:
                logger.warning("Failed to load schedule: %s", e)

    def save_schedule(self):
        try:
            with open(self.schedule_path, 'w') as f:
                json.dump(self.queue, f, indent=2)
        except Exception as e:
            logger.error("Failed to save schedule: %s", e)

    def add_task(self, goal: str, run_at: float = None):
        task = {"goal": goal, "run_at": run_at or time.time(), "status": "pending"}
        self.queue.append(task)
        self.save_schedule()
        logger.info("Task scheduled: %s", goal[:50])

    def get_pending(self):
        return [t for t in self.queue if t["status"] == "pending" and t["run_at"] <= time.time()]

    def mark_completed(self, goal: str):
        for t in self.queue:
            if t["goal"] == goal:
                t["status"] = "completed"
        self.save_schedule()
        logger.info("Task completed: %s", goal[:50])
