"""과제 초안 필수 항목 검사 (계약 v4, KPI 01: 과제 명세 필수 항목 충족률)."""

import csv
import io

from ..schemas import ProjectDraft

MIN_DATASETS, MIN_DOCUMENTS, MIN_RULES, MIN_CRITERIA = 2, 3, 3, 3
MAX_PUBLIC_CHARS = 1_200_000  # App ↔ AI 호출 입력 제한(2.1MB) 안에 수정 요청이 들어가도록


def check_draft(draft: ProjectDraft) -> list[str]:
    errors: list[str] = []

    if not draft.context or not draft.context.reference_date:
        errors.append("context 또는 기준일(reference_date) 없음")
    elif len(draft.context.departments) < 2:
        errors.append("부서·사람(departments)이 2개 미만")
    if not draft.problem or not draft.problem.situation or not draft.problem.mission:
        errors.append("problem 의 situation·mission 없음")

    if len(draft.rules) < MIN_RULES:
        errors.append(f"규칙이 {MIN_RULES}개 미만")
    if not any(r.category == "authority" for r in draft.rules):
        errors.append("승인 권한 규칙(category=authority) 없음")
    if len({r.id for r in draft.rules}) != len(draft.rules):
        errors.append("규칙 id 중복")

    if len(draft.datasets) < MIN_DATASETS:
        errors.append(f"자료 파일(CSV)이 {MIN_DATASETS}개 미만")
    columns = {(ds.filename.removesuffix(".csv"), c.name) for ds in draft.datasets for c in ds.columns}
    for ds in draft.datasets:
        header = next(csv.reader(io.StringIO(ds.csv)), [])
        if header != [c.name for c in ds.columns]:
            errors.append(f"{ds.filename}: 헤더 불일치")
        for c in ds.columns:
            if c.references and tuple(c.references.split(".", 1)) not in columns:
                errors.append(f"{ds.filename}.{c.name}: 참조 {c.references} 가 없는 표·열")

    if len(draft.documents) < MIN_DOCUMENTS:
        errors.append(f"문서가 {MIN_DOCUMENTS}개 미만")
    if len({d.kind for d in draft.documents}) < 2:
        errors.append("문서 성격(kind)이 한 가지뿐 — 규정·기록·부서 의견·외부 정보를 섞을 것")
    if len({d.filename for d in draft.documents}) != len(draft.documents):
        errors.append("문서 파일 이름 중복")

    kinds = sorted(s.kind for s in draft.required_demos)
    if kinds != ["changed", "exception", "normal"]:
        errors.append(f"시연 상황은 normal / changed / exception 하나씩이어야 함 (현재 {kinds})")
    if not draft.start_guide or not draft.start_guide.first_files:
        errors.append("시작 가이드의 먼저 볼 파일(first_files) 없음")
    else:
        files = {d.filename for d in draft.datasets} | {d.filename for d in draft.documents}
        unknown = [f for f in draft.start_guide.first_files if f not in files]
        if unknown:
            errors.append(f"먼저 볼 파일 {unknown} 가 자료실에 없음 (파일 이름 그대로 쓸 것)")
    if not 3 <= len(draft.design_questions) <= 5:
        errors.append(f"설계 설명 문항은 3~5개 (현재 {len(draft.design_questions)})")
    if len(draft.review_criteria) < MIN_CRITERIA:
        errors.append(f"평가 관점이 {MIN_CRITERIA}개 미만")
    if not draft.deliverables:
        errors.append("제출물(deliverables) 없음")
    if not draft.done_examples or not draft.not_done_examples:
        errors.append("완성·미완성 예시 없음")
    ids = [t.id for t in draft.tests]
    if len(ids) != len(set(ids)):
        errors.append("테스트 id 중복")

    size = len(draft.model_dump_json(exclude={"tasks", "dataset"}))
    if size > MAX_PUBLIC_CHARS:
        errors.append(f"초안이 너무 큼 ({size:,}자) — 행 수나 문서 길이를 줄일 것")
    return errors
