"""테스트 공통 설정: LLM 은 가짜 모드, 트레이싱은 끈다. 키 없이 돈 안 들이고 돌아간다."""

import json
import os
from pathlib import Path

import pytest

# Langfuse 클라이언트가 만들어지기 전에 꺼야 하므로 import 시점에 설정한다.
os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
    os.environ.pop(key, None)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.delenv("GENERATION_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("EVALUATION_LLM_PROVIDER", raising=False)


@pytest.fixture
def sample_requests() -> list[dict]:
    lines = (FIXTURES / "requests.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]
