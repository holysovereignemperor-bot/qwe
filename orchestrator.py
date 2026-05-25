import asyncio
import gc
import json
import os
import logging
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

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        vision: VisionClient,
        registry: SkillRegistry,
        memory: MemoryVault,
        knowledge: KnowledgeManager,
        lesson_vault: LessonVault = None,
        behavior: BehaviorManager = None,
        watchdog: SystemWatchdog = None,
        doctor: SystemDoctor = None,
    ):
        self.vision = vision
        self.architect = ArchitectAgent(vision)
        self.executor = ExecutorAgent(vision)
        self.auditor = AuditorAgent(vision)
        self.registry = registry
        self.memory = memory
        self.knowledge = knowledge
        self.lesson_vault = lesson_vault or LessonVault()
        self.status_callback = None
        self.reporter = ReportGenerator()
        self.voice = VoiceOS()
        self.behavior = behavior or BehaviorManager()
        self.watchdog = watchdog or SystemWatchdog()
        self.doctor = doctor or SystemDoctor()
        self.compressor = MemoryCompressor(vision)
        self.overlay = GhostOverlay()
        self.MAX_STEPS = 50
        self.MAX_COST = 5.0
        self.history_dir = "logs/history"
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)

    async def run(self, blackboard: Blackboard, project_context: str = ""):
        blackboard.gui_callback = self.status_callback
        try:
            while blackboard.is_running and blackboard.current_step_index < self.MAX_STEPS:
                while blackboard.is_paused:
                    await asyncio.sleep(0.5)

                gc.collect()
                blackboard.total_cost = self.architect.vision.total_cost

                if blackboard.total_cost >= self.MAX_COST:
                    logger.warning("Budget limit reached: $%.4f", blackboard.total_cost)
                    blackboard.status = "Budget Exceeded"
                    break

                try:
                    pre_screenshot, marks = get_marked_screenshot()
                except OSError as e:
                    logger.error("Screenshot capture failed: %s", e)
                    pre_screenshot, marks = None, []

                blackboard.last_screenshot = pre_screenshot

                try:
                    blackboard.last_ui_tree = get_ui_tree()
                except OSError as e:
                    logger.error("UI tree extraction failed: %s", e)
                    blackboard.last_ui_tree = {"error": str(e)}

                if not blackboard.plan:
                    try:
                        await self.architect.plan(
                            blackboard, self.memory, self.knowledge,
                            self.lesson_vault, project_context,
                        )
                    except Exception as e:
                        logger.error("Planning failed: %s", e)
                        blackboard.error = f"Planning error: {e}"
                        break

                if self.status_callback:
                    self.status_callback("agent_active", "Executor")

                try:
                    action = await self.executor.act(blackboard)
                except Exception as e:
                    logger.error("Executor failed: %s", e)
                    blackboard.add_history({"skill": "error"}, {"success": False, "observation": str(e)})
                    blackboard.current_step_index += 1
                    continue

                skill = self.registry.get(action.get("skill"))
                if skill:
                    try:
                        res = await skill.execute(action.get("params", {}))
                        if "bus_update" in res:
                            blackboard.data_bus.update(res["bus_update"])
                    except Exception as e:
                        logger.error("Skill '%s' execution failed: %s", action.get("skill"), e)
                        res = {"status": "error", "error": str(e)}
                else:
                    logger.warning("Skill not found: %s", action.get("skill"))
                    res = {"status": "error", "error": f"Skill missing: {action.get('skill')}"}

                if self.status_callback:
                    self.status_callback("agent_active", "Auditor")

                try:
                    post_screenshot, _ = get_marked_screenshot()
                    diff_score = compute_visual_diff(pre_screenshot, post_screenshot)
                    blackboard.last_screenshot = post_screenshot
                except OSError:
                    diff_score = 0.0

                try:
                    verification = await self.auditor.verify(action, blackboard)
                except Exception as e:
                    logger.error("Verification failed: %s", e)
                    verification = {"success": False, "observation": str(e)}

                blackboard.add_history(action, verification)

                if verification.get("success"):
                    blackboard.current_step_index += 1
                    logger.info("Step %d completed successfully", blackboard.current_step_index)
                else:
                    logger.warning("Step %d failed: %s", blackboard.current_step_index + 1, verification.get("observation"))
                    try:
                        await self.auditor.generate_correction_plan(verification, blackboard)
                    except Exception as e:
                        logger.error("Correction plan generation failed: %s", e)
                    blackboard.plan = []

                if blackboard.current_step_index >= len(blackboard.plan) and len(blackboard.plan) > 0:
                    blackboard.status = "Completed"
                    try:
                        lesson_strategy = await self.compressor.compress(blackboard.history)
                        self.lesson_vault.add_lesson(blackboard.goal, lesson_strategy)
                    except Exception as e:
                        logger.error("Lesson compression failed: %s", e)
                    break

                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info("Orchestration cancelled")
            blackboard.status = "Cancelled"
        except Exception as e:
            logger.exception("Orchestration crashed: %s", e)
            blackboard.error = str(e)
        finally:
            blackboard.is_running = False
            blackboard.status = blackboard.status if blackboard.status in ("Completed", "Cancelled", "Budget Exceeded") else "Finished"
            try:
                self.reporter.generate_report(blackboard)
            except Exception as e:
                logger.error("Report generation failed: %s", e)
            logger.info("Orchestration ended with status: %s", blackboard.status)
