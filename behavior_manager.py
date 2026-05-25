import os
import json
from typing import List, Dict

class BehaviorManager:
    """Neuro-Sync: Tracks action sequences and user behavioral stylistic preferences."""
    def __init__(self, behavior_path="knowledge/behavior.json"):
        self.path = behavior_path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f: return json.load(f)
            except Exception: pass
        return {
            "macros": {},
            "preferences": {
                "preferred_editor": "Cursor",
                "ui_mode": "dark",
                "coding_style": "pragmatic",
                "apps": ["iTerm2", "Safari", "Slack"]
            }
        }

    def save(self):
        with open(self.path, 'w') as f: json.dump(self.data, f, indent=2)

    def add_macro(self, goal: str, sequence: List[Dict]):
        self.data["macros"][goal] = sequence
        self.save()

    def get_macro(self, goal: str):
        for key in self.data["macros"]:
            if key.lower() in goal.lower(): return self.data["macros"][key]
        return None

    def get_behavior_context(self) -> str:
        return "User Stylistic Preferences (Behavior Modeling):\n" + json.dumps(self.data["preferences"], indent=2)
