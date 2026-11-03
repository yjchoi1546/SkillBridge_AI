"""STEP 2 Project Designer — 수행 범위, 난이도별 과제 명세, 제출물 형식."""

from ....llms import generate_structured
from ....prompts import load_prompt
from ..state import GenerationState, ProjectOutline


async def design_project(state: GenerationState) -> dict:
    parts = [
        f"업무 요청:\n{state['request'].model_dump_json(indent=2)}",
        f"문제 분석:\n{state['analysis'].model_dump_json(indent=2)}",
    ]
    if state.get("previous_draft"):
        parts.append(f"기존 초안:\n{state['previous_draft'].model_dump_json(indent=2)}")
    if state.get("feedback"):
        parts.append(f"기업 수정 요청:\n{state['feedback']}")
    if state.get("errors"):
        parts.append("직전 시도의 검증 오류 (반드시 해결):\n- " + "\n- ".join(state["errors"]))

    outline = await generate_structured(
        "generation", ProjectOutline, load_prompt("generation/design_project"), "\n\n".join(parts)
    )
    return {"outline": outline}
