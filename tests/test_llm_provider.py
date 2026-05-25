import pytest
import asyncio
import os
import tempfile
import time
from unittest.mock import MagicMock, AsyncMock, patch
from llm_provider import (
    ResponseCache, LLMRouter, OpenAIProvider, OllamaProvider,
    check_internet, check_ollama, LLMProvider,
)


class TestResponseCache:
    def test_put_and_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(os.path.join(tmpdir, "cache.db"))
            cache.put("hello", "system", "gpt-4o-mini", "world")
            result = cache.get("hello", "system", "gpt-4o-mini")
            assert result == "world"

    def test_cache_miss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(os.path.join(tmpdir, "cache.db"))
            result = cache.get("nonexistent", "", "model")
            assert result is None

    def test_different_prompts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(os.path.join(tmpdir, "cache.db"))
            cache.put("prompt1", "sys", "model", "response1")
            cache.put("prompt2", "sys", "model", "response2")
            assert cache.get("prompt1", "sys", "model") == "response1"
            assert cache.get("prompt2", "sys", "model") == "response2"

    def test_ttl_expiry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(os.path.join(tmpdir, "cache.db"), ttl_seconds=0)
            cache.put("prompt", "sys", "model", "response")
            time.sleep(0.1)
            result = cache.get("prompt", "sys", "model")
            assert result is None

    def test_max_entries_eviction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(os.path.join(tmpdir, "cache.db"), max_entries=3)
            for i in range(5):
                cache.put(f"prompt{i}", "sys", "model", f"response{i}")
            assert cache.get("prompt4", "sys", "model") == "response4"
            assert cache.get("prompt3", "sys", "model") == "response3"


class TestOpenAIProvider:
    def test_name(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            provider = OpenAIProvider(api_key="test-key")
            assert provider.name == "openai"

    def test_supports_vision(self):
        provider = OpenAIProvider(api_key="test-key")
        assert provider.supports_vision() is True

    def test_not_available_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            provider = OpenAIProvider(api_key="")
            assert provider.is_available() is False


class TestOllamaProvider:
    def test_name(self):
        provider = OllamaProvider()
        assert provider.name == "ollama"

    def test_supports_vision(self):
        provider = OllamaProvider()
        assert provider.supports_vision() is True


class MockProvider(LLMProvider):
    def __init__(self, name_val, available=True, vision=True, response="mock response"):
        self._name = name_val
        self._available = available
        self._vision = vision
        self._response = response

    @property
    def name(self):
        return self._name

    def is_available(self):
        return self._available

    def supports_vision(self):
        return self._vision

    async def chat(self, messages, model=None, max_tokens=500):
        return {
            "content": self._response,
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }


class TestLLMRouter:
    @pytest.mark.asyncio
    async def test_routes_to_preferred(self):
        p1 = MockProvider("openai", response="from openai")
        p2 = MockProvider("ollama", response="from ollama")
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(os.path.join(tmpdir, "cache.db"))
            router = LLMRouter(providers=[p1, p2], cache=cache, preferred="openai")
            result = await router.chat(
                [{"role": "user", "content": "test"}],
                use_cache=False,
            )
            assert result == "from openai"
            assert router.active_provider_name == "openai"

    @pytest.mark.asyncio
    async def test_failover(self):
        p1 = MockProvider("openai", available=False)
        p2 = MockProvider("ollama", response="fallback")
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(os.path.join(tmpdir, "cache.db"))
            router = LLMRouter(providers=[p1, p2], cache=cache, preferred="openai")
            result = await router.chat(
                [{"role": "user", "content": "test"}],
                use_cache=False,
            )
            assert result == "fallback"
            assert router.active_provider_name == "ollama"

    @pytest.mark.asyncio
    async def test_no_provider_raises(self):
        p1 = MockProvider("openai", available=False)
        p2 = MockProvider("ollama", available=False)
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(os.path.join(tmpdir, "cache.db"))
            router = LLMRouter(providers=[p1, p2], cache=cache)
            with pytest.raises(RuntimeError, match="No LLM provider available"):
                await router.chat([{"role": "user", "content": "test"}], use_cache=False)

    @pytest.mark.asyncio
    async def test_caching(self):
        call_count = 0

        class CountingProvider(MockProvider):
            async def chat(self, messages, model=None, max_tokens=500):
                nonlocal call_count
                call_count += 1
                return await super().chat(messages, model, max_tokens)

        p = CountingProvider("test", response="cached result")
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(os.path.join(tmpdir, "cache.db"))
            router = LLMRouter(providers=[p], cache=cache, preferred="test")
            r1 = await router.chat([{"role": "user", "content": "same prompt"}])
            r2 = await router.chat([{"role": "user", "content": "same prompt"}])
            assert r1 == r2 == "cached result"
            assert call_count == 1

    @pytest.mark.asyncio
    async def test_cost_tracking(self):
        p = MockProvider("openai")
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(os.path.join(tmpdir, "cache.db"))
            router = LLMRouter(providers=[p], cache=cache, preferred="openai")
            await router.chat([{"role": "user", "content": "test"}], use_cache=False)
            assert router.total_cost > 0
