from ..core.tracing import trace_run
from ..graphs.evaluation import run_evaluation
from ..schemas import (
    EvaluationKey,
    EvaluationReport,
    FollowupQuestion,
    ProjectDraft,
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
    project: ProjectDraft | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> list[FollowupQuestion]:
    """제출 직후, 제출물을 보고 참여자에게 물을 후속 질문을 만든다.

    참여자 답변은 submission.followup_answers 에 담아 evaluate_submission 에 넘긴다.
    project: (v4) 과제 전체. App 은 v4 로 옮기면서 함께 넘긴다.
    """
    # TODO(AI-B): v4 — task 대신 project(자료실·설계 문항)와 submission.design_answers 로 질문을 만든다.
    _ = project
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
    project: ProjectDraft | None = None,
    evaluation_key: EvaluationKey | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> EvaluationReport:
    """제출물 → 테스트 결과 + AI 평가 초안 (STEP 4).

    evaluation_key: (v3) 생성 결과의 기업·평가 전용 정보(숨은 함정·정답). App 은 저장해 둔 것을 그대로 넘긴다.
    user_id: 참여자 ID, session_id: 프로젝트 ID 를 넘기면 생성·수정·평가 트레이스가 한 세션으로 묶인다.
    """
    # TODO(AI-B): evaluation_key 를 평가 그래프에 넘겨 run_tests(정답 비교)·draft_review(함정 확인)에 쓴다.
    # TODO(AI-B): v4 — project 가 오면 task·dataset 대신 과제 전체(review_criteria, required_demos,
    #             design_questions)와 submission.design_answers 로 평가한다.
    _ = (project, evaluation_key)
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
