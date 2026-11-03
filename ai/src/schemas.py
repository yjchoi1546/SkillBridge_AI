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


class ProjectRequest(BaseModel):
    """기업의 업무 요청 (화면: /company/requests/new)."""

    request_text: str = Field(description="한두 문장 업무 요청")
    job_roles: list[str] = Field(default_factory=list, description="희망 직무 태그. 예: 데이터 분석")
    data_scope: Literal["synthetic_public", "deidentified", "company_tests"] = "synthetic_public"


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
    """AI 과제 초안 (화면: /company/projects/draft). 기업이 검토·수정·승인한다."""

    title: str
    summary: str
    tasks: list[TaskSpec] = Field(description="초급/중급/고급")
    dataset: SampleDataset


# ── 제출물 평가 ───────────────────────────────────────────


class Submission(BaseModel):
    """청년 참여자의 제출물. 파일 저장은 app 이 하고, 평가 시 내용만 넘긴다."""

    files: dict[str, str] = Field(description="파일명 -> 텍스트 내용")


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
