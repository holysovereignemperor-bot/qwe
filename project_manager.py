import os
import subprocess
from typing import List, Dict, Any, Optional

class ProjectManager:
    """Detects active applications and automatically switches context."""
    def __init__(self, knowledge_manager=None):
        self.km = knowledge_manager
        self.last_app = None

    def get_active_app_metadata(self) -> Dict[str, Any]:
        """Returns metadata about the frontmost application using AppleScript/PyObjC."""
        try:
            # Using simple osascript for portability across modules,
            # though PyObjC NSWorkspace is more powerful.
            script = 'tell application "System Events" to get name of first process whose frontmost is true'
            app_name = subprocess.check_output(['osascript', '-e', script]).decode('utf-8').strip()
            return {"name": app_name}
        except Exception:
            return {"name": "Unknown"}

    def auto_switch_context(self) -> Optional[str]:
        """Detects if we should switch knowledge profiles based on active app."""
        meta = self.get_active_app_metadata()
        app_name = meta.get("name")

        if app_name != self.last_app:
            self.last_app = app_name
            # Strategy: If app name matches a profile name, auto-switch
            if self.km:
                profiles = self.km.list_profiles()
                if app_name in profiles:
                    return app_name
        return None

    def get_workspace_summary(self) -> str:
        meta = self.get_active_app_metadata()
        return f"Active Context: {meta.get('name')}\nWorking Directory: {os.getcwd()}\n"
