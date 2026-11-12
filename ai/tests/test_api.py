"""공개 API(ai/src/api) 계약 테스트. App 이 기대하는 입출력 형태가 깨지면 여기서 먼저 실패한다.

LLM 은 가짜 모드라 내용이 아니라 '흐름과 형태'를 검사한다.
"""

import asyncio
import csv
import io

import pytest

from ai.src import api
from ai.src.api.generation import _request_input


def _request(sample_requests, **extra) -> api.ProjectRequest:
    return api.ProjectRequest(**sample_requests[0], **extra)


def _generate(request: api.ProjectRequest) -> api.GenerationResult:
    return asyncio.run(api.generate_project(request))


# ── 과제 생성 ─────────────────────────────────────────────


def test_generate_project_returns_three_difficulties(sample_requests):
    result = _generate(_request(sample_requests))

    assert isinstance(result, api.GenerationResult)
    assert sorted(t.difficulty for t in result.draft.tasks) == sorted(api.Difficulty)
    for task in result.draft.tasks:
        assert task.rubric and task.tests


def test_leak_report_not_checked_until_implemented(sample_requests):
    result = _generate(_request(sample_requests))
    assert result.leak_report.status == "not_checked"


def test_dataset_csv_matches_columns_and_is_reproducible(sample_requests):
    request = _request(sample_requests)
    first, second = _generate(request).draft.dataset, _generate(request).draft.dataset

    header = next(csv.reader(io.StringIO(first.csv)))
    assert header == [c.name for c in first.columns]
    assert first.csv == second.csv  # 같은 요청이면 같은 데이터 (seed 고정)


def test_revise_project_returns_generation_result(sample_requests):
    request = _request(sample_requests)
    draft = _generate(request).draft
    revised = asyncio.run(api.revise_project(request, draft, "초급 과제를 더 쉽게"))
    assert isinstance(revised, api.GenerationResult)


def test_ask_clarifying_questions_stub_returns_empty(sample_requests):
    assert asyncio.run(api.ask_clarifying_questions(_request(sample_requests))) == []


def test_document_bytes_never_reach_trace_input(sample_requests):
    secret = b"CONFIDENTIAL-SPEC-BODY"
    request = _request(
        sample_requests,
        documents=[api.CompanyDocument(filename="spec.pdf", media_type="application/pdf", content=secret)],
    )
    traced = _request_input(request)
    assert traced["documents"] == [{"filename": "spec.pdf", "media_type": "application/pdf", "bytes": len(secret)}]
    assert "CONFIDENTIAL" not in str(traced)


# ── 제출물 평가 ───────────────────────────────────────────


@pytest.fixture
def generated(sample_requests) -> api.ProjectDraft:
    return _generate(_request(sample_requests)).draft


def test_evaluate_rejects_empty_submission(generated):
    task = generated.tasks[0]
    report = asyncio.run(api.evaluate_submission(task, generated.dataset, api.Submission(files={})))

    assert report.ai_summary.startswith("제출물 형식 미충족")
    assert all(r.passed is None for r in report.test_results)


def test_evaluate_valid_submission_produces_review(generated):
    task = generated.tasks[0]
    submission = api.Submission(
        files={"main.py": "import pandas as pd\nprint('ok')\n"},
        process_log=[api.ProcessEntry(question="처음 세운 가설은?", answer="주차 변환이 핵심이라고 봤다.")],
    )
    report = asyncio.run(api.evaluate_submission(task, generated.dataset, submission))

    assert [r.test_id for r in report.test_results] == [t.id for t in task.tests]
    assert report.ai_review and report.ai_summary


def test_followup_questions_stub_returns_empty(generated):
    submission = api.Submission(files={"main.py": "print(1)"})
    assert asyncio.run(api.generate_followup_questions(generated.tasks[0], submission)) == []


# ── v3 계약 ───────────────────────────────────────────────


def test_v3_draft_has_context_rules_scenarios(sample_requests):
    draft = _generate(_request(sample_requests)).draft

    assert draft.context and draft.context.reference_date
    assert {r.source for r in draft.rules} <= {"company", "assumed"}
    for task in draft.tasks:
        assert sorted(s.kind for s in task.scenarios) == ["changed", "exception", "normal"]
        assert task.done_examples and task.not_done_examples


def test_v3_datasets_starts_with_dataset(sample_requests):
    draft = _generate(_request(sample_requests)).draft
    assert draft.datasets and draft.datasets[0] == draft.dataset  # App 이 옮겨 가는 동안 둘 다 채운다


def test_v3_evaluation_key_stays_out_of_public_draft(sample_requests):
    """숨은 함정·정답은 기업·평가 전용. App 이 공개하는 draft 에 섞이면 안 된다."""
    result = _generate(_request(sample_requests))

    assert result.evaluation_key.hidden_checks  # 가짜 데이터에는 결측·이상치가 심겨 있다
    public = result.draft.model_dump_json()
    assert "hidden_checks" not in public and "answers" not in public
    for check in result.evaluation_key.hidden_checks:
        assert check.how_to_check not in public


def test_v3_request_intake_is_optional(sample_requests):
    request = _request(sample_requests, intake=api.CompanyIntake(decision_maker="지역본부장"))
    assert _generate(request).draft.tasks


def test_v3_evaluate_accepts_evaluation_key(sample_requests):
    result = _generate(_request(sample_requests))
    submission = api.Submission(files={"main.py": "print(1)"})
    report = asyncio.run(
        api.evaluate_submission(
            result.draft.tasks[0], result.draft.dataset, submission, evaluation_key=result.evaluation_key
        )
    )
    assert report.test_results
