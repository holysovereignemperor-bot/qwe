import subprocess

class AppleScriptUtils:
    """Enhanced Templates for macOS Office Automation."""

    @staticmethod
    def run_script(script: str):
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=10)
            return {"status": "success" if result.returncode == 0 else "error", "stdout": result.stdout, "stderr": result.stderr}
        except Exception as e: return {"status": "error", "error": str(e)}

    @staticmethod
    def safari_open_url(url: str):
        return f'tell application "Safari" to make new document with properties {{URL:"{url}"}}'

    @staticmethod
    def mail_send_email(to: str, subject: str, body: str):
        return f'tell application "Mail" to make new outgoing message with properties {{subject:"{subject}", content:"{body}", visible:true}}'

    @staticmethod
    def calendar_create_event(title: str, start_date: str):
        # start_date format: "MM/DD/YYYY HH:MM:SS"
        return f'tell application "Calendar" to tell calendar "Work" to make new event with properties {{summary:"{title}", start date:date "{start_date}"}}'

    @staticmethod
    def notes_create_note(title: str, body: str):
        return f'tell application "Notes" to make new note with properties {{name:"{title}", body:"{body}"}}'
