"""AI 평가 초안 — 루브릭 기준별 충족/미충족/미검증 판정. 최종 판단은 기업 검토가 한다."""

import json

from ....llms import generate_structured
from ....prompts import load_prompt
from ..state import EvaluationState, ReviewDraft


async def draft_review(state: EvaluationState) -> dict:
    files = "\n\n".join(
        f"--- {name} ---\n{body}" for name, body in state["submission"].files.items()
    )
    tests = json.dumps(
        [r.model_dump() for r in state["test_results"]], ensure_ascii=False, indent=2
    )
    user = (
        f"과제 명세:\n{state['task'].model_dump_json(indent=2)}\n\n"
        f"테스트 결과:\n{tests}\n\n"
        f"제출물:\n{files}"
    )
    review = await generate_structured(
        "evaluation", ReviewDraft, load_prompt("evaluation/draft_review"), user
    )
    return {"review": review}
