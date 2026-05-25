import asyncio
import sys
import argparse
import logging
import threading
from vision_client import VisionClient
from blackboard import Blackboard
from orchestrator import Orchestrator
from memory_vault import MemoryVault
from skills import SkillRegistry
from plugin_system import PluginLoader
from project_manager import ProjectManager
from knowledge_manager import KnowledgeManager
from rule_manager import RuleManager
from web_server import run_server
from task_scheduler import TaskScheduler
from secure_vault import SecureVault
from lesson_vault import LessonVault
from behavior_manager import BehaviorManager
from system_watchdog import SystemWatchdog
from system_doctor import SystemDoctor

logger = logging.getLogger(__name__)


def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler("logs/omniagent.log", mode="a"),
        ],
    )


def main():
    parser = argparse.ArgumentParser(description="OmniAgent OS")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--goal", type=str, help="Goal for the agent")
    parser.add_argument("--profile", type=str, help="Knowledge profile", default="default")
    parser.add_argument("--persona", type=str, help="Persona type")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    import os
    os.makedirs("logs", exist_ok=True)
    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)
    logger.info("OmniAgent OS starting...")

    vision = VisionClient()
    memory = MemoryVault()
    registry = SkillRegistry()
    loader = PluginLoader(registry)
    loader.load_plugins()

    knowledge = KnowledgeManager()
    project = ProjectManager(knowledge)
    rules = RuleManager()
    scheduler = TaskScheduler()
    vault = SecureVault()
    lesson_vault = LessonVault()
    behavior = BehaviorManager()
    watchdog = SystemWatchdog()
    doctor = SystemDoctor()

    if args.persona:
        rules.update_rule("persona", args.persona)

    profile_data = knowledge.get_profile(args.profile)
    knowledge_context = f"Profile ({args.profile}): {profile_data}" if profile_data else ""
    rules_context = rules.get_rules_context()

    orchestrator = Orchestrator(
        vision, registry, memory, knowledge,
        lesson_vault=lesson_vault,
        behavior=behavior,
        watchdog=watchdog,
        doctor=doctor,
    )

    if args.cli:
        if not args.goal:
            logger.error("No goal provided in CLI mode")
            return
        blackboard = Blackboard(args.goal)
        run_server(blackboard)
        full_context = f"{rules_context}\n{knowledge_context}\n{project.get_workspace_summary()}"
        logger.info("Starting CLI mode with goal: %s", args.goal)
        asyncio.run(orchestrator.run(blackboard, full_context))
    else:
        from gui import OmniAgentGUI
        blackboard = Blackboard("")
        run_server(blackboard)

        app = OmniAgentGUI(orchestrator, blackboard)
        app.initial_context = f"{rules_context}\n{knowledge_context}\n{project.get_workspace_summary()}"
        app.project_manager = project
        app.scheduler = scheduler
        app.vault = vault
        logger.info("Starting GUI mode")
        app.mainloop()


if __name__ == "__main__":
    main()
