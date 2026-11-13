"""초안 조립에 쓰는 코드 규칙: 설계 설명 기본 문항, 호환용 난이도 과제, 민감 단어 검사."""

from ...schemas import (
    DesignQuestion,
    Difficulty,
    LeakFinding,
    LeakReport,
    ProjectDraft,
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
