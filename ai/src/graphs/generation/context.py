"""노드 프롬프트에 넣는 공통 문맥 (세계관, 자료 요약, 수정 요청)."""

from ...datagen import DataPlan, GeneratedData
from ...schemas import ProjectDraft
from .state import GenerationState, WorldPlan


def world_text(world: WorldPlan) -> str:
    return f"과제 세계관·문제·규칙:\n{world.model_dump_json(indent=2, exclude={'story'})}"


def data_summary(plan: DataPlan, data: GeneratedData, *, include_hidden: bool) -> str:
    """자료 요약. include_hidden 이면 비공개 사실을 '문서에 직접 쓰지 말 것' 표시와 함께 넣는다."""
    lines = ["자료 파일:"]
    for t, ds in zip(plan.tables, data.datasets):
        rows = max(ds.csv.count("\n") - 1, 0)
        lines.append(f"- {ds.filename} ({t.kind}, {rows}행): {t.description}")
        for c in t.columns:
            ref = f" → {c.ref}" if c.gen in ("ref", "lookup") and c.ref else ""
            lines.append(f"    - {c.name} ({c.dtype}{ref}): {c.description}")
    if data.public_notes:
        lines.append("공개된 데이터 한계:")
        lines += [f"- {n}" for n in data.public_notes]
    if include_hidden and data.hidden_checks:
        lines.append("데이터에 심은 사실 (비공개 — 문서·안내에 그대로 쓰지 말 것. 증상이나 다른 해석이 가능한 정황만 비칠 수 있다):")
        lines += [f"- {h.id} {h.title} ({h.location})" for h in data.hidden_checks]
    return "\n".join(lines)


def _previous_draft_text(draft: ProjectDraft) -> str:
    return draft.model_dump_json(
        indent=2,
        exclude={
            "tasks": True,
            "dataset": True,
            "datasets": {"__all__": {"csv"}},
            "documents": {"__all__": {"content"}},
        },
    )


def revision_parts(state: GenerationState, *, with_errors: bool = True) -> list[str]:
    parts: list[str] = []
    if state.get("previous_draft"):
        parts.append(f"기존 초안 (요청된 부분만 바꾸고 나머지는 유지):\n{_previous_draft_text(state['previous_draft'])}")
    if state.get("feedback"):
        parts.append(f"기업 수정 요청:\n{state['feedback']}")
    if with_errors and state.get("errors"):
        parts.append("직전 시도의 검증 오류 (반드시 해결):\n- " + "\n- ".join(state["errors"]))
    return parts
