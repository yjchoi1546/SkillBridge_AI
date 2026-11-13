from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from ...datagen import DataPlan, GeneratedData
from ...schemas import (
    BusinessRule,
    DesignQuestion,
    EvaluationKey,
    InputSlot,
    LeakReport,
    MaterialDocument,
    ProblemStatement,
    ProjectContext,
    ProjectDraft,
    ProjectRequest,
    RubricItem,
    Scenario,
    StartGuide,
    TestCase,
)


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


class WorldPlan(BaseModel):
    """design_world 산출물: 가상 회사와 문제, 규칙, 데이터로 드러나야 할 이야기."""

    title: str
    summary: str = Field(description="과제 목록에 보일 두세 문장")
    domain_tags: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list, description="필요 역량 태그")
    estimated_effort: str = Field(default="", description="예: 1주, 하루 2~3시간")
    context: ProjectContext
    problem: ProblemStatement
    rules: list[BusinessRule]
    story: list[str] = Field(
        description="데이터로 드러나야 할 이야기 4~6개. 대상·기간·크기를 구체적으로. design_data 가 사실(FactPlan)로 심는다"
    )


class DocumentSet(BaseModel):
    """write_documents 산출물."""

    documents: list[MaterialDocument]


class ProjectFinish(BaseModel):
    """finish_project 산출물: 시연 상황, 시작 가이드, 제출·평가."""

    required_demos: list[Scenario]
    start_guide: StartGuide
    deliverables: list[str]
    design_questions: list[DesignQuestion]
    review_criteria: list[RubricItem]
    done_examples: list[str]
    not_done_examples: list[str]
    tests: list[TestCase] = Field(default_factory=list)
    data_notes: list[str] = Field(default_factory=list, description="참여자에게 미리 알리는 데이터 한계")


class GenerationState(TypedDict, total=False):
    # 입력
    request: ProjectRequest
    previous_draft: ProjectDraft | None  # revise 시
    feedback: str | None  # revise 시 기업 코멘트

    # 노드 산출물
    analysis: ProblemAnalysis  # analyze_request
    world: WorldPlan  # design_world
    data_plan: DataPlan  # design_data
    data: GeneratedData  # design_data (CSV·비공개 사실·공개 한계)
    documents: list[MaterialDocument]  # write_documents
    finish: ProjectFinish  # finish_project
    draft: ProjectDraft  # validate_draft
    evaluation_key: EvaluationKey  # validate_draft (기업·평가 전용)
    leak_report: LeakReport  # validate_draft (기업 전용)

    # 검증 루프
    errors: list[str]
    attempts: int
