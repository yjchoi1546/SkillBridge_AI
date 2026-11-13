"""과제 속 회사: 기본은 실제 회사명, 원하면 가상 기업."""

import asyncio

from ai.src import api
from ai.src.graphs.generation.assembly import company_instruction, effective_generalization, leak_terms

TEXT = "매주 엑셀로 취합하는 지점별 매출 보고서 작성 시간을 줄이고 싶습니다."


def _req(**kw) -> api.ProjectRequest:
    return api.ProjectRequest(request_text=TEXT, **kw)


def test_default_is_real_company_name():
    req = _req(company_name="한빛리테일")
    assert req.generalization == "low"
    assert effective_generalization(req) == "low"
    assert "'한빛리테일' 을 그대로" in company_instruction(req)


def test_falls_back_to_virtual_without_name_or_when_blocked():
    assert effective_generalization(_req()) == "medium"  # 회사명을 못 받음
    assert effective_generalization(_req(company_name="한빛리테일", sensitive_terms=["한빛리테일"])) == "medium"


def test_virtual_mode_treats_company_name_as_leak():
    assert "한빛리테일" in leak_terms(_req(company_name="한빛리테일", generalization="medium"))
    assert "한빛리테일" not in leak_terms(_req(company_name="한빛리테일"))


def test_real_name_mode_marks_everything_synthetic_and_drops_articles():
    result = asyncio.run(api.generate_project(_req(company_name="한빛리테일")))
    draft = result.draft
    assert draft.context.company.startswith("한빛리테일")
    assert all(d.content.startswith("> 이 문서는 과제용으로 만든 합성 자료입니다. 한빛리테일") for d in draft.documents)
    assert "external" not in {d.kind for d in draft.documents}  # 실제 회사에 대한 지어낸 기사는 만들지 않는다
    assert draft.data_notes[0].startswith("모든 CSV 는 과제용 합성 데이터")
    assert result.leak_report.status == "passed"


def test_virtual_mode_keeps_articles():
    draft = asyncio.run(api.generate_project(_req(company_name="한빛리테일", generalization="medium"))).draft
    assert "external" in {d.kind for d in draft.documents}
    assert not draft.documents[0].content.startswith("> 이 문서는 과제용")
