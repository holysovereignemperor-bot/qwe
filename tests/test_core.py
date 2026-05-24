import pytest
import asyncio
import os
from blackboard import Blackboard
from skills import SkillRegistry, TerminalSkill, FileSystemSkill
from memory_vault import MemoryVault

@pytest.mark.asyncio
async def test_blackboard_initialization():
    bb = Blackboard("Test Goal")
    assert bb.goal == "Test Goal"
    assert bb.status == "Planning"
    assert bb.is_running is True

@pytest.mark.asyncio
async def test_terminal_skill_guardrail():
    skill = TerminalSkill()
    result = await skill.execute({"cmd": "rm -rf /"})
    assert result["status"] == "blocked"
    assert "Security guardrail" in result["reason"]

@pytest.mark.asyncio
async def test_file_skill_guardrail():
    skill = FileSystemSkill()
    result = await skill.execute({"action": "read", "path": "../../secret.txt"})
    assert result["status"] == "blocked"
    assert "Directory traversal" in result["reason"]

def test_memory_vault():
    db_file = "test_memory.db"
    if os.path.exists(db_file):
        os.remove(db_file)
    mv = MemoryVault(db_file)
    mv.save_experience("test task", [{"action": "click"}], True)
    similar = mv.retrieve_similar("test")
    assert len(similar) == 1
    assert similar[0]["goal"] == "test task"
    if os.path.exists(db_file):
        os.remove(db_file)

def test_skill_registry():
    registry = SkillRegistry()
    assert registry.get("click") is not None
    assert registry.get("nonexistent") is None
