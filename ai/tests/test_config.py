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
