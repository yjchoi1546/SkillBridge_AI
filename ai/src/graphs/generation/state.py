from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from ...datagen import DatasetSpec
from ...schemas import Difficulty, ProjectDraft, ProjectRequest, SampleDataset, TaskSpec


InputSlot = Literal["problem", "decision_maker", "rules", "data_sources", "success_criteria"]
"""기업 입력 질문 5개 (docs/example_project.md ①): 막히는 업무 / 누가 무엇을 결정 / 판단 규칙 / 쓰는 데이터 / 성공 기준."""


class Rule(BaseModel):
    """업무 판단 규칙. 기업이 말하지 않은 규칙은 source="assumed" 로 구분한다."""

    text: str = Field(description="예: 전주 대비 순매출이 20% 이상 하락한 지점은 지역본부장에게 보고")
    source: Literal["company", "assumed"] = Field(
        description="company=요청·첨부·답변에 있는 규칙, assumed=AI 가 합리적으로 가정한 규칙"
    )
    evidence: str = Field(default="", description="company 면 근거가 된 원문 구절, assumed 면 가정한 이유")


class ProblemAnalysis(BaseModel):
    """STEP 1 산출물. 새 필드는 기본값이 있어 가짜 응답·이전 버전과 호환된다."""

    problem: str = Field(description="요청에 숨은 실제 업무 문제 (막히는 업무)")
    goals: list[str]
    constraints: list[str]
    required_skills: list[str]

    decision_maker: str = Field(default="", description="결과를 보고 무엇을 결정하는 사람·부서. 입력에 없으면 빈 문자열")
    rules: list[Rule] = Field(default_factory=list, description="판단 규칙")
    data_sources: list[str] = Field(default_factory=list, description="업무에 쓰는 데이터와 그 형태")
    data_issues: list[str] = Field(default_factory=list, description="데이터에서 자주 생기는 문제 (중복, 표기 변형, 누락 등)")
    success_criteria: list[str] = Field(default_factory=list, description="기업이 말한 성공 기준")
    missing: list[InputSlot] = Field(
        default_factory=list, description="입력 질문 5개 중 요청·첨부·답변에서 확인되지 않은 항목. 되묻기에 쓴다"
    )


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
