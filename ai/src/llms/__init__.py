"""LLM 호출 래퍼. 노드는 이 모듈만 쓰고, 공급자별 SDK 를 직접 import 하지 않는다.

공급자 교체는 .env 의 LLM_PROVIDER 만 바꾸면 된다. 공급자 패키지
(langchain-openai / langchain-anthropic / langchain-google-genai)는
init_chat_model 이 사용 시점에 import 하므로, 쓰는 것만 설치돼 있으면 된다.
"""

from functools import lru_cache
from typing import TypeVar

from langchain.chat_models import init_chat_model
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, ValidationError

from ..core.config import FAKE_PROVIDER, Task, llm_settings
from .fake import fake_response

T = TypeVar("T", bound=BaseModel)


@lru_cache(maxsize=None)
def get_chat_model(task: Task) -> BaseChatModel:
    # temperature 등 샘플링 파라미터는 넘기지 않는다 — 최신 Claude 모델은 400 을 반환한다.
    # 공급자별 옵션(OpenAI 호환 주소, 추론 강도, 재시도)은 core/config.py 의 PROVIDERS 에서 온다.
    s = llm_settings(task)
    return init_chat_model(s.model, model_provider=s.langchain_provider, **s.kwargs)


async def generate_structured(task: Task, schema: type[T], system: str, user: str) -> T:
    """시스템/사용자 프롬프트로 호출해 `schema` 인스턴스를 받는다.

    LLM_PROVIDER=fake 면 LLM 을 부르지 않고 llms/fake.py 의 고정 응답을 돌려준다.
    """
    s = llm_settings(task)
    if s.provider == FAKE_PROVIDER:
        return fake_response(schema)
    kwargs = {"method": s.structured_method} if s.structured_method else {}
    model = get_chat_model(task).with_structured_output(schema, **kwargs)

    # 모델이 스키마를 어기는 경우가 있다 (예: EXAONE 이 list 필드를 "- a\n- b" 문자열로 채움).
    # 오류 내용을 알려주고 다시 묻는다. 그래도 안 되면 마지막 오류를 그대로 올린다.
    prompt = user
    for attempt in range(STRUCTURED_RETRIES + 1):
        try:
            return await model.ainvoke([("system", system), ("human", prompt)])
        except (ValidationError, OutputParserException) as e:
            if attempt == STRUCTURED_RETRIES:
                raise
            prompt = f"{user}\n\n{_FORMAT_RETRY_NOTE}\n{str(e)[:1500]}"
    raise AssertionError("unreachable")


# 구조화 출력이 스키마를 어겼을 때 재요청 횟수
STRUCTURED_RETRIES = 2

_FORMAT_RETRY_NOTE = (
    "[직전 응답 형식 오류] 아래 검증 오류를 고쳐 스키마에 정확히 맞게 다시 답하세요. "
    "목록(list) 필드는 글머리표 문자열이 아니라 배열로, 모든 필수 필드를 채우세요."
)
