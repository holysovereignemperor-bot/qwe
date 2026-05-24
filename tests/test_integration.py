import pytest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock
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
    orchestrator = Orchestrator(mock_vision, registry, memory)

    blackboard = Blackboard("test goal")

    # Mocking mac_utils to avoid actual OS calls
    import mac_utils
    mac_utils.capture_screen = MagicMock(return_value=b"fake_image")
    mac_utils.get_marked_screenshot = MagicMock(return_value=(b"fake_image", []))
    mac_utils.get_ui_tree = MagicMock(return_value={"role": "root"})
    mac_utils.get_window_metadata = MagicMock(return_value={"app": "test"})

    # Run loop for a short time
    task = asyncio.create_task(orchestrator.run(blackboard))
    await asyncio.sleep(0.5)
    blackboard.is_running = False # Stop it manually if it hasn't finished
    await task

    assert len(blackboard.history) > 0
    assert blackboard.status == "Finished"
    assert blackboard.total_cost > 0
