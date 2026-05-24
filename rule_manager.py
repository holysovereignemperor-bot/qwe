import os
import json

class RuleManager:
    """Manages permanent user instructions and constraints."""
    def __init__(self, rules_path="knowledge/rules.json"):
        self.rules_path = rules_path
        self.rules = self._load_rules()

    def _load_rules(self):
        if os.path.exists(self.rules_path):
            with open(self.rules_path, 'r') as f:
                return json.load(f)
        return {
            "default_browser": "Safari",
            "formatting": "Always use Markdown for reports",
            "security": "Never share my password or secret keys"
        }

    def get_rules_context(self) -> str:
        return "Permanent User Rules:\n" + json.dumps(self.rules, indent=2)

    def update_rule(self, key, value):
        self.rules[key] = value
        with open(self.rules_path, 'w') as f:
            json.dump(self.rules, f, indent=2)
