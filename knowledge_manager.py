import os
import json
from typing import Dict, Any, Optional

class KnowledgeManager:
    """Manages profile-based context injection from the knowledge/ directory."""
    def __init__(self, knowledge_dir="knowledge"):
        self.knowledge_dir = knowledge_dir
        if not os.path.exists(self.knowledge_dir):
            os.makedirs(self.knowledge_dir)

    def get_profile(self, profile_name: str) -> Optional[Dict[str, Any]]:
        if not profile_name:
            return None
        path = os.path.join(self.knowledge_dir, f"{profile_name}.json")
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def list_profiles(self):
        return [f.replace(".json", "") for f in os.listdir(self.knowledge_dir) if f.endswith(".json")]

    def save_profile(self, profile_name: str, data: Dict[str, Any]):
        path = os.path.join(self.knowledge_dir, f"{profile_name}.json")
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
