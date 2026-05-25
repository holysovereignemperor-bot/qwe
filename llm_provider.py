import os
import json
import time
import hashlib
import sqlite3
import asyncio
import socket
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Response Cache — shared by all providers
# ---------------------------------------------------------------------------

class ResponseCache:
    """SQLite-backed LRU cache for LLM responses, keyed by prompt hash."""

    def __init__(self, db_path: str = "knowledge/llm_cache.db", max_entries: int = 5000, ttl_seconds: int = 86400):
        self.db_path = db_path
        self.max_entries = max_entries
        self.ttl = ttl_seconds
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    response TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    hits INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON cache(created_at)")

    @staticmethod
    def _hash_key(prompt: str, system: str, model: str) -> str:
        raw = f"{model}::{system}::{prompt}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, prompt: str, system: str, model: str) -> Optional[str]:
        key = self._hash_key(prompt, system, model)
        cutoff = time.time() - self.ttl
        try:
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT response FROM cache WHERE key = ? AND created_at > ?",
                    (key, cutoff),
                ).fetchone()
                if row:
                    conn.execute("UPDATE cache SET hits = hits + 1 WHERE key = ?", (key,))
                    logger.debug("Cache HIT for key %s…", key[:12])
                    return row[0]
        except sqlite3.Error as e:
            logger.warning("Cache read error: %s", e)
        return None

    def put(self, prompt: str, system: str, model: str, response: str):
        key = self._hash_key(prompt, system, model)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, response, created_at, hits) VALUES (?, ?, ?, 0)",
                    (key, response, time.time()),
                )
                count = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
                if count > self.max_entries:
                    conn.execute(
                        "DELETE FROM cache WHERE key IN (SELECT key FROM cache ORDER BY created_at ASC LIMIT ?)",
                        (count - self.max_entries,),
                    )
        except sqlite3.Error as e:
            logger.warning("Cache write error: %s", e)


# ---------------------------------------------------------------------------
# Connectivity checker
# ---------------------------------------------------------------------------

def check_internet(host: str = "8.8.8.8", port: int = 53, timeout: float = 2.0) -> bool:
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False


def check_ollama(base_url: str = "http://localhost:11434", timeout: float = 2.0) -> bool:
    try:
        sock = socket.create_connection(
            (base_url.replace("http://", "").split(":")[0],
             int(base_url.rsplit(":", 1)[-1])),
            timeout=timeout,
        )
        sock.close()
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Abstract LLM provider
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def chat(self, messages: List[Dict[str, Any]], model: str, max_tokens: int = 500) -> Dict[str, Any]:
        """Returns {"content": str, "usage": {"prompt_tokens": int, "completion_tokens": int}}"""
        ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def supports_vision(self) -> bool: ...


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str = None):
        from openai import AsyncOpenAI
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._client = AsyncOpenAI(api_key=self._api_key) if self._api_key else None

    @property
    def name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(self._api_key) and check_internet()

    def supports_vision(self) -> bool:
        return True

    async def chat(self, messages: List[Dict[str, Any]], model: str = "gpt-4o-mini", max_tokens: int = 500) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError("OpenAI client not initialized (missing API key)")
        res = await self._client.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens)
        return {
            "content": res.choices[0].message.content,
            "usage": {
                "prompt_tokens": res.usage.prompt_tokens,
                "completion_tokens": res.usage.completion_tokens,
            },
        }


# ---------------------------------------------------------------------------
# Ollama provider (local LLM — offline)
# ---------------------------------------------------------------------------

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "llama3.2"):
        self.base_url = base_url
        self.default_model = default_model

    @property
    def name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        return check_ollama(self.base_url)

    def supports_vision(self) -> bool:
        return True

    async def chat(self, messages: List[Dict[str, Any]], model: str = None, max_tokens: int = 500) -> Dict[str, Any]:
        import aiohttp
        model = model or self.default_model
        text_messages = []
        images = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            text_parts.append(item["text"])
                        elif item.get("type") == "image_url":
                            url = item.get("image_url", {}).get("url", "")
                            if url.startswith("data:"):
                                b64_data = url.split(",", 1)[-1]
                                images.append(b64_data)
                content = "\n".join(text_parts)
            text_messages.append({"role": msg["role"], "content": content})

        payload = {"model": model, "messages": text_messages, "stream": False}
        if images:
            payload["images"] = images

        url = f"{self.base_url}/api/chat"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    data = await resp.json()
                    return {
                        "content": data.get("message", {}).get("content", ""),
                        "usage": {
                            "prompt_tokens": data.get("prompt_eval_count", 0),
                            "completion_tokens": data.get("eval_count", 0),
                        },
                    }
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e


# ---------------------------------------------------------------------------
# Resilient LLM Router — auto-failover + retry + cache
# ---------------------------------------------------------------------------

class LLMRouter:
    """Routes requests to best available LLM with retry, caching, and failover."""

    def __init__(
        self,
        providers: List[LLMProvider] = None,
        cache: ResponseCache = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        preferred: str = "openai",
    ):
        self.providers = providers or [OpenAIProvider(), OllamaProvider()]
        self.cache = cache or ResponseCache()
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.preferred = preferred
        self.total_cost = 0.0
        self._active_provider: Optional[LLMProvider] = None

    @property
    def active_provider_name(self) -> str:
        if self._active_provider:
            return self._active_provider.name
        return "none"

    def _select_provider(self, need_vision: bool = False) -> Optional[LLMProvider]:
        preferred_provider = None
        for p in self.providers:
            if p.name == self.preferred and p.is_available():
                if not need_vision or p.supports_vision():
                    preferred_provider = p
                    break

        if preferred_provider:
            return preferred_provider

        for p in self.providers:
            if p.is_available() and (not need_vision or p.supports_vision()):
                return p
        return None

    def _track_cost(self, usage: Dict[str, int], provider_name: str):
        if provider_name == "openai":
            cost = (usage.get("prompt_tokens", 0) * 0.00000015) + (usage.get("completion_tokens", 0) * 0.00000060)
            self.total_cost += cost
            logger.debug("API cost: $%.6f (total: $%.4f)", cost, self.total_cost)

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = "gpt-4o-mini",
        max_tokens: int = 500,
        use_cache: bool = True,
        need_vision: bool = False,
    ) -> str:
        prompt_text = ""
        system_text = ""
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text")
            if msg["role"] == "system":
                system_text = content
            else:
                prompt_text += content

        if use_cache:
            cached = self.cache.get(prompt_text, system_text, model)
            if cached is not None:
                return cached

        provider = self._select_provider(need_vision=need_vision)
        if not provider:
            raise RuntimeError("No LLM provider available (no internet + no local Ollama)")

        self._active_provider = provider
        last_error = None

        for attempt in range(self.max_retries):
            try:
                effective_model = model if provider.name == "openai" else None
                result = await provider.chat(messages, model=effective_model, max_tokens=max_tokens)
                content = result["content"]
                self._track_cost(result.get("usage", {}), provider.name)

                if use_cache and content:
                    self.cache.put(prompt_text, system_text, model, content)

                logger.debug("LLM response via %s (attempt %d)", provider.name, attempt + 1)
                return content

            except Exception as e:
                last_error = e
                delay = self.base_delay * (2 ** attempt)
                logger.warning("LLM call failed (attempt %d/%d via %s): %s. Retrying in %.1fs…",
                               attempt + 1, self.max_retries, provider.name, e, delay)
                await asyncio.sleep(delay)

                fallback = self._select_provider(need_vision=need_vision)
                if fallback and fallback.name != provider.name:
                    logger.info("Failing over from %s to %s", provider.name, fallback.name)
                    provider = fallback
                    self._active_provider = provider

        raise RuntimeError(f"All LLM retries exhausted. Last error: {last_error}")
