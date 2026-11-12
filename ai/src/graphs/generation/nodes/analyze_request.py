"""STEP 1 Problem Analyst — 요청에서 막히는 업무·결정권자·판단 규칙·데이터·성공 기준을 추출하고 빈 칸을 표시."""

from ....llms import generate_structured
from ....prompts import load_prompt
from ..request_input import format_request
from ..state import GenerationState, ProblemAnalysis


async def analyze_request(state: GenerationState) -> dict:
    req = state["request"]
    user = f"업무 요청:\n{format_request(req)}"
    if state.get("feedback"):
        user += f"\n\n기업 수정 요청:\n{state['feedback']}"

    analysis = await generate_structured(
        "generation", ProblemAnalysis, load_prompt("generation/analyze_request"), user
    )
    return {"analysis": analysis}
