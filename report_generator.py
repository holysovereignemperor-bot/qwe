import os
import json
from blackboard import Blackboard

class ReportGenerator:
    """Generates automated markdown summaries and financial audit logs."""
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
- **Steps Completed**: {blackboard.current_step_index}/{len(blackboard.plan)}

## Execution Log
"""
        for h in blackboard.history:
            action = h['action']
            res = h['result']
            report += f"### Step {h['step_index'] + 1}: {action.get('skill')}\n"
            report += f"- **Action**: {json.dumps(action.get('params'))}\n"
            report += f"- **Outcome**: {'Success' if res.get('success') else 'Failure'}\n"
            report += f"- **Observation**: {res.get('observation')}\n\n"

        if blackboard.error:
            report += f"## Error\n`{blackboard.error}`\n"

        with open(path, 'w') as f:
            f.write(report)
        return path

def time_format(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}"
