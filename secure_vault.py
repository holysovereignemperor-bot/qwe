import os
import json
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class SecureVault:
    """Local vault for API keys using Fernet symmetric encryption."""

    def __init__(self, vault_path="knowledge/vault.enc", key_path="knowledge/vault.key"):
        self.vault_path = vault_path
        self.key_path = key_path
        self._fernet = self._load_or_create_key()
        self.keys = self._load_vault()

    def _load_or_create_key(self) -> Fernet:
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
            fd = os.open(self.key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                os.write(fd, key)
            finally:
                os.close(fd)
            logger.info("Generated new encryption key at %s", self.key_path)
        return Fernet(key)

    def _load_vault(self):
        if os.path.exists(self.vault_path):
            try:
                with open(self.vault_path, "rb") as f:
                    encrypted = f.read()
                decrypted = self._fernet.decrypt(encrypted)
                return json.loads(decrypted.decode("utf-8"))
            except Exception:
                logger.warning("Failed to decrypt vault, starting fresh")
                return {}
        return {}

    def save_vault(self):
        plaintext = json.dumps(self.keys).encode("utf-8")
        encrypted = self._fernet.encrypt(plaintext)
        os.makedirs(os.path.dirname(self.vault_path), exist_ok=True)
        fd = os.open(self.vault_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, encrypted)
        finally:
            os.close(fd)

    def set_key(self, key_name: str, value: str):
        self.keys[key_name] = value
        self.save_vault()
        logger.info("Stored key: %s", key_name)

    def get_key(self, key_name: str) -> str:
        return self.keys.get(key_name)

    def delete_key(self, key_name: str):
        if key_name in self.keys:
            del self.keys[key_name]
            self.save_vault()
            logger.info("Deleted key: %s", key_name)

    def list_keys(self):
        return list(self.keys.keys())
