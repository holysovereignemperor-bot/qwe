import os
import base64
import json
from touch_id_gate import TouchIDGate

class SecureVault:
    """Local vault with TouchID biometric gate."""
    def __init__(self, vault_path="knowledge/vault.enc"):
        self.vault_path = vault_path
        self.keys = self._load_vault()
        self.gate = TouchIDGate()

    def _load_vault(self):
        if os.path.exists(self.vault_path):
            try:
                with open(self.vault_path, 'r') as f:
                    encoded = f.read()
                    return json.loads(base64.b64decode(encoded).decode('utf-8'))
            except Exception: return {}
        return {}

    def save_vault(self):
        encoded = base64.b64encode(json.dumps(self.keys).encode('utf-8')).decode('utf-8')
        with open(self.vault_path, 'w') as f: f.write(encoded)

    def set_key(self, key_name: str, value: str):
        if self.gate.authenticate(f"Store {key_name} in secure vault"):
            self.keys[key_name] = value
            self.save_vault()

    def get_key(self, key_name: str) -> str:
        if self.gate.authenticate(f"Retrieve {key_name} from secure vault"):
            return self.keys.get(key_name)
        return None
