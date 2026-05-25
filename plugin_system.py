import os
import logging
import importlib.util
from skills import Skill, SkillRegistry

logger = logging.getLogger(__name__)


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
                try:
                    spec = importlib.util.spec_from_file_location(name, path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    if hasattr(module, "register_skills"):
                        module.register_skills(self.registry)
                        logger.info("Plugin loaded: %s", name)
                    else:
                        logger.warning("Plugin '%s' missing register_skills()", name)
                except Exception as e:
                    logger.error("Failed to load plugin '%s': %s", name, e)
