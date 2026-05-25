import os
import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class BehaviorManager:
    """Tracks action sequences and user behavioral preferences."""

    def __init__(self, behavior_path="knowledge/behavior.json"):
        self.path = behavior_path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load behavior data: %s", e)
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
        try:
            with open(self.path, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save behavior data: %s", e)

    def add_macro(self, goal: str, sequence: List[Dict]):
        self.data["macros"][goal] = sequence
        self.save()
        logger.info("Macro added for: %s", goal[:50])

    def get_macro(self, goal: str):
        for key in self.data["macros"]:
            if key.lower() in goal.lower():
                return self.data["macros"][key]
        return None

    def get_behavior_context(self) -> str:
        return "User Preferences:\n" + json.dumps(self.data["preferences"], indent=2)
