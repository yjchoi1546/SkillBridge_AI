"""초안 조립 + 규칙 기반 필수 항목 검사. 실패하면 routers 가 design_project 로 되돌린다."""

from ....datagen import hidden_checks_from_spec
from ....schemas import EvaluationKey, ProjectDraft
from ....validation import check_draft
from ..state import GenerationState


async def validate_draft(state: GenerationState) -> dict:
    outline = state["outline"]
    draft = ProjectDraft(
        title=outline.title,
        summary=outline.summary,
        tasks=state["tasks"],
        dataset=state["dataset"],
        context=outline.context,
        rules=outline.rules,
        datasets=[state["dataset"]],
        data_notes=outline.data_notes,
    )
    # 숨은 함정은 datagen 이 실제로 심은 것만 적는다 (LLM 설명이 아니라 생성 설정에서 계산).
    # TODO(AI-A): A5 에서 auto 테스트 정답(answers)을 생성 데이터로 계산해 채운다.
    key = EvaluationKey(hidden_checks=hidden_checks_from_spec(state["dataset_spec"]))
    return {
        "draft": draft,
        "evaluation_key": key,
        "errors": check_draft(draft),
        "attempts": state.get("attempts", 0) + 1,
    }
