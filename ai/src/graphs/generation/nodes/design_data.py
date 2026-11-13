"""자료 설계도(LLM) → CSV 여러 개 생성(코드, seed 고정). 설계도에 문제가 있으면 오류를 알려 주고 다시 쓰게 한다."""

import zlib

from ....datagen import DataPlan, build_dataset
from ....llms import generate_structured
from ....prompts import load_prompt
from ..context import revision_parts, world_text
from ..state import GenerationState

PLAN_RETRIES = 2  # 설계도 오류(없는 열 참조, 0행에 적용된 사실 등)를 고쳐 쓰게 하는 횟수


async def design_data(state: GenerationState) -> dict:
    world = state["world"]
    base = "\n\n".join(
        [
            world_text(world),
            "데이터로 드러나야 할 이야기 (각각 사실 FactPlan 으로 심을 것):\n- " + "\n- ".join(world.story),
            *revision_parts(state, with_errors=False),
        ]
    )
    # 같은 요청이면 같은 데이터가 나오도록 요청 문장에서 seed 를 만든다.
    seed = zlib.crc32(state["request"].request_text.encode("utf-8"))
    system = load_prompt("generation/design_data")

    prompt = base
    for attempt in range(PLAN_RETRIES + 1):
        plan = await generate_structured("generation", DataPlan, system, prompt)
        data = build_dataset(plan, seed)
        if not data.errors or attempt == PLAN_RETRIES:
            break
        prompt = (
            f"{base}\n\n직전 설계도:\n{plan.model_dump_json(indent=2)}\n\n"
            "직전 설계도의 문제 (모두 고쳐서 설계도 전체를 다시 쓸 것):\n- " + "\n- ".join(data.errors)
        )
    return {"data_plan": plan, "data": data}
