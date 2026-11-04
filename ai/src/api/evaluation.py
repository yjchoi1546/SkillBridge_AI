from ..core.tracing import trace_run
from ..graphs.evaluation import run_evaluation
from ..schemas import EvaluationReport, SampleDataset, Submission, TaskSpec


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
        # 제출물 본문은 draft_review generation 입력에 남는다. root 에는 파일 목록만.
        input={
            "task": task.title,
            "difficulty": task.difficulty.value,
            "files": sorted(submission.files),
        },
        tags=["submission-evaluation"],
        user_id=user_id,
        session_id=session_id,
    ) as run:
        report = await run_evaluation(task, dataset, submission)
        run.set_output(report.model_dump(mode="json"))
        return report
