"""기업 요청(ProjectRequest)을 LLM 프롬프트용 텍스트로 바꾼다.

`model_dump_json()` 을 그대로 쓰면 첨부 문서의 원본 바이트(PDF 등)가 UTF-8 이 아니어서
직렬화 오류가 나고, 성공해도 바이트가 프롬프트를 채운다. 그래서 첨부는 따로 다룬다.

- 텍스트 문서(text/*, .md/.txt/.csv 등): 내용을 앞부분만 넣는다.
- 그 밖(PDF, DOCX 등): 파일 이름과 형식만 알린다. 텍스트 추출은 의존성 추가가 필요해 아직 안 한다.
"""

from pathlib import PurePath

from ...schemas import CompanyDocument, ProjectRequest

MAX_DOC_CHARS = 8_000  # 문서 1개당 프롬프트에 넣는 최대 글자 수
MAX_TOTAL_DOC_CHARS = 16_000  # 첨부 전체 상한

_TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".csv", ".tsv", ".json", ".yaml", ".yml"}
_TEXT_MEDIA_TYPES = {"application/json", "application/x-yaml", "application/yaml"}


def _is_text(doc: CompanyDocument) -> bool:
    media = doc.media_type.split(";")[0].strip().lower()
    return media.startswith("text/") or media in _TEXT_MEDIA_TYPES or PurePath(doc.filename).suffix.lower() in _TEXT_SUFFIXES


def _decode(content: bytes) -> str | None:
    for encoding in ("utf-8-sig", "cp949"):  # 국내 기업 문서는 cp949(EUC-KR) 인 경우가 많다
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def format_document(doc: CompanyDocument, limit: int = MAX_DOC_CHARS) -> str:
    header = f"[첨부] {doc.filename} ({doc.media_type})"
    text = _decode(doc.content) if _is_text(doc) else None
    if text is None:
        return f"{header}\n(이 형식은 아직 내용을 읽지 못한다. 파일 이름만 참고하고, 내용을 추측하지 않는다.)"
    text = text.strip()
    if limit <= 0:
        return f"{header}\n(분량 제한으로 내용 생략)"
    if len(text) > limit:
        text = text[:limit] + f"\n... (이하 생략, 전체 {len(text):,}자)"
    return f"{header}\n{text}"


def format_request(req: ProjectRequest) -> str:
    """노드 프롬프트에 넣을 기업 요청 텍스트. 첨부 바이트는 포함하지 않는다."""
    body = req.model_dump_json(indent=2, exclude={"documents"})
    parts = [body]
    if req.documents:
        budget = MAX_TOTAL_DOC_CHARS
        rendered = []
        for doc in req.documents:
            block = format_document(doc, min(MAX_DOC_CHARS, budget))
            budget -= len(block)
            rendered.append(block)
        parts.append("첨부 문서:\n\n" + "\n\n".join(rendered))
    return "\n\n".join(parts)
