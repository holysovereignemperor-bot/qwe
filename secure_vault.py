import os
import subprocess
from touch_id_gate import TouchIDGate

class SecureVault:
    """Keychain-Integrated Secure Vault for macOS."""
    def __init__(self):
        self.gate = TouchIDGate()

    def set_key(self, key_name: str, value: str):
        if self.gate.authenticate(f"Store {key_name} in system keychain"):
            try:
                # Use macOS security CLI to add generic password
                cmd = ['security', 'add-generic-password', '-a', os.getlogin(), '-s', f"OmniAgent.{key_name}", '-w', value, '-U']
                subprocess.run(cmd, capture_output=True)
            except Exception as e: print(f"Keychain Error: {e}")

    def get_key(self, key_name: str) -> str:
        if self.gate.authenticate(f"Access {key_name} from system keychain"):
            try:
                cmd = ['security', 'find-generic-password', '-s', f"OmniAgent.{key_name}", '-w']
                val = subprocess.check_output(cmd).decode('utf-8').strip()
                return val
            except Exception: return None
        return None
