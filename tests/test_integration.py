import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from orchestrator import Orchestrator
from blackboard import Blackboard
from skills import SkillRegistry
from memory_vault import MemoryVault

@pytest.fixture
def mock_vision():
    vision = MagicMock()
    vision.get_plan = AsyncMock(return_value=[{"action": "test", "description": "test step"}])
    vision.get_action = AsyncMock(return_value={"skill": "command", "params": {"cmd": "echo 'hello'"}})
    vision.verify_outcome = AsyncMock(return_value={"success": True, "observation": "it worked"})
    vision.total_cost = 0.01
    return vision

@pytest.mark.asyncio
async def test_full_orchestration_loop(mock_vision):
    registry = SkillRegistry()
    memory = MemoryVault(":memory:")
    knowledge = MagicMock()
    knowledge.search_docs = MagicMock(return_value=[])

    orchestrator = Orchestrator(mock_vision, registry, memory, knowledge)
    blackboard = Blackboard("test goal")
    blackboard.plan = [{"action": "test", "description": "test step"}]

    with patch('orchestrator.get_marked_screenshot', return_value=(b"fake_image", [])), \
         patch('orchestrator.get_ui_tree', return_value={"role": "root"}), \
         patch('orchestrator.get_window_metadata', return_value={"app": "test"}), \
         patch('orchestrator.open', MagicMock()), \
         patch('orchestrator.VoiceOS.speak', MagicMock()):

        task = asyncio.create_task(orchestrator.run(blackboard))
        await asyncio.sleep(0.5)
        blackboard.is_running = False
        await task

    assert len(blackboard.history) > 0
    assert blackboard.status == "Finished"
