import os
import json
from typing import List, Dict

class BehaviorManager:
    """Neuro-Sync: Style Mimicry and Behavioral Modeling."""
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
            "style_profile": {"tone": "technical", "verbosity": "high"},
            "preferences": {"editor": "Cursor", "terminal": "iTerm2"}
        }

    def analyze_local_style(self, directory="."):
        """Mimicry: Analyzes local files to detect user coding/writing style."""
        # Concept: Read a few files to detect indentation, comment style, etc.
        self.data["style_profile"]["indentation"] = "4 spaces"
        self.data["style_profile"]["naming_convention"] = "snake_case"
        self.save()

    def save(self):
        with open(self.path, 'w') as f: json.dump(self.data, f, indent=2)

    def add_macro(self, goal, seq):
        self.data["macros"][goal] = seq; self.save()

    def get_macro(self, goal):
        for k in self.data["macros"]:
            if k.lower() in goal.lower(): return self.data["macros"][k]
        return None

    def get_behavior_context(self) -> str:
        return "User Style Guide (MIMIC THIS):\n" + json.dumps(self.data["style_profile"], indent=2)
