from ..core.tracing import trace_run
from ..graphs.evaluation import run_evaluation
from ..schemas import (
    EvaluationReport,
    FollowupQuestion,
    SampleDataset,
    Submission,
    TaskSpec,
)


def _submission_input(task: TaskSpec, submission: Submission) -> dict:
    # 제출물 본문은 LLM generation 입력에 남는다. root 에는 리뷰어가 볼 요약만.
    return {
        "task": task.title,
        "difficulty": task.difficulty.value,
        "files": sorted(submission.files),
        "references": len(submission.references),
        "process_entries": len(submission.process_log),
        "ai_usage_disclosed": bool(submission.ai_usage.strip()),
        "followup_answers": len(submission.followup_answers),
    }


async def generate_followup_questions(
    task: TaskSpec,
    submission: Submission,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
) -> list[FollowupQuestion]:
    """제출 직후, 제출물을 보고 참여자에게 물을 후속 질문을 만든다.

    참여자 답변은 submission.followup_answers 에 담아 evaluate_submission 에 넘긴다.
    """
    with trace_run(
        "generate-followup-questions",
        input=_submission_input(task, submission),
        tags=["submission-evaluation", "followup"],
        user_id=user_id,
        session_id=session_id,
    ) as run:
        # TODO(AI-B): 구현 전까지는 질문 없음으로 응답해 app 흐름이 막히지 않게 한다.
        questions: list[FollowupQuestion] = []
        run.set_output([q.model_dump(mode="json") for q in questions])
        return questions


async def evaluate_submission(
    task: TaskSpec,
    dataset: SampleDataset,
    submission: Submission,
    *,
    user_id: str | None = None,
    session_id: str | None = None,
) -> EvaluationReport:
    """제출물 → 테스트 결과 + AI 평가 초안 (STEP 4).

    user_id: 참여자 ID, session_id: 프로젝트 ID 를 넘기면 생성·수정·평가 트레이스가 한 세션으로 묶인다.
    """
    with trace_run(
        "evaluate-submission",
        input=_submission_input(task, submission),
        tags=["submission-evaluation"],
        user_id=user_id,
        session_id=session_id,
    ) as run:
        report = await run_evaluation(task, dataset, submission)
        run.set_output(report.model_dump(mode="json"))
        return report
