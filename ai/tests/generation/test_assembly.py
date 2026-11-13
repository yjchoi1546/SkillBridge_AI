"""초안 조립 규칙: 설계 설명 문항, 호환용 난이도 과제, 민감 단어 검사."""

from ai.src.graphs.generation.assembly import BASE_IDS, check_leak, merge_design_questions
from ai.src.schemas import DesignQuestion, ProjectDraft, SampleDataset

EMPTY = SampleDataset(filename="a.csv", columns=[], csv="", seed=0)


def _q(id_: str, *prompts: str) -> DesignQuestion:
    return DesignQuestion(id=id_, title=id_, prompts=list(prompts), max_chars=1000)


def test_base_questions_always_present_and_500_chars():
    merged = merge_design_questions([_q("q_flow", "승인·거절이 오면 상태가 어떻게 바뀌나요?")])
    assert [q.id for q in merged] == BASE_IDS
    assert merged[1].prompts == ["승인·거절이 오면 상태가 어떻게 바뀌나요?"]  # LLM 이 다듬은 하위 질문 사용
    assert all(q.max_chars == 500 and q.required for q in merged)


def test_at_most_two_extra_questions():
    extras = [_q(f"q_extra{i}", "질문") for i in range(4)]
    merged = merge_design_questions(extras)
    assert len(merged) == 5 and [q.id for q in merged[3:]] == ["q_extra0", "q_extra1"]


def test_leak_check_finds_term_in_csv_and_text():
    draft = ProjectDraft(
        title="과제",
        summary="실제회사 지점 이야기",
        dataset=EMPTY,
        datasets=[SampleDataset(filename="s.csv", columns=[], csv="name\n실제회사\n", seed=0)],
    )
    report = check_leak(draft, ["실제회사"])
    assert report.status == "failed"
    assert {"summary", "datasets[0].csv"} <= {f.location for f in report.findings}
    assert check_leak(draft, []).status == "passed"
