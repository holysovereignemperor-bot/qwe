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
from web_server import run_server

def main():
    parser = argparse.ArgumentParser(description="OmniAgent OS")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--goal", type=str, help="Goal for the agent (CLI mode only)")
    parser.add_argument("--profile", type=str, help="Knowledge profile to load", default="default")
    args = parser.parse_args()

    # 1. Initialize Core
    vision = VisionClient()
    memory = MemoryVault()
    registry = SkillRegistry()

    # Load Plugins
    loader = PluginLoader(registry)
    loader.load_plugins()

    # Context Managers
    project = ProjectManager()
    knowledge = KnowledgeManager()

    # Load active profile context
    profile_data = knowledge.get_profile(args.profile)
    knowledge_context = f"Knowledge Profile ({args.profile}): {profile_data}" if profile_data else ""

    orchestrator = Orchestrator(vision, registry, memory)

    # 2. Modes
    if args.cli:
        if not args.goal:
            print("Error: --goal is required for CLI mode")
            return

        blackboard = Blackboard(args.goal)
        # Start Web Server in background for CLI as well
        run_server(blackboard)

        full_context = f"{knowledge_context}\n{project.get_workspace_summary()}"
        asyncio.run(orchestrator.run(blackboard, full_context))
    else:
        from gui import OmniAgentGUI
        blackboard = Blackboard("")

        # Start Web Server
        run_server(blackboard)

        app = OmniAgentGUI(orchestrator, blackboard)
        # Pass context to orchestrator via closure or state
        # For simplicity, we just pass the initial summary
        initial_context = f"{knowledge_context}\n{project.get_workspace_summary()}"

        # In GUI mode, the RUN button triggers orchestrator.run with initial_context
        # We need to make sure gui knows about it
        app.initial_context = initial_context

        app.mainloop()

if __name__ == "__main__":
    main()
