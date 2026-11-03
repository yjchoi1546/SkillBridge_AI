from typing import Literal

from .state import EvaluationState


def route_after_check(state: EvaluationState) -> Literal["ok", "invalid"]:
    """형식 미충족이면 테스트·AI 평가를 건너뛰고 바로 리포트로."""
    return "invalid" if state.get("format_errors") else "ok"
