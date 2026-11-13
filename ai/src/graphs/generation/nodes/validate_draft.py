"""초안 조립 + 규칙 검사 + 민감 단어 검사. 실패하면 routers 가 design_world 로 되돌린다."""

from ....schemas import EvaluationKey, ProjectDraft, SampleDataset
from ....validation import check_draft
from ..assembly import LEAK_PREFIX, check_leak, compat_tasks, merge_design_questions
from ..state import GenerationState

_EMPTY = SampleDataset(filename="empty.csv", columns=[], csv="", seed=0)


async def validate_draft(state: GenerationState) -> dict:
    world, data, finish = state["world"], state["data"], state["finish"]
    draft = ProjectDraft(
        title=world.title,
        summary=world.summary,
        domain_tags=world.domain_tags,
        skills=world.skills,
        estimated_effort=world.estimated_effort,
        context=world.context,
        problem=world.problem,
        rules=world.rules,
        datasets=data.datasets,
        dataset=data.datasets[0] if data.datasets else _EMPTY,
        documents=state["documents"],
        data_notes=[*data.public_notes, *finish.data_notes],
        required_demos=finish.required_demos,
        start_guide=finish.start_guide,
        deliverables=finish.deliverables,
        design_questions=merge_design_questions(finish.design_questions),
        review_criteria=finish.review_criteria,
        done_examples=finish.done_examples,
        not_done_examples=finish.not_done_examples,
        tests=finish.tests,
    )
    draft.tasks = compat_tasks(draft)

    leak = check_leak(draft, state["request"].sensitive_terms)
    errors = [*data.errors, *check_draft(draft)]
    # [leak] 오류는 재시도 사유가 되지만, 재시도 후에도 남으면 생성을 실패시키지 않고 LeakReport 로 기업에게 보여 준다.
    errors += [f"{LEAK_PREFIX} 민감 단어 '{f.text}' 가 공개본 {f.location} 에 있음 — 일반적인 표현으로 바꿀 것" for f in leak.findings]
    return {
        "draft": draft,
        "evaluation_key": EvaluationKey(hidden_checks=data.hidden_checks),
        "leak_report": leak,
        "errors": errors,
        "attempts": state.get("attempts", 0) + 1,
    }
