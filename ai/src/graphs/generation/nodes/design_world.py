"""가상 회사·문제·규칙과 데이터로 드러나야 할 이야기를 설계한다."""

from ....llms import generate_structured
from ....prompts import load_prompt
from ..assembly import company_instruction
from ..context import revision_parts
from ..request_input import format_request
from ..state import GenerationState, WorldPlan


async def design_world(state: GenerationState) -> dict:
    parts = [
        f"업무 요청:\n{format_request(state['request'])}",
        f"요청 분석:\n{state['analysis'].model_dump_json(indent=2)}",
        company_instruction(state["request"]),
        *revision_parts(state),
    ]
    world = await generate_structured(
        "generation", WorldPlan, load_prompt("generation/design_world"), "\n\n".join(parts)
    )
    return {"world": world}
