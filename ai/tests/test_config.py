"""설정·가짜 모드 동작."""

import pytest
from pydantic import BaseModel

from ai.src.core.config import llm_settings
from ai.src.core.errors import ConfigError
from ai.src.llms.fake import fake_response


def test_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ConfigError):
        llm_settings("generation")


def test_task_specific_provider_overrides_default(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    monkeypatch.setenv("GENERATION_LLM_PROVIDER", "fake")
    assert llm_settings("generation").provider == "fake"


def test_real_provider_without_key_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        llm_settings("generation")


def test_fake_mode_names_missing_schema():
    class BrandNewSchema(BaseModel):
        x: int

    with pytest.raises(ConfigError, match="BrandNewSchema"):
        fake_response(BrandNewSchema)


# ── EXAONE (OpenAI 호환) ──────────────────────────────────


@pytest.fixture
def exaone_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "exaone")
    monkeypatch.setenv("EXAONE_API_KEY", "test-exaone-key")
    monkeypatch.setenv("EXAONE_MODEL", "k-exaone_v2.5")
    for key in ("EXAONE_BASE_URL", "EXAONE_REASONING_EFFORT", "EXAONE_STRUCTURED_METHOD"):
        monkeypatch.delenv(key, raising=False)


def test_exaone_uses_openai_client_with_exaone_url(exaone_env):
    s = llm_settings("generation")
    assert s.langchain_provider == "openai"
    assert s.kwargs["base_url"] == "https://api.exaone.ai/v1"
    assert s.kwargs["api_key"] == "test-exaone-key"  # OPENAI_API_KEY 를 대신 읽지 않게
    assert s.kwargs["reasoning_effort"] == "low"
    assert s.kwargs["use_responses_api"] is False  # EXAONE 은 Chat Completions 만 지원
    assert s.structured_method == "function_calling"  # 실측상 가장 정확


def test_exaone_options_can_be_overridden(exaone_env, monkeypatch):
    monkeypatch.setenv("EXAONE_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("EXAONE_REASONING_EFFORT", "high")
    monkeypatch.setenv("EXAONE_STRUCTURED_METHOD", "json_mode")
    s = llm_settings("generation")
    assert s.kwargs["base_url"] == "https://example.test/v1"
    assert s.kwargs["reasoning_effort"] == "high"
    assert s.structured_method == "json_mode"


def test_exaone_rejects_bad_reasoning_effort(exaone_env, monkeypatch):
    monkeypatch.setenv("EXAONE_REASONING_EFFORT", "medium")
    with pytest.raises(ConfigError, match="EXAONE_REASONING_EFFORT"):
        llm_settings("generation")


def test_exaone_chat_model_builds_without_network(exaone_env):
    from ai.src.llms import get_chat_model

    get_chat_model.cache_clear()
    try:
        model = get_chat_model("generation")
        assert model.openai_api_base == "https://api.exaone.ai/v1"
        assert model.model_name == "k-exaone_v2.5"
        assert model.reasoning_effort == "low"
    finally:
        get_chat_model.cache_clear()
