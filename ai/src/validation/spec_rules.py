"""과제 초안 필수 항목 검사 (KPI 01: 과제 명세 필수 항목 충족률)."""

import csv
import io

from ..schemas import Difficulty, ProjectDraft


def check_draft(draft: ProjectDraft) -> list[str]:
    errors: list[str] = []

    difficulties = [t.difficulty for t in draft.tasks]
    if sorted(difficulties) != sorted(Difficulty):
        errors.append(f"난이도는 초급/중급/고급 각 1개여야 함 (현재: {[d.value for d in difficulties]})")

    for t in draft.tasks:
        where = f"[{t.difficulty.value}] {t.title}"
        for field in ("goal", "scope", "steps", "deliverables", "rubric", "tests"):
            if not getattr(t, field):
                errors.append(f"{where}: {field} 비어 있음")
        ids = [c.id for c in t.tests]
        if len(ids) != len(set(ids)):
            errors.append(f"{where}: 테스트 id 중복")

    header = next(csv.reader(io.StringIO(draft.dataset.csv)), [])
    expected = [c.name for c in draft.dataset.columns]
    if header != expected:
        errors.append(f"샘플 데이터 헤더 불일치: {header} != {expected}")

    return errors
