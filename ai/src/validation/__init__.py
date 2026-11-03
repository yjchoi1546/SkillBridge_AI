"""LLM 없이 도는 규칙 기반 검증. 함수는 모두 에러 메시지 리스트를 반환한다 (빈 리스트 = 통과)."""

from .spec_rules import check_draft
from .submission_rules import check_submission

__all__ = ["check_draft", "check_submission"]
