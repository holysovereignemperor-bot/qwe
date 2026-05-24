import os
import json
from typing import List, Dict

class MacroManager:
    """Saves and replays successful action sequences to save API tokens."""
    def __init__(self, macros_path="knowledge/macros.json"):
        self.macros_path = macros_path
        self.macros: Dict[str, List[Dict]] = self._load_macros()

    def _load_macros(self):
        if os.path.exists(self.macros_path):
            try:
                with open(self.macros_path, 'r') as f: return json.load(f)
            except Exception: return {}
        return {}

    def save_macro(self, goal: str, sequence: List[Dict]):
        self.macros[goal] = sequence
        with open(self.macros_path, 'w') as f: json.dump(self.macros, f, indent=2)

    def get_macro(self, goal: str):
        # Fuzzy match goal for replay
        for key in self.macros:
            if key.lower() in goal.lower(): return self.macros[key]
        return None
