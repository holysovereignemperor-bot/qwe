import subprocess

class AppleScriptUtils:
    """Templates and runner for macOS AppleScript automation."""

    @staticmethod
    def run_script(script: str):
        try:
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=10)
            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def safari_open_url(url: str):
        return f'tell application "Safari" to make new document with properties {{URL:"{url}"}}'

    @staticmethod
    def mail_send_email(to: str, subject: str, body: str):
        return f'''
        tell application "Mail"
            set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{body}", visible:true}}
            tell newMessage
                make new recipient at end of recipients with properties {{address:"{to}"}}
                -- send -- Uncomment to actually send
            end tell
        end tell
        '''

    @staticmethod
    def notes_create_note(title: str, body: str):
        return f'tell application "Notes" to make new note with properties {{name:"{title}", body:"{body}"}}'
