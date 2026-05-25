import os
import json
import logging

logger = logging.getLogger(__name__)


class RuleManager:
    """Manages permanent user instructions and specialized agent personas."""

    def __init__(self, rules_path="knowledge/rules.json"):
        self.rules_path = rules_path
        self.rules = self._load_rules()
        self.personas = {
            "Senior Engineer": "You are a pragmatic, security-conscious Senior Software Engineer. You prefer CLI tools and clean, well-documented code.",
            "Executive Assistant": "You are a polite, proactive Executive Assistant. You focus on scheduling, organization, and clear communication.",
            "Research Scientist": "You are an analytical Research Scientist. You excel at data gathering, competitor analysis, and detailed reporting.",
        }

    def _load_rules(self):
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load rules: %s", e)
        return {
            "default_browser": "Safari",
            "persona": "Senior Engineer",
            "security": "Block all direct 'rm -rf' variants.",
        }

    def get_rules_context(self) -> str:
        persona_name = self.rules.get("persona", "Senior Engineer")
        persona_prompt = self.personas.get(persona_name, "")
        return (
            f"Current Persona: {persona_name}\n"
            f"Persona Instructions: {persona_prompt}\n"
            f"User Rules:\n{json.dumps(self.rules, indent=2)}"
        )

    def update_rule(self, key, value):
        self.rules[key] = value
        try:
            with open(self.rules_path, 'w') as f:
                json.dump(self.rules, f, indent=2)
            logger.info("Rule updated: %s = %s", key, value)
        except Exception as e:
            logger.error("Failed to save rules: %s", e)
