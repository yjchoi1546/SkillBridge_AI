"""테스트 결과 + AI 평가 초안을 EvaluationReport 로 묶는다. 기업 피드백은 app 이 붙인다."""

from ....schemas import CriterionVerdict, EvaluationReport, TestResult
from ..state import EvaluationState


async def build_report(state: EvaluationState) -> dict:
    task = state["task"]

    if state.get("format_errors"):
        report = EvaluationReport(
            test_results=[
                TestResult(test_id=t.id, passed=None, detail="제출물 형식 미충족으로 실행 안 함")
                for t in task.tests
            ],
            ai_review=[
                CriterionVerdict(criterion=r.criterion, status="unverified", comment="평가 보류")
                for r in task.rubric
            ],
            ai_summary="제출물 형식 미충족: " + "; ".join(state["format_errors"]),
        )
        return {"report": report}

    review = state["review"]
    report = EvaluationReport(
        test_results=state["test_results"],
        ai_review=review.ai_review,
        ai_summary=review.ai_summary,
        improvements=review.improvements,
    )
    return {"report": report}
