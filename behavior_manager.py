import os
import json
from typing import List, Dict

class BehaviorManager:
    """Neuro-Sync: Synthesis of Workflow Maps and User Preferences."""
    def __init__(self, behavior_path="knowledge/behavior.json"):
        self.path = behavior_path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f: return json.load(f)
            except Exception: pass
        return {
            "workflows": {}, # Goal -> Optimized Chain
            "preferences": {"editor": "Cursor", "ui": "dark", "verbosity": "concise"},
            "history_count": 0
        }

    def save(self):
        with open(self.path, 'w') as f: json.dump(self.data, f, indent=2)

    def map_workflow(self, goal: str, chain: List[Dict]):
        """Synthesizes a reusable workflow map for a goal."""
        self.data["workflows"][goal] = [c.get("skill") for c in chain if "skill" in c]
        self.data["history_count"] += 1
        self.save()

    def get_workflow(self, goal: str):
        for k in self.data["workflows"]:
            if k.lower() in goal.lower(): return self.data["workflows"][k]
        return None

    def get_behavior_context(self) -> str:
        return "User Behavior Map (Frequent Workflows):\n" + json.dumps(self.data["workflows"], indent=2)
