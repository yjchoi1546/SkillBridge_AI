"""초안 조립 + 규칙 기반 필수 항목 검사. 실패하면 routers 가 design_project 로 되돌린다."""

from ....schemas import ProjectDraft
from ....validation import check_draft
from ..state import GenerationState


async def validate_draft(state: GenerationState) -> dict:
    outline = state["outline"]
    draft = ProjectDraft(
        title=outline.title,
        summary=outline.summary,
        tasks=state["tasks"],
        dataset=state["dataset"],
    )
    return {
        "draft": draft,
        "errors": check_draft(draft),
        "attempts": state.get("attempts", 0) + 1,
    }
