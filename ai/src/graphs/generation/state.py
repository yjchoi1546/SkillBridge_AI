from typing import TypedDict

from pydantic import BaseModel, Field

from ...datagen import DatasetSpec
from ...schemas import Difficulty, ProjectDraft, ProjectRequest, SampleDataset, TaskSpec


class ProblemAnalysis(BaseModel):
    """STEP 1 산출물."""

    problem: str = Field(description="요청에 숨은 실제 업무 문제")
    goals: list[str]
    constraints: list[str]
    required_skills: list[str]


class TaskOutline(BaseModel):
    """STEP 2 산출물 (평가 항목은 STEP 3 에서 붙는다)."""

    difficulty: Difficulty
    title: str
    goal: str
    scope: str
    steps: list[str]
    deliverables: list[str]
    skills: list[str]


class ProjectOutline(BaseModel):
    title: str
    summary: str
    tasks: list[TaskOutline]


class GenerationState(TypedDict, total=False):
    # 입력
    request: ProjectRequest
    previous_draft: ProjectDraft | None  # revise 시
    feedback: str | None  # revise 시 기업 코멘트

    # 노드 산출물
    analysis: ProblemAnalysis  # analyze_request
    outline: ProjectOutline  # design_project
    dataset_spec: DatasetSpec  # design_dataset
    dataset: SampleDataset  # design_dataset
    tasks: list[TaskSpec]  # design_evaluation
    draft: ProjectDraft  # validate_draft

    # 검증 루프
    errors: list[str]
    attempts: int
