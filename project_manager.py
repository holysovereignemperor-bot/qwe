import os
import subprocess
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ProjectManager:
    """Detects active applications and automatically switches context."""

    def __init__(self, knowledge_manager=None):
        self.km = knowledge_manager
        self.last_app = None

    def get_active_app_metadata(self) -> Dict[str, Any]:
        try:
            script = 'tell application "System Events" to get name of first process whose frontmost is true'
            app_name = subprocess.check_output(['osascript', '-e', script], timeout=5).decode('utf-8').strip()
            return {"name": app_name}
        except Exception:
            return {"name": "Unknown"}

    def auto_switch_context(self) -> Optional[str]:
        meta = self.get_active_app_metadata()
        app_name = meta.get("name")

        if app_name != self.last_app:
            self.last_app = app_name
            if self.km:
                profiles = self.km.list_profiles()
                if app_name in profiles:
                    logger.info("Auto-switching to profile: %s", app_name)
                    return app_name
        return None

    def get_workspace_summary(self) -> str:
        meta = self.get_active_app_metadata()
        return f"Active Context: {meta.get('name')}\nWorking Directory: {os.getcwd()}\n"
