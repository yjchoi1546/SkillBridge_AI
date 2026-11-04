from ..core.tracing import trace_run
from ..graphs.generation import run_generation
from ..schemas import ProjectDraft, ProjectRequest


def _draft_output(draft: ProjectDraft) -> dict:
    # 샘플 CSV 본문은 커서 트레이스 출력에서 빼고 행 수만 남긴다.
    out = draft.model_dump(mode="json", exclude={"dataset": {"csv"}})
    out["dataset"]["rows"] = max(draft.dataset.csv.count("\n") - 1, 0)
    return out


async def generate_project(
    request: ProjectRequest,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
) -> ProjectDraft:
    """기업 업무 요청 → 과제 초안 (STEP 1~3).

    user_id: 기업 회원 ID, session_id: 프로젝트 ID 를 넘기면 트레이스가 프로젝트 단위로 묶인다.
    """
    with trace_run(
        "generate-project",
        input=request.model_dump(mode="json"),
        tags=["project-generation"],
        user_id=user_id,
        session_id=session_id,
    ) as run:
        draft = await run_generation(request)
        run.set_output(_draft_output(draft))
        return draft


async def revise_project(
    request: ProjectRequest,
    draft: ProjectDraft,
    feedback: str,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
) -> ProjectDraft:
    """기업의 [수정] 요청. 기존 초안과 코멘트를 반영해 다시 생성한다."""
    with trace_run(
        "revise-project",
        input={"request": request.model_dump(mode="json"), "feedback": feedback},
        tags=["project-generation", "revision"],
        user_id=user_id,
        session_id=session_id,
    ) as run:
        revised = await run_generation(request, previous_draft=draft, feedback=feedback)
        run.set_output(_draft_output(revised))
        return revised
