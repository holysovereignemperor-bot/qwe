import pytest
import os
import json
import tempfile
from lesson_vault import LessonVault
from behavior_manager import BehaviorManager
from task_scheduler import TaskScheduler
from rule_manager import RuleManager
from report_generator import ReportGenerator, time_format
from blackboard import Blackboard
from macro_manager import MacroManager
from system_watchdog import SystemWatchdog
from knowledge_manager import KnowledgeManager
from plugin_system import PluginLoader
from skills import SkillRegistry


class TestLessonVault:
    def test_add_and_retrieve(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            lv = LessonVault(db_path)
            lv.add_lesson("python setup", "Use virtualenv and pip install")
            lessons = lv.get_lessons("python")
            assert len(lessons) == 1
            assert "virtualenv" in lessons[0]["strategy"]
        finally:
            os.unlink(db_path)

    def test_update_usage_count(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            lv = LessonVault(db_path)
            lv.add_lesson("deploy app", "Use docker compose")
            lv.add_lesson("deploy app", "Use docker compose")
            lessons = lv.get_lessons("deploy")
            assert len(lessons) == 1
        finally:
            os.unlink(db_path)

    def test_empty_goal(self):
        lv = LessonVault(":memory:")
        assert lv.get_lessons("") == []


class TestBehaviorManager:
    def test_default_preferences(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        os.unlink(path)
        try:
            bm = BehaviorManager(path)
            assert bm.data["preferences"]["ui_mode"] == "dark"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_add_macro(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        os.unlink(path)
        try:
            bm = BehaviorManager(path)
            bm.add_macro("open safari", [{"skill": "applescript"}])
            macro = bm.get_macro("open safari and search")
            assert macro is not None
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_no_macro(self):
        bm = BehaviorManager("/tmp/nonexistent_behavior_test.json")
        assert bm.get_macro("random unrelated goal") is None


class TestTaskScheduler:
    def test_add_and_get_pending(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            ts = TaskScheduler(path)
            ts.add_task("do something")
            pending = ts.get_pending()
            assert len(pending) == 1
            assert pending[0]["goal"] == "do something"
        finally:
            os.unlink(path)

    def test_mark_completed(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            ts = TaskScheduler(path)
            ts.add_task("task A")
            ts.mark_completed("task A")
            pending = ts.get_pending()
            assert len(pending) == 0
        finally:
            os.unlink(path)

    def test_future_task_not_pending(self):
        import time
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            ts = TaskScheduler(path)
            ts.add_task("future task", run_at=time.time() + 9999)
            pending = ts.get_pending()
            assert len(pending) == 0
        finally:
            os.unlink(path)


class TestRuleManager:
    def test_defaults(self):
        rm = RuleManager("/tmp/nonexistent_rules_test.json")
        ctx = rm.get_rules_context()
        assert "Senior Engineer" in ctx

    def test_update_rule(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            rm = RuleManager(path)
            rm.update_rule("persona", "Research Scientist")
            ctx = rm.get_rules_context()
            assert "Research Scientist" in ctx
        finally:
            os.unlink(path)


class TestReportGenerator:
    def test_generate_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rg = ReportGenerator(tmpdir)
            bb = Blackboard("Test Goal")
            bb.add_history({"skill": "click", "params": {"x": 100}}, {"success": True, "observation": "OK"})
            path = rg.generate_report(bb)
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert "Test Goal" in content
            assert "click" in content

    def test_time_format(self):
        assert time_format(0) == "0:00:00"
        assert time_format(61) == "0:01:01"
        assert time_format(3661) == "1:01:01"


class TestMacroManager:
    def test_save_and_get(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        os.unlink(path)
        try:
            mm = MacroManager(path)
            mm.save_macro("test goal", [{"action": "click"}])
            macro = mm.get_macro("test goal here")
            assert macro is not None
            assert macro[0]["action"] == "click"
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestSystemWatchdog:
    def test_check_health(self):
        sw = SystemWatchdog()
        status = sw.check_health()
        assert "ram" in status
        assert "disk" in status
        assert "critical" in status
        assert isinstance(status["ram"], float)


class TestKnowledgeManager:
    def test_profile_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KnowledgeManager(tmpdir)
            assert km.get_profile("nonexistent") is None

    def test_save_and_load_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KnowledgeManager(tmpdir)
            km.save_profile("test", {"key": "value"})
            profile = km.get_profile("test")
            assert profile["key"] == "value"

    def test_list_profiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            km = KnowledgeManager(tmpdir)
            km.save_profile("alpha", {"a": 1})
            km.save_profile("beta", {"b": 2})
            profiles = km.list_profiles()
            assert "alpha" in profiles
            assert "beta" in profiles


class TestPluginLoader:
    def test_load_example_plugin(self):
        registry = SkillRegistry()
        loader = PluginLoader(registry, "plugins")
        loader.load_plugins()
        skill = registry.get("hello_world")
        assert skill is not None
