import os
import json
import time
import logging
from blackboard import Blackboard

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates automated markdown summaries and audit logs."""

    def __init__(self, export_dir="exports"):
        self.export_dir = export_dir
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)

    def generate_report(self, blackboard: Blackboard):
        filename = f"task_{int(blackboard.start_time)}.md"
        path = os.path.join(self.export_dir, filename)

        report = f"""# OmniAgent Task Report
## Goal: {blackboard.goal}
- **Status**: {blackboard.status}
- **Total Cost**: ${blackboard.total_cost:.4f}
- **Runtime**: {time_format(time.time() - blackboard.start_time)}
- **Steps Completed**: {blackboard.current_step_index}/{len(blackboard.plan) if blackboard.plan else 0}

## Execution Log
"""
        for h in blackboard.history:
            action = h.get('action', {})
            res = h.get('result', {})
            report += f"### Step {h.get('step_index', 0) + 1}: {action.get('skill', 'unknown')}\n"
            report += f"- **Action**: {json.dumps(action.get('params'))}\n"
            report += f"- **Outcome**: {'Success' if res.get('success') else 'Failure'}\n"
            report += f"- **Observation**: {res.get('observation', 'N/A')}\n\n"

        if blackboard.error:
            report += f"## Error\n`{blackboard.error}`\n"

        try:
            with open(path, 'w') as f:
                f.write(report)
            logger.info("Report saved to %s", path)
        except Exception as e:
            logger.error("Failed to save report: %s", e)
        return path


def time_format(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}"
