import pytest
import os
import tempfile
import json
from secure_vault import SecureVault
from github_manager import GithubManager


class TestSecureVault:
    def test_create_vault(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = os.path.join(tmpdir, "vault.enc")
            key_path = os.path.join(tmpdir, "vault.key")
            vault = SecureVault(vault_path, key_path)
            assert os.path.exists(key_path)

    def test_set_and_get_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = SecureVault(
                os.path.join(tmpdir, "vault.enc"),
                os.path.join(tmpdir, "vault.key"),
            )
            vault.set_key("API_KEY", "sk-test-123")
            assert vault.get_key("API_KEY") == "sk-test-123"

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = os.path.join(tmpdir, "vault.enc")
            key_path = os.path.join(tmpdir, "vault.key")

            vault1 = SecureVault(vault_path, key_path)
            vault1.set_key("SECRET", "my_secret")

            vault2 = SecureVault(vault_path, key_path)
            assert vault2.get_key("SECRET") == "my_secret"

    def test_encrypted_file_not_plaintext(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = os.path.join(tmpdir, "vault.enc")
            key_path = os.path.join(tmpdir, "vault.key")
            vault = SecureVault(vault_path, key_path)
            vault.set_key("SECRET", "plaintext_value")

            with open(vault_path, "rb") as f:
                content = f.read()
            assert b"plaintext_value" not in content
            assert b"SECRET" not in content

    def test_delete_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = SecureVault(
                os.path.join(tmpdir, "vault.enc"),
                os.path.join(tmpdir, "vault.key"),
            )
            vault.set_key("TO_DELETE", "value")
            vault.delete_key("TO_DELETE")
            assert vault.get_key("TO_DELETE") is None

    def test_list_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = SecureVault(
                os.path.join(tmpdir, "vault.enc"),
                os.path.join(tmpdir, "vault.key"),
            )
            vault.set_key("KEY1", "val1")
            vault.set_key("KEY2", "val2")
            keys = vault.list_keys()
            assert "KEY1" in keys
            assert "KEY2" in keys

    def test_nonexistent_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = SecureVault(
                os.path.join(tmpdir, "vault.enc"),
                os.path.join(tmpdir, "vault.key"),
            )
            assert vault.get_key("MISSING") is None

    def test_key_file_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = os.path.join(tmpdir, "vault.key")
            vault = SecureVault(
                os.path.join(tmpdir, "vault.enc"),
                key_path,
            )
            mode = oct(os.stat(key_path).st_mode)[-3:]
            assert mode == "600"


class TestGithubManager:
    def test_protected_branch_push_blocked(self):
        gh = GithubManager(token="fake-token")
        result = gh.run_git(["push", "origin", "main"])
        assert result["status"] == "blocked"
        assert "main" in result["reason"]

    def test_protected_branch_master(self):
        gh = GithubManager(token="fake-token")
        result = gh.run_git(["push", "origin", "master"])
        assert result["status"] == "blocked"

    def test_sensitive_file_blocked(self):
        gh = GithubManager(token="fake-token")
        result = gh.run_git(["add", ".env"])
        assert result["status"] == "blocked"

    def test_sensitive_file_vault_key(self):
        gh = GithubManager(token="fake-token")
        result = gh.run_git(["add", "vault.key"])
        assert result["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_pr_no_token(self):
        gh = GithubManager(token=None)
        os.environ.pop("GITHUB_TOKEN", None)
        gh.token = None
        result = await gh.create_pull_request("owner/repo", "title", "feature")
        assert result["status"] == "error"
        assert "token" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_pr_missing_fields(self):
        gh = GithubManager(token="fake-token")
        result = await gh.create_pull_request(repo="", title="", head="")
        assert result["status"] == "error"
        assert "Missing" in result["error"]
