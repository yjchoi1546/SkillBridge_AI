from ..core.tracing import trace_run
from ..graphs.generation import run_generation
from ..schemas import (
    ClarifyingQuestion,
    GenerationResult,
    LeakReport,
    ProjectDraft,
    ProjectRequest,
)


def _request_input(request: ProjectRequest) -> dict:
    # 첨부 문서 원본은 트레이스에 남기지 않는다 (기업 기밀). 파일명·크기만.
    out = request.model_dump(mode="json", exclude={"documents"})
    out["documents"] = [
        {"filename": d.filename, "media_type": d.media_type, "bytes": len(d.content)}
        for d in request.documents
    ]
    return out


def _draft_output(draft: ProjectDraft) -> dict:
    # 샘플 CSV 본문은 커서 트레이스 출력에서 빼고 행 수만 남긴다.
    out = draft.model_dump(mode="json", exclude={"dataset": {"csv"}})
    out["dataset"]["rows"] = max(draft.dataset.csv.count("\n") - 1, 0)
    return out


def _result(draft: ProjectDraft) -> GenerationResult:
    # TODO(AI-A): 유출 검사 노드가 생기면 그래프 결과의 LeakReport 를 그대로 쓴다.
    return GenerationResult(draft=draft, leak_report=LeakReport(status="not_checked"))


async def ask_clarifying_questions(
    request: ProjectRequest,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
) -> list[ClarifyingQuestion]:
    """과제를 만들기 전, 요청에 부족한 정보를 기업에 되묻는다. 빈 리스트면 바로 generate_project.

    기업 답변은 request.clarifications 에 담아 generate_project 에 넘긴다.
    """
    with trace_run(
        "ask-clarifying-questions",
        input=_request_input(request),
        tags=["project-generation", "clarification"],
        user_id=user_id,
        session_id=session_id,
    ) as run:
        # TODO(AI-A): 구현 전까지는 "되물을 것 없음" 으로 응답해 app 흐름이 막히지 않게 한다.
        questions: list[ClarifyingQuestion] = []
        run.set_output([q.model_dump(mode="json") for q in questions])
        return questions


async def generate_project(
    request: ProjectRequest,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
) -> GenerationResult:
    """기업 업무 요청 → 과제 초안(공개본) + 유출 검사 결과(기업 전용).

    user_id: 기업 회원 ID, session_id: 프로젝트 ID 를 넘기면 트레이스가 프로젝트 단위로 묶인다.
    """
    with trace_run(
        "generate-project",
        input=_request_input(request),
        tags=["project-generation"],
        user_id=user_id,
        session_id=session_id,
    ) as run:
        draft = await run_generation(request)
        run.set_output(_draft_output(draft))
        return _result(draft)


async def revise_project(
    request: ProjectRequest,
    draft: ProjectDraft,
    feedback: str,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
) -> GenerationResult:
    """기업의 [수정] 요청. 기존 초안과 코멘트를 반영해 다시 생성한다."""
    with trace_run(
        "revise-project",
        input={"request": _request_input(request), "feedback": feedback},
        tags=["project-generation", "revision"],
        user_id=user_id,
        session_id=session_id,
    ) as run:
        revised = await run_generation(request, previous_draft=draft, feedback=feedback)
        run.set_output(_draft_output(revised))
        return _result(revised)
