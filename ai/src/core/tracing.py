"""트레이싱 진입점. Langfuse 의존은 이 파일에만 둔다.

나중에 자체 모니터링(monitoring/sdk)으로 바꿔도 이 파일의 함수 시그니처만 유지하면 된다.

설정은 Langfuse SDK 가 환경변수에서 직접 읽는다 (.env.example 참고):
    LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY / LANGFUSE_BASE_URL
    LANGFUSE_TRACING_ENVIRONMENT (development / staging / production)
키가 비어 있으면 클라이언트가 스스로 비활성화되고, 앱은 트레이싱 없이 정상 동작한다.

트레이스 구조:
    generate-project | revise-project | evaluate-submission   (root, chain)
     └ generation-graph | evaluation-graph                    (LangGraph, CallbackHandler)
        └ analyze_request, design_project, ...                (노드)
           └ Chat* generation                                 (LLM 호출: 모델·토큰·비용)
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from langfuse import Langfuse, propagate_attributes
from langfuse.langchain import CallbackHandler

from .config import TRACING_ENVIRONMENT

# 기업 요청·참여자 제출물이 그대로 LLM 입력으로 들어가므로, 개인정보·키 형태는 전송 전에 가린다.
_MASKS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"\b01[016789][-. ]?\d{3,4}[-. ]?\d{4}\b"), "[PHONE]"),
    (re.compile(r"\b\d{6}[-]?[1-4]\d{6}\b"), "[RRN]"),
    (re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}"), "[SECRET]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"), "[SECRET]"),
]


def _mask_value(data: Any) -> Any:
    if isinstance(data, str):
        for pattern, repl in _MASKS:
            data = pattern.sub(repl, data)
        return data
    if isinstance(data, dict):
        return {k: _mask_value(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [_mask_value(v) for v in data]
    return data


def _mask(*, data: Any, **kwargs: Any) -> Any:
    return _mask_value(data)


@lru_cache(maxsize=1)
def _client() -> Langfuse:
    # 이 인스턴스가 싱글턴으로 등록되어 CallbackHandler 도 같은 mask 설정을 쓴다.
    return Langfuse(mask=_mask, environment=TRACING_ENVIRONMENT)


def langchain_callbacks() -> list:
    """LangGraph/LangChain ainvoke 의 config["callbacks"] 에 넣을 핸들러."""
    _client()
    return [CallbackHandler()]


class TraceRun:
    def __init__(self, span: Any):
        self._span = span

    def set_output(self, output: Any) -> None:
        self._span.update(output=output)


@contextmanager
def trace_run(
    name: str,
    *,
    input: Any,
    tags: list[str],
    user_id: str | None = None,
    session_id: str | None = None,
) -> Iterator[TraceRun]:
    """공개 API 1회 호출 = 트레이스 1개. 실패하면 root 에 ERROR 로 기록하고 예외는 그대로 올린다."""
    lf = _client()
    with lf.start_as_current_observation(name=name, as_type="chain", input=input) as span:
        with propagate_attributes(
            trace_name=name, tags=tags, user_id=user_id, session_id=session_id
        ):
            try:
                yield TraceRun(span)
            except Exception as e:
                span.update(level="ERROR", status_message=f"{type(e).__name__}: {e}")
                raise


def annotate(**metadata: Any) -> None:
    """현재 활성 span 에 메타데이터를 붙인다 (예: 재시도 횟수). 트레이싱이 꺼져 있으면 무시된다."""
    _client().update_current_span(metadata=metadata)


def flush() -> None:
    """스크립트·노트북처럼 짧게 끝나는 프로세스는 종료 전에 호출해야 트레이스가 전송된다."""
    _client().flush()
