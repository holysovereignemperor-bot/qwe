import asyncio
import gc
import json
import os
import logging
from typing import List, Dict, Any
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
from checkpoint_manager import CheckpointManager
from task_decomposer import TaskDecomposer

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
        checkpoint_mgr: CheckpointManager = None,
        task_decomposer: TaskDecomposer = None,
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
        self.checkpoint = checkpoint_mgr or CheckpointManager()
        self.decomposer = task_decomposer
        self.overlay = GhostOverlay()
        self.MAX_STEPS = 50
        self.MAX_COST = 5.0
        self.MAX_CONSECUTIVE_FAILURES = 3
        self.CHECKPOINT_INTERVAL = 3
        self.history_dir = "logs/history"
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)

    def _compress_context(self, history: List[Dict[str, Any]], max_entries: int = 10) -> str:
        if len(history) <= max_entries:
            return json.dumps(history)
        recent = history[-max_entries:]
        summary = f"[{len(history) - max_entries} earlier steps omitted] "
        summary += json.dumps(recent)
        return summary

    def _save_checkpoint(self, blackboard: Blackboard, sub_goals=None, completed_sub_goals=None):
        self.checkpoint.save(blackboard.goal, {
            "step_index": blackboard.current_step_index,
            "plan": blackboard.plan,
            "history": blackboard.history[-20:],
            "data_bus": blackboard.data_bus,
            "status": blackboard.status,
            "sub_goals": sub_goals or [],
            "completed_sub_goals": completed_sub_goals or [],
            "total_cost": blackboard.total_cost,
        })

    def _restore_checkpoint(self, blackboard: Blackboard) -> bool:
        cp = self.checkpoint.load(blackboard.goal)
        if not cp:
            return False
        blackboard.current_step_index = cp["step_index"]
        blackboard.plan = cp.get("plan", [])
        blackboard.history = cp.get("history", [])
        blackboard.data_bus = cp.get("data_bus", {})
        blackboard.status = cp.get("status", "Resuming")
        self.vision.total_cost = cp.get("total_cost", 0.0)
        logger.info("Resumed from checkpoint at step %d", blackboard.current_step_index)
        return True

    async def _execute_parallel_skills(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        async def _run_skill(action):
            skill = self.registry.get(action.get("skill"))
            if skill:
                try:
                    return await skill.execute(action.get("params", {}))
                except Exception as e:
                    logger.error("Parallel skill '%s' failed: %s", action.get("skill"), e)
                    return {"status": "error", "error": str(e)}
            return {"status": "error", "error": f"Skill missing: {action.get('skill')}"}

        return await asyncio.gather(*[_run_skill(a) for a in actions])

    async def run(self, blackboard: Blackboard, project_context: str = ""):
        blackboard.gui_callback = self.status_callback
        consecutive_failures = 0

        restored = self._restore_checkpoint(blackboard)
        if restored:
            blackboard.status = "Resuming"
            logger.info("Continuing from checkpoint")

        try:
            while blackboard.is_running and blackboard.current_step_index < self.MAX_STEPS:
                while blackboard.is_paused:
                    await asyncio.sleep(0.5)

                gc.collect()
                blackboard.total_cost = self.vision.total_cost

                if blackboard.total_cost >= self.MAX_COST:
                    logger.warning("Budget limit reached: $%.4f", blackboard.total_cost)
                    blackboard.status = "Budget Exceeded"
                    break

                health = self.watchdog.check_health()
                if health.get("critical"):
                    logger.critical("System health critical: %s", health["reason"])
                    blackboard.status = "System Critical"
                    self._save_checkpoint(blackboard)
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
                        context_with_history = project_context
                        if blackboard.history:
                            context_with_history += f"\nRecent history: {self._compress_context(blackboard.history)}"

                        await self.architect.plan(
                            blackboard, self.memory, self.knowledge,
                            self.lesson_vault, context_with_history,
                        )
                    except Exception as e:
                        logger.error("Planning failed: %s", e)
                        blackboard.error = f"Planning error: {e}"
                        self._save_checkpoint(blackboard)
                        break

                if self.status_callback:
                    self.status_callback("agent_active", "Executor")

                try:
                    action = await self.executor.act(blackboard)
                except Exception as e:
                    logger.error("Executor failed: %s", e)
                    blackboard.add_history({"skill": "error"}, {"success": False, "observation": str(e)})
                    blackboard.current_step_index += 1
                    consecutive_failures += 1
                    if consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                        logger.warning("Too many consecutive failures (%d), replanning", consecutive_failures)
                        blackboard.plan = []
                        blackboard.correction_plan = f"Last {consecutive_failures} steps failed. Try a different approach."
                        consecutive_failures = 0
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
                    consecutive_failures = 0
                    logger.info("Step %d completed successfully", blackboard.current_step_index)
                else:
                    consecutive_failures += 1
                    logger.warning("Step %d failed (streak %d): %s",
                                   blackboard.current_step_index + 1,
                                   consecutive_failures,
                                   verification.get("observation"))

                    if consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                        logger.warning("Adaptive replan triggered after %d failures", consecutive_failures)
                        blackboard.plan = []
                        blackboard.correction_plan = (
                            f"Last {consecutive_failures} attempts failed. "
                            f"Observations: {verification.get('observation')}. "
                            "Use a completely different approach."
                        )
                        consecutive_failures = 0
                    else:
                        try:
                            await self.auditor.generate_correction_plan(verification, blackboard)
                        except Exception as e:
                            logger.error("Correction plan generation failed: %s", e)
                        blackboard.plan = []

                if blackboard.current_step_index % self.CHECKPOINT_INTERVAL == 0:
                    self._save_checkpoint(blackboard)

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
            self._save_checkpoint(blackboard)
        except Exception as e:
            logger.exception("Orchestration crashed: %s", e)
            blackboard.error = str(e)
            self._save_checkpoint(blackboard)
        finally:
            blackboard.is_running = False
            blackboard.status = blackboard.status if blackboard.status in ("Completed", "Cancelled", "Budget Exceeded", "System Critical") else "Finished"
            try:
                self.reporter.generate_report(blackboard)
            except Exception as e:
                logger.error("Report generation failed: %s", e)
            self.checkpoint.clear(blackboard.goal)
            logger.info("Orchestration ended with status: %s (provider: %s)",
                         blackboard.status, self.vision.llm.active_provider_name)

    async def run_complex(self, blackboard: Blackboard, project_context: str = ""):
        """Handles complex multi-goal tasks with decomposition and parallel execution."""
        if not self.decomposer:
            await self.run(blackboard, project_context)
            return

        sub_goals = await self.decomposer.decompose(blackboard.goal, project_context)
        if len(sub_goals) <= 1:
            await self.run(blackboard, project_context)
            return

        groups = self.decomposer.get_parallel_groups(sub_goals)
        completed = []

        logger.info("Complex task decomposed: %d sub-goals in %d groups", len(sub_goals), len(groups))
        blackboard.status = "Decomposed"

        for group_idx, group in enumerate(groups):
            if not blackboard.is_running:
                break

            if len(group) == 1:
                sg = group[0]
                sub_bb = Blackboard(sg["sub_goal"])
                sub_context = f"{project_context}\nCompleted so far: {json.dumps(completed)}"
                logger.info("Executing sub-goal %d/%d: %s", sg["id"], len(sub_goals), sg["sub_goal"][:60])

                await self.run(sub_bb, sub_context)

                completed.append({"id": sg["id"], "goal": sg["sub_goal"], "status": sub_bb.status})
                blackboard.total_cost = self.vision.total_cost
                blackboard.history.extend(sub_bb.history)
                blackboard.data_bus.update(sub_bb.data_bus)
            else:
                tasks = []
                sub_bbs = []
                for sg in group:
                    sub_bb = Blackboard(sg["sub_goal"])
                    sub_bbs.append((sg, sub_bb))
                    sub_context = f"{project_context}\nCompleted so far: {json.dumps(completed)}"
                    tasks.append(self.run(sub_bb, sub_context))

                logger.info("Executing %d sub-goals in parallel (group %d)", len(group), group_idx + 1)
                await asyncio.gather(*tasks)

                for sg, sub_bb in sub_bbs:
                    completed.append({"id": sg["id"], "goal": sg["sub_goal"], "status": sub_bb.status})
                    blackboard.history.extend(sub_bb.history)
                    blackboard.data_bus.update(sub_bb.data_bus)

                blackboard.total_cost = self.vision.total_cost

            self._save_checkpoint(blackboard, sub_goals, completed)

        all_ok = all(c["status"] in ("Completed", "Finished") for c in completed)
        blackboard.status = "Completed" if all_ok else "Partial"
        blackboard.is_running = False
        logger.info("Complex task finished: %d/%d sub-goals completed", len(completed), len(sub_goals))
