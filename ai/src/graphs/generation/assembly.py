"""초안 조립에 쓰는 코드 규칙: 설계 설명 기본 문항, 호환용 난이도 과제, 민감 단어 검사."""

from ...schemas import (
    DesignQuestion,
    Difficulty,
    LeakFinding,
    LeakReport,
    ProjectDraft,
    ProjectRequest,
    TaskSpec,
)

MAX_CHARS = 500
LEAK_PREFIX = "[leak]"
MAX_EXTRA_QUESTIONS = 2

# 기본 문항 3개. LLM 은 하위 질문을 과제 상황에 맞게 바꿀 수 있고, 문항을 최대 2개 더할 수 있다.
BASE_QUESTIONS: list[DesignQuestion] = [
    DesignQuestion(
        id="q_target",
        title="무엇을 풀었나",
        prompts=["누구의 어떤 일을 돕기로 했나요?", "여러 문제 중 그것을 고른 이유는 무엇인가요?"],
    ),
    DesignQuestion(
        id="q_flow",
        title="어떻게 동작하나",
        prompts=[
            "무엇을 받아서, 어떤 순서로 처리하고, 무엇을 남기나요?",
            "사람이 확인하거나 승인하는 곳은 어디인가요?",
        ],
    ),
    DesignQuestion(
        id="q_basis",
        title="무엇을 근거로 했나",
        prompts=[
            "어떤 파일·문서를 근거로 썼나요?",
            "자료에 없던 정보는 어떻게 처리했나요? (물어보기·미루기·가정)",
            "부서 의견과 사실을 어떻게 구분했나요?",
        ],
    ),
]
BASE_IDS = [q.id for q in BASE_QUESTIONS]


def merge_design_questions(proposed: list[DesignQuestion]) -> list[DesignQuestion]:
    """기본 3개는 항상 넣고(LLM 이 다듬은 하위 질문이 있으면 그것을), 추가 문항은 최대 2개. 글자 수는 500 고정."""
    by_id = {q.id: q for q in proposed}
    merged: list[DesignQuestion] = []
    for base in BASE_QUESTIONS:
        q = by_id.get(base.id)
        prompts = q.prompts if q and q.prompts else base.prompts
        merged.append(base.model_copy(update={"prompts": prompts, "required": True, "max_chars": MAX_CHARS}))
    extras = [q for q in proposed if q.id not in BASE_IDS and q.prompts][:MAX_EXTRA_QUESTIONS]
    merged += [q.model_copy(update={"max_chars": MAX_CHARS}) for q in extras]
    return merged


def compat_tasks(draft: ProjectDraft) -> list[TaskSpec]:
    """(v4 전환 기간 호환용) App 이 아직 난이도별 과제 3개를 기대하므로 v4 과제 하나로 같은 내용 3개를 만든다.

    LLM 을 다시 부르지 않는다. App 이 v4 화면으로 옮기면 지운다.
    """
    problem, guide = draft.problem, draft.start_guide
    base = dict(
        title=draft.title,
        goal=problem.mission if problem else draft.summary,
        scope=(problem.scope_guide if problem else "") or "범위는 참여자가 정한다.",
        steps=(guide.questions if guide and guide.questions else ["자료실 파일과 문서를 훑어본다", "풀 범위를 정한다", "시연할 상황 3개를 동작시킨다"]),
        deliverables=draft.deliverables or ["실행 가능한 결과물", "설계 설명"],
        skills=draft.skills or ["데이터 분석"],
        rubric=draft.review_criteria,
        tests=draft.tests,
        scenarios=draft.required_demos,
        done_examples=draft.done_examples,
        not_done_examples=draft.not_done_examples,
    )
    return [TaskSpec(difficulty=d, **base) for d in Difficulty]


def effective_generalization(req: ProjectRequest) -> str:
    """실제 회사명(low)은 회사 이름이 있고, 기업이 그 이름을 민감 단어로 막지 않았을 때만 쓴다. 아니면 가상 기업(medium)."""
    if req.generalization == "low":
        name = req.company_name.strip()
        blocked = any(t.strip() and (t.strip() in name or name in t) for t in req.sensitive_terms)
        if not name or blocked:
            return "medium"
    return req.generalization


def company_instruction(req: ProjectRequest) -> str:
    """노드 프롬프트에 넣는 '과제 속 회사' 지시."""
    mode, name = effective_generalization(req), req.company_name.strip()
    if mode == "low":
        return (
            f"과제 속 회사 설정: 실제 출제 기업 '{name}' 을 그대로 쓴다. context.company 는 '{name}' 으로 시작한다. "
            "단 데이터·문서는 모두 과제용 합성이므로 실제 실적·사건·인물처럼 단정하지 않고, "
            "이 회사에 대한 외부 기사(kind=external) 문서는 만들지 않는다."
        )
    if mode == "high":
        return "과제 속 회사 설정: 업무 구조는 그대로 두고 다른 업종으로 옮긴 가상 기업을 만든다. 이름 뒤에 '(가상 기업)'. 출제 기업 이름은 쓰지 않는다."
    return "과제 속 회사 설정: 같은 업종의 가상 기업을 새로 만든다. 이름 뒤에 '(가상 기업)'. 출제 기업 이름은 쓰지 않는다."


def apply_company_mode(draft: ProjectDraft, req: ProjectRequest) -> None:
    """실제 회사명 모드의 약속을 코드로 지킨다 (LLM 재시도에 맡기지 않는다).

    - 실제 회사에 대한 외부 기사 문서는 뺀다 (지어낸 기사가 실제 보도처럼 읽히지 않게)
    - 모든 문서 앞에 '합성 자료' 표시, 데이터 한계 맨 앞에 'CSV 는 합성' 표시
    - context.company 에 회사명이 없으면 앞에 붙인다
    """
    if effective_generalization(req) != "low":
        return
    name = req.company_name.strip()
    draft.documents = [d for d in draft.documents if d.kind != "external"]
    notice = f"> 이 문서는 과제용으로 만든 합성 자료입니다. {name} 의 실제 문서·수치가 아닙니다.\n\n"
    for doc in draft.documents:
        if not doc.content.startswith("> 이 문서는 과제용"):
            doc.content = notice + doc.content
    data_note = f"모든 CSV 는 과제용 합성 데이터입니다. {name} 의 실제 수치가 아닙니다."
    if data_note not in draft.data_notes:
        draft.data_notes.insert(0, data_note)
    if draft.context and name not in draft.context.company:
        draft.context.company = f"{name} — {draft.context.company}"


def leak_terms(req: ProjectRequest) -> list[str]:
    """유출 검사 단어. 가상 기업으로 만들 때는 출제 기업 이름도 공개본에 나오면 안 된다."""
    terms = list(req.sensitive_terms)
    if effective_generalization(req) != "low" and req.company_name.strip():
        terms.append(req.company_name.strip())
    return terms


def check_leak(draft: ProjectDraft, sensitive_terms: list[str]) -> LeakReport:
    """공개본에 기업이 지정한 민감 단어가 남았는지. 원문 고유명사·수치 비교는 TODO(AI-A)."""
    public = draft.model_dump(mode="json", exclude={"tasks"})
    findings: list[LeakFinding] = []

    def walk(node, path: str):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str):
            for term in sensitive_terms:
                if term.strip() and term in node:
                    findings.append(LeakFinding(text=term, location=path, source="sensitive_term"))

    walk(public, "")
    return LeakReport(status="failed" if findings else "passed", findings=findings)
