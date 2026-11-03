"""STEP 1 Problem Analyst — 자연어 요청에서 문제·목표·제약·필요 역량 추출."""

from ....llms import generate_structured
from ....prompts import load_prompt
from ..state import GenerationState, ProblemAnalysis


async def analyze_request(state: GenerationState) -> dict:
    req = state["request"]
    user = f"업무 요청:\n{req.model_dump_json(indent=2)}"
    if state.get("feedback"):
        user += f"\n\n기업 수정 요청:\n{state['feedback']}"

    analysis = await generate_structured(
        "generation", ProblemAnalysis, load_prompt("generation/analyze_request"), user
    )
    return {"analysis": analysis}
