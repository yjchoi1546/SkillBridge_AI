"""ai ↔ app 계약 타입 정의. app 에는 api/schemas.py 를 통해 공개된다.

여기 필드를 바꾸면 app 쪽이 깨진다 — 변경은 루트 CLAUDE.md "ai/ ↔ app/ 접점" 절차를 따른다.
AI 는 DB 를 모른다. 저장·ID 발급·상태(작성 중/검토 중/공개…) 관리는 app 이 한다.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# ── 과제 생성 입력 ─────────────────────────────────────────
# 기업 원문(요청·첨부 문서·민감 단어)은 기업 본인만 볼 수 있다. 개인 회원에게는 절대 내려보내지 않는다.


class CompanyDocument(BaseModel):
    """기업이 올린 첨부 문서 (개발규격서, 사업계획서 등). 텍스트 추출·목차 파악은 AI 가 한다."""

    filename: str = Field(description="예: 설비모니터링_규격서.pdf")
    media_type: str = Field(description="예: application/pdf, text/markdown")
    content: bytes = Field(description="파일 원본 바이트. 트레이스에는 남기지 않는다")


class Clarification(BaseModel):
    """AI 가 되물은 질문과 기업의 답변 (ask_clarifying_questions → 기업 답변 → 다시 요청에 첨부)."""

    question: str
    answer: str


class ProjectRequest(BaseModel):
    """기업의 업무 요청 (화면: /company/requests/new)."""

    request_text: str = Field(description="업무 요청 자유 서술. 한두 문장도, 긴 설명도 가능")
    job_roles: list[str] = Field(default_factory=list, description="희망 직무 태그. 예: 데이터 분석")
    data_scope: Literal["synthetic_public", "deidentified", "company_tests"] = "synthetic_public"
    documents: list[CompanyDocument] = Field(default_factory=list, description="첨부 문서")
    sensitive_terms: list[str] = Field(
        default_factory=list,
        description="공개 과제에 절대 나오면 안 되는 단어. 예: 회사명, 제품명, 내부 시스템명",
    )
    generalization: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="공개 과제 일반화 수준. low=고유명사만 치환, medium=업종까지 일반화, high=다른 도메인으로 이전",
    )
    clarifications: list[Clarification] = Field(default_factory=list)


class ClarifyingQuestion(BaseModel):
    """요청만으로 과제를 만들기에 정보가 부족할 때 AI 가 기업에 되묻는 질문."""

    id: str
    question: str
    reason: str = Field(description="왜 필요한지. 화면에 함께 보여준다")


# ── 과제 생성 출력 ─────────────────────────────────────────


class DatasetColumn(BaseModel):
    name: str
    dtype: Literal["string", "int", "float", "date", "bool"]
    description: str


class SampleDataset(BaseModel):
    filename: str = Field(description="예: sales_sample.csv")
    columns: list[DatasetColumn]
    csv: str = Field(description="CSV 본문. datagen 이 seed 고정으로 생성")
    seed: int


class RubricItem(BaseModel):
    criterion: str = Field(description="예: 집계 정확성")
    description: str
    auto_checkable: bool = Field(description="사전 정의 테스트로 판정 가능한지")


class TestCase(BaseModel):
    id: str
    description: str
    kind: Literal["auto", "manual"] = Field(description="auto=샌드박스 실행, manual=기업 확인 필요")


class TaskSpec(BaseModel):
    """난이도 하나의 과제 명세."""

    difficulty: Difficulty
    title: str
    goal: str
    scope: str
    steps: list[str]
    deliverables: list[str] = Field(description="예: 실행 코드, 결과 보고서")
    skills: list[str] = Field(description="기술 태그. 프로젝트 탐색 필터용")
    rubric: list[RubricItem]
    tests: list[TestCase]


class ProjectDraft(BaseModel):
    """AI 과제 초안 = 공개본 (화면: /company/projects/draft). 기업이 검토·수정·승인하면 개인에게 공개된다.

    원문의 회사명·고유명사·수치는 일반화되어 있어야 한다. 원문과 비교한 결과는 LeakReport 에 따로 둔다.
    """

    title: str
    summary: str
    domain_tags: list[str] = Field(
        default_factory=list, description="도메인 태그. 예: 제조, 금융. 개인 회원 탐색 필터용"
    )
    tasks: list[TaskSpec] = Field(description="초급/중급/고급")
    dataset: SampleDataset


class LeakFinding(BaseModel):
    text: str = Field(description="공개본에서 발견된 표현")
    location: str = Field(description="공개본 내 위치. 예: tasks[1].goal")
    source: Literal["sensitive_term", "proper_noun", "number", "llm"] = Field(
        description="무엇으로 잡았나: 기업 지정 민감 단어 / 원문 고유명사 / 원문 수치 / LLM 판단"
    )


class LeakReport(BaseModel):
    """공개본에 원문 민감 정보가 남았는지 검사한 결과. **기업 본인에게만** 보여준다."""

    status: Literal["passed", "failed", "not_checked"]
    findings: list[LeakFinding] = Field(default_factory=list)


class GenerationResult(BaseModel):
    """generate_project / revise_project 결과. draft 는 공개 가능, leak_report 는 기업 전용."""

    draft: ProjectDraft
    leak_report: LeakReport


# ── 제출물 평가 ───────────────────────────────────────────


class Reference(BaseModel):
    """참여자가 문제 해결에 사용한 자료."""

    kind: Literal["dataset", "document", "library", "other"]
    title: str
    url: str | None = None
    note: str = Field(default="", description="어디에 어떻게 썼는지")


class ProcessEntry(BaseModel):
    """해결 과정 기록 한 칸. 질문은 app 화면이 정한다 (권장 질문은 ai/CONTRACT.md)."""

    question: str = Field(description="예: 처음 세운 가설은?")
    answer: str


class FollowupQuestion(BaseModel):
    """제출물을 보고 AI 가 참여자에게 묻는 후속 질문 (본인이 직접 풀었는지 확인하는 구술 면접 역할)."""

    id: str
    question: str


class FollowupAnswer(BaseModel):
    question_id: str
    question: str
    answer: str


class Submission(BaseModel):
    """청년 참여자의 제출물. 파일 저장은 app 이 하고, 평가 시 내용만 넘긴다."""

    files: dict[str, str] = Field(description="파일명 -> 텍스트 내용")
    references: list[Reference] = Field(default_factory=list, description="사용한 자료·데이터 목록")
    process_log: list[ProcessEntry] = Field(default_factory=list, description="해결 과정 기록")
    ai_usage: str = Field(default="", description="AI 도구 사용 공개. 빈 문자열 = 사용 안 함")
    followup_answers: list[FollowupAnswer] = Field(default_factory=list)


class TestResult(BaseModel):
    test_id: str
    passed: bool | None = Field(description="None = 실행 안 함(manual 등)")
    detail: str = ""


class CriterionVerdict(BaseModel):
    criterion: str
    status: Literal["met", "not_met", "unverified"]
    comment: str


class EvaluationReport(BaseModel):
    """테스트 결과 + AI 평가 초안. 기업 피드백은 app 이 덧붙여 최종 리포트를 확정한다."""

    test_results: list[TestResult]
    ai_review: list[CriterionVerdict]
    ai_summary: str
    improvements: list[str] = Field(default_factory=list)
