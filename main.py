import asyncio
import sys
import argparse
from vision_client import VisionClient
from blackboard import Blackboard
from orchestrator import Orchestrator
from memory_vault import MemoryVault
from skills import SkillRegistry
from plugin_system import PluginLoader
from project_manager import ProjectManager

def main():
    parser = argparse.ArgumentParser(description="OmniAgent OS")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--goal", type=str, help="Goal for the agent (CLI mode only)")
    args = parser.parse_args()

    # Initialize Core
    vision = VisionClient()
    memory = MemoryVault()
    registry = SkillRegistry()
    loader = PluginLoader(registry)
    loader.load_plugins()
    project = ProjectManager()

    orchestrator = Orchestrator(vision, registry, memory)

    if args.cli:
        if not args.goal:
            print("Error: --goal is required for CLI mode")
            return

        blackboard = Blackboard(args.goal)
        asyncio.run(orchestrator.run(blackboard, project.get_workspace_summary()))
    else:
        from gui import OmniAgentGUI
        blackboard = Blackboard("")
        app = OmniAgentGUI(orchestrator, blackboard)
        app.mainloop()

if __name__ == "__main__":
    main()
