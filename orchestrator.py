import asyncio
import gc
import json
import os
from agents import ArchitectAgent, ExecutorAgent, AuditorAgent
from blackboard import Blackboard
from memory_vault import MemoryVault
from mac_utils import get_marked_screenshot, get_ui_tree, get_window_metadata, compute_visual_diff, GhostOverlay
from vision_client import VisionClient
from skills import SkillRegistry
from report_generator import ReportGenerator
from voice_os import VoiceOS
from knowledge_manager import KnowledgeManager
from behavior_manager import BehaviorManager
from system_watchdog import SystemWatchdog
from system_doctor import SystemDoctor
from lesson_vault import LessonVault
from memory_compressor import MemoryCompressor

class Orchestrator:
    def __init__(self, vision: VisionClient, registry: SkillRegistry, memory: MemoryVault, knowledge: KnowledgeManager):
        self.vision = vision
        self.architect = ArchitectAgent(vision); self.executor = ExecutorAgent(vision)
        self.auditor = AuditorAgent(vision); self.registry = registry
        self.memory = memory; self.knowledge = knowledge
        self.status_callback = None; self.reporter = ReportGenerator()
        self.voice = VoiceOS(); self.behavior = BehaviorManager()
        self.watchdog = SystemWatchdog(); self.doctor = SystemDoctor()
        self.compressor = MemoryCompressor(vision)
        self.overlay = GhostOverlay()
        self.MAX_STEPS = 50; self.MAX_COST = 5.0
        self.history_dir = "logs/history"
        if not os.path.exists(self.history_dir): os.makedirs(self.history_dir)

    async def execute_step_parallel(self, action, blackboard):
        """Concurrent execution of a single step."""
        skill = self.registry.get(action.get('skill'))
        if skill:
            res = await skill.execute(action.get('params', {}))
            if "bus_update" in res: blackboard.data_bus.update(res["bus_update"])
            return res
        return {"status": "error", "error": "Skill missing"}

    async def run(self, blackboard: Blackboard, project_context: str = ""):
        blackboard.gui_callback = self.status_callback
        try:
            while blackboard.is_running and blackboard.current_step_index < self.MAX_STEPS:
                while blackboard.is_paused: await asyncio.sleep(0.5)
                gc.collect()
                blackboard.total_cost = self.architect.vision.total_cost
                pre_screenshot, marks = get_marked_screenshot()
                blackboard.last_screenshot = pre_screenshot
                blackboard.last_ui_tree = get_ui_tree()

                if not blackboard.plan:
                    await self.architect.plan(blackboard, self.memory, self.knowledge, project_context)

                # Swarm Parallelism: Check if multiple independent actions exist
                # Logic: If plan has multiple 'independent' actions at this stage
                # For demo, we just process one by one unless specially flagged
                current_actions = [blackboard.plan[blackboard.current_step_index]]

                # Execution
                if self.status_callback: self.status_callback("agent_active", "Executor")
                results = await asyncio.gather(*[self.execute_step_parallel(a, blackboard) for a in current_actions])

                # Verify (Post-action)
                if self.status_callback: self.status_callback("agent_active", "Auditor")
                post_screenshot, _ = get_marked_screenshot()
                diff_score = compute_visual_diff(pre_screenshot, post_screenshot)
                blackboard.last_screenshot = post_screenshot

                # Consensus verification for the batch
                verification = await self.auditor.verify(current_actions[0], blackboard)
                blackboard.add_history(current_actions[0], verification)

                if verification.get("success"):
                    blackboard.current_step_index += 1
                else:
                    await self.auditor.generate_correction_plan(verification, blackboard)
                    blackboard.plan = []

                if blackboard.current_step_index >= len(blackboard.plan) and len(blackboard.plan) > 0:
                    blackboard.status = "Completed"
                    lesson_strategy = await self.compressor.compress(blackboard.history)
                    LessonVault().add_lesson(blackboard.goal, lesson_strategy)
                    break
                await asyncio.sleep(0.5)

        except Exception as e: blackboard.error = str(e)
        finally:
            blackboard.is_running = False; blackboard.status = "Finished"
            self.reporter.generate_report(blackboard)
