"""AI 영역 설정. 환경변수는 이 모듈에서만 읽는다.

키 목록은 루트 .env.example 참고. 실행 시 `uv run --env-file .env ...` 로 주입한다.
"""

import os
from dataclasses import dataclass
from typing import Literal

from .errors import ConfigError

Task = Literal["generation", "evaluation"]

# provider(init_chat_model 의 model_provider 값) -> (API 키 환경변수, 모델 환경변수)
PROVIDERS: dict[str, tuple[str, str]] = {
    "openai": ("OPENAI_API_KEY", "OPENAI_MODEL"),
    "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
    "google_genai": ("GOOGLE_API_KEY", "GEMINI_MODEL"),
}

DEFAULT_PROVIDER = "anthropic"


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str


def llm_settings(task: Task) -> LLMSettings:
    """작업별 LLM 설정. `{TASK}_LLM_PROVIDER` 가 비어 있으면 `LLM_PROVIDER` 를 쓴다."""
    provider = (
        os.getenv(f"{task.upper()}_LLM_PROVIDER")
        or os.getenv("LLM_PROVIDER")
        or DEFAULT_PROVIDER
    )
    if provider not in PROVIDERS:
        raise ConfigError(f"지원하지 않는 LLM provider: {provider!r} (가능: {', '.join(PROVIDERS)})")

    key_env, model_env = PROVIDERS[provider]
    if not os.getenv(key_env):
        raise ConfigError(f"{key_env} 가 비어 있습니다 (provider={provider})")
    model = os.getenv(model_env)
    if not model:
        raise ConfigError(f"{model_env} 가 비어 있습니다 (provider={provider})")

    return LLMSettings(provider=provider, model=model)


# Langfuse 트레이스 환경. 비어 있으면 development — 개발 중 트레이스가 운영 대시보드에 섞이지 않게.
TRACING_ENVIRONMENT = os.getenv("LANGFUSE_TRACING_ENVIRONMENT") or "development"

# 생성 그래프에서 검증 실패 시 재생성 최대 횟수
MAX_GENERATION_RETRIES = int(os.getenv("MAX_GENERATION_RETRIES", "2"))
