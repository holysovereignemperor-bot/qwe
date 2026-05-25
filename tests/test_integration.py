import pytest
import asyncio
import json
import os
import tempfile
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from orchestrator import Orchestrator
from blackboard import Blackboard
from skills import SkillRegistry
from memory_vault import MemoryVault
from knowledge_manager import KnowledgeManager
from lesson_vault import LessonVault
from checkpoint_manager import CheckpointManager


class _MockLLM:
    def __init__(self, cost=0.01):
        self.total_cost = cost
        self.active_provider_name = "mock"


class _MockVision:
    def __init__(self, cost=0.01):
        self.llm = _MockLLM(cost)
        self.get_plan = AsyncMock(return_value=[{"action": "test", "description": "test step"}])
        self.get_action = AsyncMock(return_value={"skill": "command", "params": {"cmd": "echo 'hello'"}})
        self.verify_outcome = AsyncMock(return_value={"success": True, "observation": "it worked"})
        self._call_text = AsyncMock(return_value="lesson learned")
        self._call_vision = AsyncMock(return_value='{"success": true}')

    @property
    def total_cost(self):
        return self.llm.total_cost

    @total_cost.setter
    def total_cost(self, value):
        self.llm.total_cost = value


@pytest.fixture
def mock_vision():
    return _MockVision(cost=0.01)


@pytest.fixture
def temp_lesson_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def temp_checkpoint_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def _make_orchestrator(vision, lesson_path, checkpoint_dir):
    registry = SkillRegistry()
    memory = MemoryVault(":memory:")
    knowledge = MagicMock(spec=KnowledgeManager)
    knowledge.search_docs = MagicMock(return_value=[])
    lesson_vault = LessonVault(lesson_path)
    cp = CheckpointManager(checkpoint_dir)
    return Orchestrator(vision, registry, memory, knowledge, lesson_vault=lesson_vault, checkpoint_mgr=cp)


@pytest.mark.asyncio
async def test_full_orchestration_loop(mock_vision, temp_lesson_db, temp_checkpoint_dir):
    orchestrator = _make_orchestrator(mock_vision, temp_lesson_db, temp_checkpoint_dir)
    blackboard = Blackboard("test goal")
    blackboard.plan = [{"action": "test", "description": "test step"}]

    with patch('orchestrator.get_marked_screenshot', return_value=(b"fake_image", [])), \
         patch('orchestrator.get_ui_tree', return_value={"role": "root"}), \
         patch('orchestrator.get_window_metadata', return_value={"app": "test"}), \
         patch('orchestrator.compute_visual_diff', return_value=0.5), \
         patch('orchestrator.gc.collect', MagicMock()):

        task = asyncio.create_task(orchestrator.run(blackboard))
        await asyncio.sleep(1.5)
        blackboard.is_running = False
        await task

    assert len(blackboard.history) > 0
    assert blackboard.status in ("Completed", "Finished")


@pytest.mark.asyncio
async def test_orchestrator_handles_planning_error(mock_vision, temp_lesson_db, temp_checkpoint_dir):
    mock_vision.get_plan = AsyncMock(side_effect=RuntimeError("API down"))
    orchestrator = _make_orchestrator(mock_vision, temp_lesson_db, temp_checkpoint_dir)
    blackboard = Blackboard("test goal")

    with patch('orchestrator.get_marked_screenshot', return_value=(b"fake_image", [])), \
         patch('orchestrator.get_ui_tree', return_value={"role": "root"}), \
         patch('orchestrator.get_window_metadata', return_value={"app": "test"}), \
         patch('orchestrator.compute_visual_diff', return_value=0.0), \
         patch('orchestrator.gc.collect', MagicMock()):

        await orchestrator.run(blackboard)

    assert blackboard.error is not None
    assert "Planning error" in blackboard.error


@pytest.mark.asyncio
async def test_orchestrator_handles_skill_not_found(mock_vision, temp_lesson_db, temp_checkpoint_dir):
    mock_vision.get_action = AsyncMock(return_value={"skill": "nonexistent_skill", "params": {}})
    mock_vision.verify_outcome = AsyncMock(return_value={"success": True, "observation": "ok"})
    orchestrator = _make_orchestrator(mock_vision, temp_lesson_db, temp_checkpoint_dir)
    blackboard = Blackboard("test goal")
    blackboard.plan = [{"action": "test"}]

    with patch('orchestrator.get_marked_screenshot', return_value=(b"fake_image", [])), \
         patch('orchestrator.get_ui_tree', return_value={"role": "root"}), \
         patch('orchestrator.get_window_metadata', return_value={"app": "test"}), \
         patch('orchestrator.compute_visual_diff', return_value=0.0), \
         patch('orchestrator.gc.collect', MagicMock()):

        task = asyncio.create_task(orchestrator.run(blackboard))
        await asyncio.sleep(1.5)
        blackboard.is_running = False
        await task

    assert len(blackboard.history) > 0


@pytest.mark.asyncio
async def test_budget_limit(temp_lesson_db, temp_checkpoint_dir):
    mock_vision = _MockVision(cost=10.0)
    mock_vision.verify_outcome = AsyncMock(return_value={"success": False, "observation": "fail"})
    mock_vision._call_vision = AsyncMock(return_value="correction")
    orchestrator = _make_orchestrator(mock_vision, temp_lesson_db, temp_checkpoint_dir)
    blackboard = Blackboard("test")
    blackboard.plan = [{"action": "s1"}, {"action": "s2"}, {"action": "s3"}]

    with patch('orchestrator.get_marked_screenshot', return_value=(b"fake", [])), \
         patch('orchestrator.get_ui_tree', return_value={}), \
         patch('orchestrator.get_window_metadata', return_value={}), \
         patch('orchestrator.compute_visual_diff', return_value=0.0), \
         patch('orchestrator.gc.collect', MagicMock()):

        await orchestrator.run(blackboard)

    assert blackboard.status == "Budget Exceeded"


@pytest.mark.asyncio
async def test_adaptive_replan_on_consecutive_failures(temp_lesson_db, temp_checkpoint_dir):
    """Orchestrator sets correction_plan on first failure via auditor."""
    mock_vision = _MockVision(cost=0.01)
    mock_vision.verify_outcome = AsyncMock(return_value={"success": False, "observation": "failed"})
    mock_vision._call_vision = AsyncMock(return_value="try different approach")
    orchestrator = _make_orchestrator(mock_vision, temp_lesson_db, temp_checkpoint_dir)
    blackboard = Blackboard("test")
    blackboard.plan = [{"action": "step1"}, {"action": "step2"}]

    async def plan_that_stops(*args, **kwargs):
        raise RuntimeError("stop after replan")

    orchestrator.architect.plan = plan_that_stops

    with patch('orchestrator.get_marked_screenshot', return_value=(b"fake", [])), \
         patch('orchestrator.get_ui_tree', return_value={}), \
         patch('orchestrator.compute_visual_diff', return_value=0.0), \
         patch('orchestrator.gc.collect', MagicMock()):

        await orchestrator.run(blackboard)

    assert blackboard.correction_plan is not None
    assert len(blackboard.history) > 0
