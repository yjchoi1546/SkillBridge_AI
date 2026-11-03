from typing import Literal

from ...core.config import MAX_GENERATION_RETRIES
from .state import GenerationState


def route_after_validation(state: GenerationState) -> Literal["retry", "done"]:
    if state.get("errors") and state.get("attempts", 0) <= MAX_GENERATION_RETRIES:
        return "retry"
    return "done"
