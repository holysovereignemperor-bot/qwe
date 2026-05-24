import os
import importlib.util
from skills import Skill, SkillRegistry

class PluginLoader:
    """Dynamically loads skills from the plugins/ directory."""
    def __init__(self, registry: SkillRegistry, plugin_dir="plugins"):
        self.registry = registry
        self.plugin_dir = plugin_dir
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)

    def load_plugins(self):
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py"):
                name = filename[:-3]
                path = os.path.join(self.plugin_dir, filename)

                spec = importlib.util.spec_from_file_location(name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, "register_skills"):
                    module.register_skills(self.registry)
