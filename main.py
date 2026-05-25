import asyncio
import sys
import argparse
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

def main():
    parser = argparse.ArgumentParser(description="OmniAgent OS")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--goal", type=str, help="Goal for the agent")
    parser.add_argument("--profile", type=str, help="Knowledge profile", default="default")
    parser.add_argument("--persona", type=str, help="Persona type")
    args = parser.parse_args()

    # 1. Initialize Zenith Core
    vision = VisionClient()
    memory = MemoryVault()
    registry = SkillRegistry()
    loader = PluginLoader(registry); loader.load_plugins()

    knowledge = KnowledgeManager()
    project = ProjectManager(knowledge)
    rules = RuleManager()
    scheduler = TaskScheduler()
    vault = SecureVault()

    if args.persona: rules.update_rule("persona", args.persona)

    profile_data = knowledge.get_profile(args.profile)
    knowledge_context = f"Profile ({args.profile}): {profile_data}" if profile_data else ""
    rules_context = rules.get_rules_context()

    orchestrator = Orchestrator(vision, registry, memory, knowledge)

    # 2. Modes
    if args.cli:
        if not args.goal: return
        blackboard = Blackboard(args.goal)
        run_server(blackboard)
        full_context = f"{rules_context}\n{knowledge_context}\n{project.get_workspace_summary()}"
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
        app.mainloop()

if __name__ == "__main__": main()
