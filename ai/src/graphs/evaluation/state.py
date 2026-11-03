from typing import TypedDict

from pydantic import BaseModel

from ...schemas import (
    CriterionVerdict,
    EvaluationReport,
    SampleDataset,
    Submission,
    TaskSpec,
    TestResult,
)


class ReviewDraft(BaseModel):
    """draft_review 의 LLM 출력."""

    ai_review: list[CriterionVerdict]
    ai_summary: str
    improvements: list[str]


class EvaluationState(TypedDict, total=False):
    # 입력
    task: TaskSpec
    dataset: SampleDataset
    submission: Submission

    # 노드 산출물
    format_errors: list[str]  # check_submission
    test_results: list[TestResult]  # run_tests
    review: ReviewDraft  # draft_review
    report: EvaluationReport  # build_report
