"""AI 영역 설정. 환경변수는 이 모듈에서만 읽는다.

키 목록은 루트 .env.example 참고. 실행 시 `uv run --env-file .env ...` 로 주입한다.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Literal

from .errors import ConfigError

Task = Literal["generation", "evaluation"]
StructuredMethod = Literal["json_schema", "function_calling", "json_mode"]


@dataclass(frozen=True)
class ProviderSpec:
    key_env: str  # API 키 환경변수
    model_env: str  # 모델 ID 환경변수
    langchain_provider: str  # init_chat_model 의 model_provider
    # OpenAI 호환 API(EXAONE 등)는 openai 클라이언트로 주소만 바꿔 부른다
    base_url_env: str | None = None
    default_base_url: str | None = None
    # 공급자별 고정 옵션 (init_chat_model 에 그대로 넘긴다)
    options: dict[str, Any] = field(default_factory=dict)
    # with_structured_output 방식. None = LangChain 기본값
    structured_method: StructuredMethod | None = None


PROVIDERS: dict[str, ProviderSpec] = {
    "openai": ProviderSpec("OPENAI_API_KEY", "OPENAI_MODEL", "openai"),
    "anthropic": ProviderSpec("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "anthropic"),
    "google_genai": ProviderSpec("GOOGLE_API_KEY", "GEMINI_MODEL", "google_genai"),
    # LG K-EXAONE (https://docs.exaone.ai) — OpenAI 호환 Chat Completions.
    # 항상 추론(thinking)하는 모델이라 추론 강도를 낮춰 속도·토큰을 아낀다 (기본값 max 는 너무 길다).
    # 무료 API 는 초·분·일 단위 호출 제한이 있어 429 재시도를 넉넉히 둔다.
    # 구조화 출력은 function_calling 이 가장 정확·빠르다 (2026-11-09 실측: json_schema 는 형식만 맞고
    # 내용이 엉뚱했고, json_mode 는 필드를 몰라 실패).
    "exaone": ProviderSpec(
        "EXAONE_API_KEY",
        "EXAONE_MODEL",
        "openai",
        base_url_env="EXAONE_BASE_URL",
        default_base_url="https://api.exaone.ai/v1",
        options={"use_responses_api": False, "max_retries": 6},
        structured_method="function_calling",
    ),
}

DEFAULT_PROVIDER = "anthropic"

# 키 없이 고정 응답을 돌려주는 개발·테스트용 공급자 (llms/fake.py)
FAKE_PROVIDER = "fake"


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    langchain_provider: str = ""
    # init_chat_model 에 넘길 추가 인자 (base_url, api_key, 공급자 옵션)
    kwargs: dict[str, Any] = field(default_factory=dict)
    structured_method: StructuredMethod | None = None


def _exaone_options() -> dict[str, Any]:
    effort = os.getenv("EXAONE_REASONING_EFFORT") or "low"
    if effort not in ("low", "high", "max"):
        raise ConfigError(f"EXAONE_REASONING_EFFORT 는 low/high/max 중 하나여야 합니다 (현재: {effort!r})")
    return {"reasoning_effort": effort}


def llm_settings(task: Task) -> LLMSettings:
    """작업별 LLM 설정. `{TASK}_LLM_PROVIDER` 가 비어 있으면 `LLM_PROVIDER` 를 쓴다."""
    provider = (
        os.getenv(f"{task.upper()}_LLM_PROVIDER")
        or os.getenv("LLM_PROVIDER")
        or DEFAULT_PROVIDER
    )
    if provider == FAKE_PROVIDER:
        return LLMSettings(provider=FAKE_PROVIDER, model=FAKE_PROVIDER)
    if provider not in PROVIDERS:
        raise ConfigError(
            f"지원하지 않는 LLM provider: {provider!r} (가능: {', '.join(PROVIDERS)}, {FAKE_PROVIDER})"
        )

    spec = PROVIDERS[provider]
    api_key = os.getenv(spec.key_env)
    if not api_key:
        raise ConfigError(f"{spec.key_env} 가 비어 있습니다 (provider={provider})")
    model = os.getenv(spec.model_env)
    if not model:
        raise ConfigError(f"{spec.model_env} 가 비어 있습니다 (provider={provider})")

    kwargs: dict[str, Any] = dict(spec.options)
    if spec.base_url_env:
        # OpenAI 호환 공급자: 키를 명시적으로 넘겨야 OPENAI_API_KEY 를 대신 읽지 않는다.
        kwargs["base_url"] = os.getenv(spec.base_url_env) or spec.default_base_url
        kwargs["api_key"] = api_key
    if provider == "exaone":
        kwargs |= _exaone_options()

    method = os.getenv(f"{provider.upper()}_STRUCTURED_METHOD") or spec.structured_method
    if method not in (None, "json_schema", "function_calling", "json_mode"):
        raise ConfigError(f"{provider.upper()}_STRUCTURED_METHOD 값이 잘못됐습니다: {method!r}")

    return LLMSettings(
        provider=provider,
        model=model,
        langchain_provider=spec.langchain_provider,
        kwargs=kwargs,
        structured_method=method,
    )


# Langfuse 트레이스 환경. 비어 있으면 development — 개발 중 트레이스가 운영 대시보드에 섞이지 않게.
TRACING_ENVIRONMENT = os.getenv("LANGFUSE_TRACING_ENVIRONMENT") or "development"

# 생성 그래프에서 검증 실패 시 재생성 최대 횟수
MAX_GENERATION_RETRIES = int(os.getenv("MAX_GENERATION_RETRIES", "2"))
