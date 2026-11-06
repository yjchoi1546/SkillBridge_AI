"""ai ↔ app 계약 타입의 공개 경로. 정의는 ai/src/schemas.py 에 있다.

내부 모듈은 ai/src/schemas.py 를 직접 import 한다 (api 를 거치면 순환 import 가 생긴다).
app/backend 는 이 모듈(또는 ai.src.api)에서만 가져간다.
"""

from ..schemas import (
    Clarification,
    ClarifyingQuestion,
    CompanyDocument,
    CriterionVerdict,
    DatasetColumn,
    Difficulty,
    EvaluationReport,
    FollowupAnswer,
    FollowupQuestion,
    GenerationResult,
    LeakFinding,
    LeakReport,
    ProcessEntry,
    ProjectDraft,
    ProjectRequest,
    Reference,
    RubricItem,
    SampleDataset,
    Submission,
    TaskSpec,
    TestCase,
    TestResult,
)

__all__ = [
    "Clarification",
    "ClarifyingQuestion",
    "CompanyDocument",
    "CriterionVerdict",
    "DatasetColumn",
    "Difficulty",
    "EvaluationReport",
    "FollowupAnswer",
    "FollowupQuestion",
    "GenerationResult",
    "LeakFinding",
    "LeakReport",
    "ProcessEntry",
    "ProjectDraft",
    "ProjectRequest",
    "Reference",
    "RubricItem",
    "SampleDataset",
    "Submission",
    "TaskSpec",
    "TestCase",
    "TestResult",
]
