import pytest
import asyncio
import json
import os
import tempfile
from unittest.mock import MagicMock, AsyncMock, patch
from orchestrator import Orchestrator
from blackboard import Blackboard
from skills import SkillRegistry
from memory_vault import MemoryVault
from knowledge_manager import KnowledgeManager
from lesson_vault import LessonVault


@pytest.fixture
def mock_vision():
    vision = MagicMock()
    vision.get_plan = AsyncMock(return_value=[{"action": "test", "description": "test step"}])
    vision.get_action = AsyncMock(return_value={"skill": "command", "params": {"cmd": "echo 'hello'"}})
    vision.verify_outcome = AsyncMock(return_value={"success": True, "observation": "it worked"})
    vision.total_cost = 0.01
    return vision


@pytest.fixture
def temp_lesson_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.mark.asyncio
async def test_full_orchestration_loop(mock_vision, temp_lesson_db):
    registry = SkillRegistry()
    memory = MemoryVault(":memory:")
    knowledge = MagicMock(spec=KnowledgeManager)
    knowledge.search_docs = MagicMock(return_value=[])
    lesson_vault = LessonVault(temp_lesson_db)

    orchestrator = Orchestrator(mock_vision, registry, memory, knowledge, lesson_vault=lesson_vault)
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
async def test_orchestrator_handles_planning_error(mock_vision, temp_lesson_db):
    mock_vision.get_plan = AsyncMock(side_effect=RuntimeError("API down"))
    registry = SkillRegistry()
    memory = MemoryVault(":memory:")
    knowledge = MagicMock(spec=KnowledgeManager)
    knowledge.search_docs = MagicMock(return_value=[])
    lesson_vault = LessonVault(temp_lesson_db)

    orchestrator = Orchestrator(mock_vision, registry, memory, knowledge, lesson_vault=lesson_vault)
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
async def test_orchestrator_handles_skill_not_found(mock_vision, temp_lesson_db):
    mock_vision.get_action = AsyncMock(return_value={"skill": "nonexistent_skill", "params": {}})
    mock_vision.verify_outcome = AsyncMock(return_value={"success": True, "observation": "ok"})
    registry = SkillRegistry()
    memory = MemoryVault(":memory:")
    knowledge = MagicMock(spec=KnowledgeManager)
    knowledge.search_docs = MagicMock(return_value=[])
    lesson_vault = LessonVault(temp_lesson_db)

    orchestrator = Orchestrator(mock_vision, registry, memory, knowledge, lesson_vault=lesson_vault)
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
async def test_budget_limit(mock_vision, temp_lesson_db):
    mock_vision.total_cost = 10.0  # Over budget
    registry = SkillRegistry()
    memory = MemoryVault(":memory:")
    knowledge = MagicMock(spec=KnowledgeManager)
    knowledge.search_docs = MagicMock(return_value=[])
    lesson_vault = LessonVault(temp_lesson_db)

    orchestrator = Orchestrator(mock_vision, registry, memory, knowledge, lesson_vault=lesson_vault)
    blackboard = Blackboard("test")
    blackboard.plan = [{"action": "test"}]

    with patch('orchestrator.get_marked_screenshot', return_value=(b"fake", [])), \
         patch('orchestrator.get_ui_tree', return_value={}), \
         patch('orchestrator.get_window_metadata', return_value={}), \
         patch('orchestrator.compute_visual_diff', return_value=0.0), \
         patch('orchestrator.gc.collect', MagicMock()):

        await orchestrator.run(blackboard)

    assert blackboard.status == "Budget Exceeded"
