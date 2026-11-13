"""시연 상황, 시작 가이드, 제출물·설계 문항, 평가 관점을 정한다."""

from ....llms import generate_structured
from ....prompts import load_prompt
from ..assembly import BASE_QUESTIONS
from ..context import data_summary, revision_parts, world_text
from ..state import GenerationState, ProjectFinish


async def finish_project(state: GenerationState) -> dict:
    docs = "\n".join(f"- {d.filename} [{d.kind}] {d.title}" for d in state["documents"])
    base_q = "\n".join(f"- {q.id} {q.title}: {' / '.join(q.prompts)}" for q in BASE_QUESTIONS)
    parts = [
        world_text(state["world"]),
        data_summary(state["data_plan"], state["data"], include_hidden=True),
        f"자료실 문서:\n{docs}",
        f"설계 설명 기본 문항 (id 그대로 쓰고 하위 질문만 이 과제에 맞게 다듬을 것):\n{base_q}",
        *revision_parts(state),
    ]
    finish = await generate_structured(
        "generation", ProjectFinish, load_prompt("generation/finish_project"), "\n\n".join(parts)
    )
    return {"finish": finish}
