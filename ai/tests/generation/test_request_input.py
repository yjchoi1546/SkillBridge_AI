"""기업 요청을 LLM 프롬프트에 넣을 때의 형식 (첨부 문서 처리 포함)."""

import asyncio

from ai.src import api
from ai.src.graphs.generation.request_input import format_request

PDF_BYTES = b"%PDF-1.7\n\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"


def _request(**kwargs) -> api.ProjectRequest:
    return api.ProjectRequest(request_text="지점별 매출 보고서 작성 시간을 줄이고 싶습니다.", **kwargs)


def test_generate_project_with_binary_attachment():
    """PDF 같은 바이너리 첨부가 있어도 생성이 죽지 않는다."""
    req = _request(documents=[api.CompanyDocument(filename="규격서.pdf", media_type="application/pdf", content=PDF_BYTES)])
    result = asyncio.run(api.generate_project(req))
    assert len(result.draft.tasks) == 3


def test_binary_attachment_listed_without_bytes():
    req = _request(documents=[api.CompanyDocument(filename="규격서.pdf", media_type="application/pdf", content=PDF_BYTES)])
    text = format_request(req)
    assert "규격서.pdf" in text
    assert "%PDF" not in text
    assert "content" not in text


def test_text_attachment_included():
    body = "판단 규칙: 전주 대비 20% 이상 하락하면 지역본부장에게 보고"
    req = _request(documents=[api.CompanyDocument(filename="규칙.md", media_type="text/markdown", content=body.encode())])
    assert body in format_request(req)


def test_long_text_attachment_truncated():
    body = "가" * 50_000
    req = _request(documents=[api.CompanyDocument(filename="긴문서.txt", media_type="text/plain", content=body.encode())])
    text = format_request(req)
    assert len(text) < 20_000
    assert "이하 생략" in text


def test_clarifications_included():
    req = _request(clarifications=[api.Clarification(question="누가 결정하나요?", answer="지역본부장")])
    text = format_request(req)
    assert "누가 결정하나요?" in text and "지역본부장" in text
