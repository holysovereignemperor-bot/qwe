import os
import importlib.util
from skills import Skill, SkillRegistry

class PluginLoader:
    """Hot-Reloading: Dynamically loads and updates skill modules."""
    def __init__(self, registry: SkillRegistry, plugin_dir="plugins"):
        self.registry = registry
        self.plugin_dir = plugin_dir
        self.last_mtimes = {}
        if not os.path.exists(self.plugin_dir): os.makedirs(self.plugin_dir)

    def load_plugins(self):
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py"):
                path = os.path.join(self.plugin_dir, filename)
                mtime = os.path.getmtime(path)

                # Check if new or modified
                if path not in self.last_mtimes or mtime > self.last_mtimes[path]:
                    self.last_mtimes[path] = mtime
                    self._load_module(filename[:-3], path)

    def _load_module(self, name, path):
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "register_skills"):
                module.register_skills(self.registry)
                print(f"Hot-Reloaded Skill: {name}")
        except Exception as e: print(f"Plugin load error: {e}")
