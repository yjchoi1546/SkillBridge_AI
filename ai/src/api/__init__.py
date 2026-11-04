"""AI 영역의 유일한 공개 진입점. app/backend 는 여기만 import 한다.

    from ai.src.api import generate_project, ProjectRequest
"""

from ..core.errors import AIError, ConfigError, GenerationError
from ..core.tracing import flush as flush_tracing
from .evaluation import evaluate_submission
from .generation import generate_project, revise_project
from .schemas import (
    CriterionVerdict,
    DatasetColumn,
    Difficulty,
    EvaluationReport,
    ProjectDraft,
    ProjectRequest,
    RubricItem,
    SampleDataset,
    Submission,
    TaskSpec,
    TestCase,
    TestResult,
)

__all__ = [
    "generate_project",
    "revise_project",
    "evaluate_submission",
    "flush_tracing",
    "AIError",
    "ConfigError",
    "GenerationError",
    "CriterionVerdict",
    "DatasetColumn",
    "Difficulty",
    "EvaluationReport",
    "ProjectDraft",
    "ProjectRequest",
    "RubricItem",
    "SampleDataset",
    "Submission",
    "TaskSpec",
    "TestCase",
    "TestResult",
]
