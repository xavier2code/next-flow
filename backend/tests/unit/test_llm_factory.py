"""Unit tests for LLM factory function and Settings extension.

Tests cover AGNT-04: LLM integration via LangChain with OpenAI and Ollama providers.
"""

from unittest.mock import patch, MagicMock

import pytest

from app.core.config import Settings


class TestSettingsLLMFields:
    """Test that Settings has the required LLM configuration fields."""

    def test_settings_has_default_provider(self):
        settings = Settings()
        assert hasattr(settings, "default_provider")
        assert settings.default_provider == "openai"

    def test_settings_has_default_model(self):
        settings = Settings()
        assert hasattr(settings, "default_model")
        assert settings.default_model == "gpt-4o"

    def test_settings_has_openai_api_key(self):
        settings = Settings()
        assert hasattr(settings, "openai_api_key")
        assert settings.openai_api_key == ""

    def test_settings_has_ollama_base_url(self):
        settings = Settings()
        assert hasattr(settings, "ollama_base_url")
        assert settings.ollama_base_url == "http://localhost:11434"


class TestGetLLMFactory:
    """Test the get_llm factory function."""

    def test_get_llm_openai(self):
        """get_llm with provider='openai' returns ChatOpenAI with streaming=True."""
        from langchain_openai import ChatOpenAI

        from app.services.agent_engine.llm import get_llm

        with patch("app.services.agent_engine.llm.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            result = get_llm({"provider": "openai", "model": "gpt-4o"})

        assert isinstance(result, ChatOpenAI)
        assert result.streaming is True

    def test_get_llm_ollama(self):
        """get_llm with provider='ollama' returns ChatOllama instance."""
        from langchain_ollama import ChatOllama

        from app.services.agent_engine.llm import get_llm

        with patch("app.services.agent_engine.llm.settings") as mock_settings:
            mock_settings.ollama_base_url = "http://localhost:11434"
            result = get_llm({"provider": "ollama", "model": "llama3"})

        assert isinstance(result, ChatOllama)

    def test_get_llm_default_fallback(self):
        """get_llm(None) falls back to settings.default_provider and settings.default_model."""
        from langchain_openai import ChatOpenAI

        from app.services.agent_engine.llm import get_llm

        with patch("app.services.agent_engine.llm.settings") as mock_settings:
            mock_settings.default_provider = "openai"
            mock_settings.default_model = "gpt-4o"
            mock_settings.openai_api_key = "test-key"
            result = get_llm(None)

        assert isinstance(result, ChatOpenAI)

    def test_get_llm_empty_dict_fallback(self):
        """get_llm({}) falls back to settings defaults."""
        from langchain_openai import ChatOpenAI

        from app.services.agent_engine.llm import get_llm

        with patch("app.services.agent_engine.llm.settings") as mock_settings:
            mock_settings.default_provider = "openai"
            mock_settings.default_model = "gpt-4o"
            mock_settings.openai_api_key = "test-key"
            result = get_llm({})

        assert isinstance(result, ChatOpenAI)

    def test_get_llm_unknown_provider_raises(self):
        """get_llm with unknown provider raises ValueError."""
        from app.services.agent_engine.llm import get_llm

        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            get_llm({"provider": "unknown"})

    def test_get_llm_temperature_override(self):
        """get_llm config overrides temperature from the config dict."""
        from app.services.agent_engine.llm import get_llm

        with patch("app.services.agent_engine.llm.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            result = get_llm({"provider": "openai", "model": "gpt-4o", "temperature": 0.5})

        assert result.temperature == 0.5

    def test_get_llm_max_tokens_override(self):
        """get_llm config overrides max_tokens from the config dict."""
        from app.services.agent_engine.llm import get_llm

        with patch("app.services.agent_engine.llm.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            result = get_llm({"provider": "openai", "model": "gpt-4o", "max_tokens": 2048})

        assert result.max_tokens == 2048

    def test_get_llm_streaming_always_true(self):
        """All LLM instances created with streaming=True per D-10."""
        from app.services.agent_engine.llm import get_llm

        with patch("app.services.agent_engine.llm.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            result = get_llm({"provider": "openai", "model": "gpt-4o"})

        assert result.streaming is True
