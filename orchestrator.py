import asyncio
import gc
import json
import os
from agents import ArchitectAgent, ExecutorAgent, AuditorAgent
from blackboard import Blackboard
from memory_vault import MemoryVault
from mac_utils import get_marked_screenshot, get_ui_tree, get_window_metadata
from vision_client import VisionClient
from skills import SkillRegistry
from report_generator import ReportGenerator
from voice_os import VoiceOS
from knowledge_manager import KnowledgeManager
from macro_manager import MacroManager
from system_watchdog import SystemWatchdog

class Orchestrator:
    def __init__(self, vision: VisionClient, registry: SkillRegistry, memory: MemoryVault, knowledge: KnowledgeManager):
        self.architect = ArchitectAgent(vision); self.executor = ExecutorAgent(vision)
        self.auditor = AuditorAgent(vision); self.registry = registry
        self.memory = memory; self.knowledge = knowledge
        self.status_callback = None; self.reporter = ReportGenerator()
        self.voice = VoiceOS(); self.macro_manager = MacroManager()
        self.watchdog = SystemWatchdog()
        self.MAX_STEPS = 50; self.MAX_COST = 5.0
        self.history_dir = "logs/history"
        if not os.path.exists(self.history_dir): os.makedirs(self.history_dir)

    async def run(self, blackboard: Blackboard, project_context: str = ""):
        blackboard.gui_callback = self.status_callback
        try:
            # System Health Check
            health = self.watchdog.check_health()
            if health["critical"]:
                blackboard.error = health["reason"]; return

            macro = self.macro_manager.get_macro(blackboard.goal)
            if macro:
                if self.status_callback: self.status_callback("log", "⚡ Macro replay...")
                for step in macro:
                    skill = self.registry.get(step.get('skill'))
                    if skill: await skill.execute(step.get('params', {}))
                blackboard.status = "Completed (Macro)"; return

            self.voice.speak(f"Monolith initiate: {blackboard.goal}")
            while blackboard.is_running and blackboard.current_step_index < self.MAX_STEPS:
                while blackboard.is_paused: await asyncio.sleep(0.5)
                gc.collect()

                # Dynamic Resource Monitor
                health = self.watchdog.check_health()
                if health["critical"]:
                    blackboard.is_paused = True
                    if self.status_callback: self.status_callback("log", f"⚠️  System Warning: {health['reason']}")

                blackboard.total_cost = self.architect.vision.total_cost
                blackboard.last_screenshot, marks = get_marked_screenshot()
                blackboard.last_ui_tree = get_ui_tree()

                if not blackboard.plan:
                    if self.status_callback: self.status_callback("agent_active", "PM")
                    await self.architect.plan(blackboard, self.memory, self.knowledge, project_context)

                if self.status_callback: self.status_callback("agent_active", "Executor")
                action = await self.executor.act(blackboard)

                if action.get("skill") == "ask_user":
                    blackboard.is_paused = True; continue

                skill = self.registry.get(action.get('skill'))
                if skill:
                    if self.status_callback and action.get('skill') == "click":
                         self.status_callback("visual_feedback", action.get('params', {}))
                    await skill.execute(action.get('params', {}))

                if self.status_callback: self.status_callback("agent_active", "Auditor")
                blackboard.last_screenshot, _ = get_marked_screenshot()
                blackboard.last_ui_tree = get_ui_tree()
                verification = await self.auditor.verify(action, blackboard)
                blackboard.add_history(action, verification)

                if verification.get("success"):
                    blackboard.current_step_index += 1
                else:
                    await self.auditor.generate_correction_plan(verification, blackboard)
                    blackboard.plan = []

                if blackboard.current_step_index >= len(blackboard.plan) and len(blackboard.plan) > 0:
                    blackboard.status = "Completed"
                    sequence = [h['action'] for h in blackboard.history if h['result'].get('success')]
                    self.macro_manager.save_macro(blackboard.goal, sequence)
                    break
                await asyncio.sleep(0.5)

        except Exception as e: blackboard.error = str(e)
        finally:
            blackboard.is_running = False; blackboard.status = "Finished"
            self.reporter.generate_report(blackboard)
