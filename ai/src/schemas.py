"""ai ↔ app 계약 타입 정의. app 에는 api/schemas.py 를 통해 공개된다.

여기 필드를 바꾸면 app 쪽이 깨진다 — 변경은 루트 CLAUDE.md "ai/ ↔ app/ 접점" 절차를 따른다.
AI 는 DB 를 모른다. 저장·ID 발급·상태(작성 중/검토 중/공개…) 관리는 app 이 한다.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, JsonValue


class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


InputSlot = Literal["problem", "decision_maker", "rules", "data_sources", "success_criteria"]
"""기업 입력 질문 5개: 막히는 업무 / 누가 무엇을 결정 / 판단 규칙 / 쓰는 데이터 / 성공 기준."""


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


class CompanyIntake(BaseModel):
    """(v3) 기업 입력 질문 5개. 요청 화면의 질문별 입력칸. 빈 칸은 AI 가 되묻는다 (ClarifyingQuestion.slot)."""

    problem: str = Field(default="", description="어떤 업무가 막히나요? 지금 방식, 걸리는 시간, 자주 생기는 실수")
    decision_maker: str = Field(default="", description="결과를 보고 누가 무엇을 결정하나요?")
    rules: str = Field(default="", description="판단할 때 쓰는 규칙·기준은? 예: 전주 대비 20% 이상 하락 시 보고")
    data_sources: str = Field(default="", description="어떤 데이터를 쓰나요? 파일 종류, 주요 항목, 자주 생기는 문제")
    success_criteria: str = Field(default="", description="어떻게 되면 성공인가요? 마감, 정확도 등")


class ProjectRequest(BaseModel):
    """기업의 업무 요청 (화면: /company/requests/new)."""

    request_text: str = Field(description="업무 요청 자유 서술. 한두 문장도, 긴 설명도 가능")
    intake: CompanyIntake = Field(default_factory=CompanyIntake, description="(v3) 질문 5개 답변. 비워도 된다")
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
    slot: InputSlot | None = Field(default=None, description="(v3) 질문 5개 중 어느 빈 칸을 채우는 질문인지")


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
    description: str = Field(default="", description="(v3) 파일 설명. 예: 조건 변경 시나리오에서만 쓰는 정정본")


class RubricItem(BaseModel):
    criterion: str = Field(description="예: 집계 정확성")
    description: str
    auto_checkable: bool = Field(description="사전 정의 테스트로 판정 가능한지")


class TestCase(BaseModel):
    id: str
    description: str
    kind: Literal["auto", "manual"] = Field(description="auto=샌드박스 실행, manual=기업 확인 필요")


class Scenario(BaseModel):
    """(v3) 과제 하나의 시나리오. 난이도마다 normal / changed / exception 을 하나씩 둔다."""

    kind: Literal["normal", "changed", "exception"] = Field(
        description="normal=정상, changed=조건 변경(정정 데이터·기준 변경), exception=정보 부족·거절"
    )
    situation: str = Field(description="상황. 예: W13 매출 정정본이 도착")
    expected: str = Field(description="기대 동작. 예: 다시 계산하고 판정이 바뀐 지점과 이유를 표시")


class TaskSpec(BaseModel):
    """난이도 하나의 과제 명세. 공개본에 그대로 들어가므로 정답·숨은 함정을 넣지 않는다."""

    difficulty: Difficulty
    title: str
    goal: str
    scope: str
    steps: list[str]
    deliverables: list[str] = Field(description="예: 실행 코드, 결과 보고서")
    skills: list[str] = Field(description="기술 태그. 프로젝트 탐색 필터용")
    rubric: list[RubricItem]
    tests: list[TestCase]
    scenarios: list[Scenario] = Field(default_factory=list, description="(v3) 정상 / 조건 변경 / 예외 시나리오")
    done_examples: list[str] = Field(default_factory=list, description="(v3) 이러면 완성. 예: 다시 돌리면 같은 표가 나온다")
    not_done_examples: list[str] = Field(default_factory=list, description="(v3) 이러면 미완성. 예: 손으로 고친 표만 있다")


class Department(BaseModel):
    """(v3) 가상 회사의 부서·사람."""

    name: str = Field(description="예: 지역본부장 (결정권자)")
    goal: str
    constraint: str = ""


class ProjectContext(BaseModel):
    """(v3) 가상 회사 세계관. 실제 회사와 무관하게 AI 가 지어낸 설정이다."""

    company: str = Field(description="예: 온새리빙 (가상 기업) — 생활용품 오프라인 매장 체인")
    reference_date: str = Field(description="기준일('오늘'). 예: 2026-04-06(월) 09:00 — 직전 주 보고서를 만드는 시점")
    background: str = Field(description="핵심 문제. 보고가 늦거나 틀리면 무엇이 밀리는지")
    facts: list[str] = Field(default_factory=list, description="지점 수, 데이터 기간, 금액 단위 등")
    departments: list[Department] = Field(default_factory=list)


class BusinessRule(BaseModel):
    """(v3) 업무 판단 규칙. 기업이 말하지 않은 규칙은 source="assumed" 로 표시해 화면에 (가정) 배지를 단다."""

    id: str = Field(description="예: R1")
    text: str = Field(description="예: 전주 대비 순매출 20% 이상 하락 지점은 본부장 보고 대상")
    source: Literal["company", "assumed"] = Field(description="company=기업 제공, assumed=AI 가정 (기업 확인 필요)")
    note: str = Field(default="", description="assumed 면 가정한 이유")


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
    dataset: SampleDataset = Field(description="주 데이터 파일. datasets[0] 과 같다 (v3 에서 datasets 로 옮겨 가는 중)")
    context: ProjectContext | None = Field(default=None, description="(v3) 가상 회사 세계관")
    rules: list[BusinessRule] = Field(default_factory=list, description="(v3) 업무 규칙과 출처")
    datasets: list[SampleDataset] = Field(default_factory=list, description="(v3) 데이터 파일 전체. 첫 번째 = dataset")
    data_notes: list[str] = Field(
        default_factory=list, description="(v3) 참여자에게 미리 알리는 데이터 한계. 숨은 함정은 여기 쓰지 않는다"
    )


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


class HiddenCheck(BaseModel):
    """(v3) 참여자에게 알리지 않는 데이터 함정. seed 로 위치가 고정되어 정답을 재현할 수 있다."""

    id: str = Field(description="예: H1")
    title: str = Field(description="예: POS 재전송으로 같은 행 중복")
    location: str = Field(description="어디에 심었는지. 예: sales_daily.csv, 2026-03-31, 3개 지점")
    how_to_check: str = Field(description="참여자가 잡았는지 확인하는 방법")
    test_ids: list[str] = Field(default_factory=list, description="이 함정을 확인하는 TestCase.id")


class TestAnswer(BaseModel):
    """(v3) auto 테스트의 정답. 생성 데이터로 미리 계산한다. 비교 방법은 AI-B 샌드박스가 정한다."""

    test_id: str
    expected: JsonValue = Field(description="정답 값. 숫자, 문자열, 목록, 표(행 목록) 등")
    tolerance: float = Field(default=0.0, description="숫자 비교 허용 오차")
    note: str = ""


class EvaluationKey(BaseModel):
    """(v3) 기업·평가 전용 정보. **개인 회원에게 절대 보내지 않는다** (LeakReport 와 같은 권한).

    App 은 생성 결과에서 받아 비공개로 저장하고, 평가할 때 evaluate_submission 에 그대로 넘긴다.
    """

    hidden_checks: list[HiddenCheck] = Field(default_factory=list)
    answers: list[TestAnswer] = Field(default_factory=list)


class GenerationResult(BaseModel):
    """generate_project / revise_project 결과. draft 는 공개 가능, leak_report·evaluation_key 는 기업 전용."""

    draft: ProjectDraft
    leak_report: LeakReport
    evaluation_key: EvaluationKey = Field(default_factory=EvaluationKey, description="(v3) 숨은 함정·테스트 정답")


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
