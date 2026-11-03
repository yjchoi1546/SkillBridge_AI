"""LLM 호출 래퍼. 노드는 이 모듈만 쓰고, 공급자별 SDK 를 직접 import 하지 않는다.

공급자 교체는 .env 의 LLM_PROVIDER 만 바꾸면 된다. 공급자 패키지
(langchain-openai / langchain-anthropic / langchain-google-genai)는
init_chat_model 이 사용 시점에 import 하므로, 쓰는 것만 설치돼 있으면 된다.
"""

from functools import lru_cache
from typing import TypeVar

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from ..core.config import Task, llm_settings

T = TypeVar("T", bound=BaseModel)


@lru_cache(maxsize=None)
def get_chat_model(task: Task) -> BaseChatModel:
    # temperature 등 샘플링 파라미터는 넘기지 않는다 — 최신 Claude 모델은 400 을 반환한다.
    s = llm_settings(task)
    return init_chat_model(s.model, model_provider=s.provider)


async def generate_structured(task: Task, schema: type[T], system: str, user: str) -> T:
    """시스템/사용자 프롬프트로 호출해 `schema` 인스턴스를 받는다."""
    model = get_chat_model(task).with_structured_output(schema)
    return await model.ainvoke([("system", system), ("human", user)])
