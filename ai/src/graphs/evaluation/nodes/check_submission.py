"""제출물 형식 규칙 검사."""

from ....validation import check_submission as _check
from ..state import EvaluationState


async def check_submission(state: EvaluationState) -> dict:
    return {"format_errors": _check(state["task"], state["submission"])}
