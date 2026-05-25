import asyncio
import sys
import argparse
import logging
import os
from llm_provider import LLMRouter, OpenAIProvider, OllamaProvider, ResponseCache
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
from checkpoint_manager import CheckpointManager
from task_decomposer import TaskDecomposer

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


def build_llm_router(args) -> LLMRouter:
    providers = []

    providers.append(OpenAIProvider(api_key=os.environ.get("OPENAI_API_KEY")))

    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    providers.append(OllamaProvider(base_url=ollama_url, default_model=ollama_model))

    preferred = getattr(args, "provider", None) or os.environ.get("LLM_PROVIDER", "openai")

    cache = ResponseCache(
        db_path="knowledge/llm_cache.db",
        max_entries=int(os.environ.get("LLM_CACHE_MAX", "5000")),
        ttl_seconds=int(os.environ.get("LLM_CACHE_TTL", "86400")),
    )

    router = LLMRouter(
        providers=providers,
        cache=cache,
        max_retries=3,
        preferred=preferred,
    )

    logger.info("LLM Router initialized: preferred=%s, providers=%s",
                preferred, [p.name for p in providers])
    return router


def main():
    parser = argparse.ArgumentParser(description="OmniAgent OS")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--goal", type=str, help="Goal for the agent")
    parser.add_argument("--profile", type=str, help="Knowledge profile", default="default")
    parser.add_argument("--persona", type=str, help="Persona type")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--provider", type=str, help="LLM provider: openai or ollama", default=None)
    parser.add_argument("--offline", action="store_true", help="Force offline mode (use local LLM)")
    parser.add_argument("--complex", action="store_true", help="Enable task decomposition for complex goals")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint if available")
    args = parser.parse_args()

    os.makedirs("logs", exist_ok=True)
    os.makedirs("knowledge", exist_ok=True)
    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)
    logger.info("OmniAgent OS starting...")

    if args.offline:
        os.environ.pop("OPENAI_API_KEY", None)
        logger.info("Forced offline mode — will use local LLM only")

    llm_router = build_llm_router(args)

    vision = VisionClient(llm_router=llm_router)
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
    checkpoint_mgr = CheckpointManager()
    decomposer = TaskDecomposer(llm_router) if args.complex else None

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
        checkpoint_mgr=checkpoint_mgr,
        task_decomposer=decomposer,
    )

    if args.cli:
        if not args.goal:
            logger.error("No goal provided in CLI mode")
            return
        blackboard = Blackboard(args.goal)
        run_server(blackboard)
        full_context = f"{rules_context}\n{knowledge_context}\n{project.get_workspace_summary()}"
        logger.info("Starting CLI mode with goal: %s", args.goal)
        logger.info("Active LLM provider: %s", llm_router.active_provider_name)

        if args.complex:
            asyncio.run(orchestrator.run_complex(blackboard, full_context))
        else:
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
