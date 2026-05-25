import pytest
import os
import tempfile
import time
from checkpoint_manager import CheckpointManager
from task_decomposer import TaskDecomposer


class TestCheckpointManager:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CheckpointManager(tmpdir)
            cm.save("test goal", {
                "step_index": 5,
                "plan": [{"action": "click"}],
                "history": [],
                "data_bus": {"key": "value"},
                "status": "Executing",
            })
            cp = cm.load("test goal")
            assert cp is not None
            assert cp["step_index"] == 5
            assert cp["data_bus"]["key"] == "value"

    def test_load_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CheckpointManager(tmpdir)
            assert cm.load("nonexistent goal") is None

    def test_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CheckpointManager(tmpdir)
            cm.save("test", {"step_index": 1})
            cm.clear("test")
            assert cm.load("test") is None

    def test_list_checkpoints(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = CheckpointManager(tmpdir)
            cm.save("goal A", {"step_index": 1, "status": "Paused"})
            cm.save("goal B", {"step_index": 3, "status": "Executing"})
            cps = cm.list_checkpoints()
            assert len(cps) == 2
            goals = [c["goal"] for c in cps]
            assert "goal A" in goals
            assert "goal B" in goals


class TestTaskDecomposer:
    def test_parse_response_valid(self):
        from unittest.mock import MagicMock
        td = TaskDecomposer(MagicMock())
        result = td._parse_response('[{"id": 1, "sub_goal": "test", "parallel": false}]')
        assert len(result) == 1
        assert result[0]["sub_goal"] == "test"

    def test_parse_response_json_block(self):
        from unittest.mock import MagicMock
        td = TaskDecomposer(MagicMock())
        raw = '```json\n[{"id": 1, "sub_goal": "test"}]\n```'
        result = td._parse_response(raw)
        assert len(result) == 1

    def test_parse_response_invalid(self):
        from unittest.mock import MagicMock
        td = TaskDecomposer(MagicMock())
        result = td._parse_response("not json at all")
        assert result == []

    def test_parallel_groups_sequential(self):
        from unittest.mock import MagicMock
        td = TaskDecomposer(MagicMock())
        sub_goals = [
            {"id": 1, "sub_goal": "A", "parallel": False, "depends_on": []},
            {"id": 2, "sub_goal": "B", "parallel": False, "depends_on": [1]},
        ]
        groups = td.get_parallel_groups(sub_goals)
        assert len(groups) == 2

    def test_parallel_groups_parallel(self):
        from unittest.mock import MagicMock
        td = TaskDecomposer(MagicMock())
        sub_goals = [
            {"id": 1, "sub_goal": "A", "parallel": True, "depends_on": []},
            {"id": 2, "sub_goal": "B", "parallel": True, "depends_on": []},
            {"id": 3, "sub_goal": "C", "parallel": False, "depends_on": [1, 2]},
        ]
        groups = td.get_parallel_groups(sub_goals)
        assert len(groups[0]) == 2
        assert len(groups) >= 2
