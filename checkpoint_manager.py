import os
import json
import time
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Saves and restores orchestration progress for crash recovery."""

    def __init__(self, checkpoint_dir: str = "logs/checkpoints"):
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(self.checkpoint_dir, exist_ok=True)

    def _path(self, goal_hash: str) -> str:
        safe = "".join(c if c.isalnum() else "_" for c in goal_hash[:40])
        return os.path.join(self.checkpoint_dir, f"cp_{safe}.json")

    @staticmethod
    def goal_key(goal: str) -> str:
        import hashlib
        return hashlib.sha256(goal.encode()).hexdigest()[:16]

    def save(self, goal: str, state: Dict[str, Any]):
        key = self.goal_key(goal)
        path = self._path(key)
        data = {
            "goal": goal,
            "timestamp": time.time(),
            "step_index": state.get("step_index", 0),
            "plan": state.get("plan", []),
            "history": state.get("history", []),
            "data_bus": state.get("data_bus", {}),
            "status": state.get("status", "Paused"),
            "sub_goals": state.get("sub_goals", []),
            "completed_sub_goals": state.get("completed_sub_goals", []),
            "total_cost": state.get("total_cost", 0.0),
        }
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug("Checkpoint saved: %s (step %d)", key, data["step_index"])
        except Exception as e:
            logger.error("Checkpoint save failed: %s", e)

    def load(self, goal: str) -> Optional[Dict[str, Any]]:
        key = self.goal_key(goal)
        path = self._path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            age = time.time() - data.get("timestamp", 0)
            if age > 3600:
                logger.info("Checkpoint too old (%.0fs), ignoring", age)
                self.clear(goal)
                return None
            logger.info("Checkpoint loaded: %s (step %d, age %.0fs)", key, data["step_index"], age)
            return data
        except Exception as e:
            logger.warning("Checkpoint load failed: %s", e)
            return None

    def clear(self, goal: str):
        key = self.goal_key(goal)
        path = self._path(key)
        if os.path.exists(path):
            os.unlink(path)
            logger.debug("Checkpoint cleared: %s", key)

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        results = []
        for fname in os.listdir(self.checkpoint_dir):
            if fname.endswith(".json"):
                path = os.path.join(self.checkpoint_dir, fname)
                try:
                    with open(path) as f:
                        data = json.load(f)
                    results.append({
                        "goal": data.get("goal", ""),
                        "step": data.get("step_index", 0),
                        "status": data.get("status", ""),
                        "age": time.time() - data.get("timestamp", 0),
                    })
                except Exception:
                    pass
        return results
