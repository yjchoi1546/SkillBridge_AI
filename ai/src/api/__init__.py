"""AI 영역의 유일한 공개 진입점. app/backend 는 여기만 import 한다.

    from ai.src.api import generate_project, ProjectRequest

호출 순서와 각 타입의 의미는 ai/CONTRACT.md 참고.
"""

from ..core.errors import AIError, ConfigError, GenerationError
from ..core.tracing import flush as flush_tracing
from . import schemas as _schemas
from .evaluation import evaluate_submission, generate_followup_questions
from .generation import ask_clarifying_questions, generate_project, revise_project
from .schemas import *  # noqa: F403

__all__ = [
    # 과제 생성
    "ask_clarifying_questions",
    "generate_project",
    "revise_project",
    # 제출물 평가
    "generate_followup_questions",
    "evaluate_submission",
    # 기타
    "flush_tracing",
    "AIError",
    "ConfigError",
    "GenerationError",
    *_schemas.__all__,
]
