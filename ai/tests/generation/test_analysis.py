"""STEP 1 요청 분석 결과 (ProblemAnalysis) 형태."""

import pytest
from pydantic import ValidationError

from ai.src.graphs.generation.state import ProblemAnalysis

BASE = {"problem": "p", "goals": [], "constraints": [], "required_skills": []}


def test_new_fields_have_defaults():
    """새 필드가 없어도 읽힌다 (가짜 응답·이전 버전 호환)."""
    a = ProblemAnalysis.model_validate(BASE)
    assert a.decision_maker == "" and a.rules == [] and a.missing == []


def test_rule_source_and_missing_slots():
    a = ProblemAnalysis.model_validate(
        {
            **BASE,
            "rules": [
                {"text": "전주 대비 20% 이상 하락 시 보고", "source": "company", "evidence": "20% 넘게 빠지면"},
                {"text": "휴점일은 비교에서 제외", "source": "assumed", "evidence": "휴점 기준이 입력에 없음"},
            ],
            "missing": ["decision_maker", "success_criteria"],
        }
    )
    assert [r.source for r in a.rules] == ["company", "assumed"]


@pytest.mark.parametrize("field,value", [("missing", ["deadline"]), ("rules", [{"text": "x", "source": "guess"}])])
def test_rejects_unknown_values(field, value):
    with pytest.raises(ValidationError):
        ProblemAnalysis.model_validate({**BASE, field: value})
