import pytest
import asyncio
import os
import tempfile
from blackboard import Blackboard
from skills import (
    SkillRegistry, TerminalSkill, FileSystemSkill, ExecuteCodeSkill,
    ClickSkill, TypeSkill, TransferSkill, CLIFactorySkill,
)
from memory_vault import MemoryVault


class TestBlackboard:
    def test_initialization(self):
        bb = Blackboard("Test Goal")
        assert bb.goal == "Test Goal"
        assert bb.status == "Planning"
        assert bb.is_running is True
        assert bb.plan == []
        assert bb.history == []
        assert bb.data_bus == {}
        assert bb.total_cost == 0.0

    def test_add_history(self):
        bb = Blackboard("Goal")
        bb.add_history({"skill": "click"}, {"success": True})
        assert len(bb.history) == 1
        assert bb.history[0]["action"]["skill"] == "click"
        assert bb.history[0]["result"]["success"] is True
        assert "timestamp" in bb.history[0]

    def test_add_chat(self):
        bb = Blackboard("Goal")
        bb.add_chat("user", "hello")
        bb.add_chat("agent", "hi there")
        assert len(bb.chat_history) == 2
        assert bb.chat_history[0]["role"] == "user"
        assert bb.chat_history[1]["content"] == "hi there"

    def test_context_summary(self):
        bb = Blackboard("My Goal")
        summary = bb.get_context_summary()
        assert "My Goal" in summary

    def test_context_summary_with_plan(self):
        bb = Blackboard("My Goal")
        bb.plan = [{"step": 1}, {"step": 2}]
        summary = bb.get_context_summary()
        assert "1/2" in summary

    def test_to_dict(self):
        bb = Blackboard("Test")
        d = bb.to_dict()
        assert d["goal"] == "Test"
        assert d["status"] == "Planning"
        assert "runtime" in d
        assert "total_cost" in d


class TestTerminalSkill:
    @pytest.mark.asyncio
    async def test_guardrail_rm_rf(self):
        skill = TerminalSkill()
        result = await skill.execute({"cmd": "rm -rf /"})
        assert result["status"] == "blocked"
        assert "Security guardrail" in result["reason"]

    @pytest.mark.asyncio
    async def test_guardrail_sudo(self):
        skill = TerminalSkill()
        result = await skill.execute({"cmd": "sudo rm something"})
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_guardrail_mkfs(self):
        skill = TerminalSkill()
        result = await skill.execute({"cmd": "mkfs.ext4 /dev/sda1"})
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_guardrail_fork_bomb(self):
        skill = TerminalSkill()
        result = await skill.execute({"cmd": ":(){ :|:& };:"})
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_safe_command(self):
        skill = TerminalSkill()
        result = await skill.execute({"cmd": "echo hello"})
        assert result["status"] == "success"
        assert "hello" in result["stdout"]

    @pytest.mark.asyncio
    async def test_command_failure(self):
        skill = TerminalSkill()
        result = await skill.execute({"cmd": "ls /nonexistent_path_12345"})
        assert result["status"] == "success"
        assert result["returncode"] != 0


class TestFileSystemSkill:
    @pytest.mark.asyncio
    async def test_guardrail_traversal(self):
        skill = FileSystemSkill()
        result = await skill.execute({"action": "read", "path": "../../secret.txt"})
        assert result["status"] == "blocked"
        assert "Directory traversal" in result["reason"]

    @pytest.mark.asyncio
    async def test_no_path(self):
        skill = FileSystemSkill()
        result = await skill.execute({"action": "read"})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_read_file(self):
        skill = FileSystemSkill()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, dir='.') as f:
            f.write("test content")
            f.flush()
            name = os.path.basename(f.name)
        try:
            result = await skill.execute({"action": "read", "path": name})
            assert result["status"] == "success"
            assert result["content"] == "test content"
        finally:
            os.unlink(name)

    @pytest.mark.asyncio
    async def test_write_file(self):
        skill = FileSystemSkill()
        name = "test_write_tmp.txt"
        try:
            result = await skill.execute({"action": "write", "path": name, "content": "written"})
            assert result["status"] == "success"
            with open(name) as f:
                assert f.read() == "written"
        finally:
            if os.path.exists(name):
                os.unlink(name)


class TestExecuteCodeSkill:
    @pytest.mark.asyncio
    async def test_safe_code(self):
        skill = ExecuteCodeSkill()
        result = await skill.execute({"code": "x = 2 + 2\nprint(x)"})
        assert result["status"] == "success"
        assert "4" in result["stdout"]

    @pytest.mark.asyncio
    async def test_blocked_os_import(self):
        skill = ExecuteCodeSkill()
        result = await skill.execute({"code": "import os\nos.system('ls')"})
        assert result["status"] == "blocked"
        assert "os" in result["reason"]

    @pytest.mark.asyncio
    async def test_blocked_subprocess(self):
        skill = ExecuteCodeSkill()
        result = await skill.execute({"code": "import subprocess\nsubprocess.run(['ls'])"})
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_blocked_sys(self):
        skill = ExecuteCodeSkill()
        result = await skill.execute({"code": "import sys\nsys.exit(1)"})
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_blocked_dunder_import(self):
        skill = ExecuteCodeSkill()
        result = await skill.execute({"code": "__import__('os').system('ls')"})
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_blocked_eval(self):
        skill = ExecuteCodeSkill()
        result = await skill.execute({"code": "eval('1+1')"})
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_blocked_open(self):
        skill = ExecuteCodeSkill()
        result = await skill.execute({"code": "open('/etc/passwd').read()"})
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_no_code(self):
        skill = ExecuteCodeSkill()
        result = await skill.execute({"code": ""})
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_runtime_error_handled(self):
        skill = ExecuteCodeSkill()
        result = await skill.execute({"code": "1/0"})
        assert result["status"] == "error"
        assert "division by zero" in result["error"]


class TestTransferSkill:
    @pytest.mark.asyncio
    async def test_transfer(self):
        skill = TransferSkill()
        result = await skill.execute({"key": "data", "value": "test_value"})
        assert result["status"] == "success"
        assert result["bus_update"] == {"data": "test_value"}

    @pytest.mark.asyncio
    async def test_no_key(self):
        skill = TransferSkill()
        result = await skill.execute({"value": "something"})
        assert result["status"] == "error"


class TestMemoryVault:
    def test_init_and_save(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            mv = MemoryVault(db_path)
            mv.save_experience("test task", [{"action": "click"}], True)
            similar = mv.retrieve_similar("test")
            assert len(similar) == 1
            assert similar[0]["goal"] == "test task"
        finally:
            os.unlink(db_path)

    def test_update_existing(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            mv = MemoryVault(db_path)
            mv.save_experience("task", [{"a": 1}], True, 1.0)
            mv.save_experience("task", [{"a": 1}], True, 2.0)
            results = mv.retrieve_similar("task")
            assert len(results) == 1
            assert results[0]["usage"] == 2
        finally:
            os.unlink(db_path)

    def test_empty_query(self):
        mv = MemoryVault(":memory:")
        results = mv.retrieve_similar("")
        assert results == []

    def test_no_matches(self):
        mv = MemoryVault(":memory:")
        results = mv.retrieve_similar("nonexistent query")
        assert results == []


class TestSkillRegistry:
    def test_default_skills(self):
        registry = SkillRegistry()
        assert registry.get("click") is not None
        assert registry.get("command") is not None
        assert registry.get("execute_code") is not None
        assert registry.get("file") is not None

    def test_self_evolve_removed(self):
        registry = SkillRegistry()
        assert registry.get("self_evolve") is None

    def test_register_custom(self):
        registry = SkillRegistry()
        from skills import Skill
        class CustomSkill(Skill):
            async def execute(self, params):
                return {"status": "success"}
        registry.register("custom", CustomSkill())
        assert registry.get("custom") is not None

    def test_nonexistent(self):
        registry = SkillRegistry()
        assert registry.get("nonexistent") is None

    def test_list_skills(self):
        registry = SkillRegistry()
        skills = registry.list_skills()
        assert "click" in skills
        assert "command" in skills
        assert len(skills) >= 10
