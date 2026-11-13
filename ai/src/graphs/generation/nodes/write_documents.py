"""자료실 문서(규정·기록·부서 의견·외부 정보)를 세계관·자료와 맞물리게 쓴다."""

from ....llms import generate_structured
from ....prompts import load_prompt
from ..assembly import company_instruction
from ..context import data_summary, revision_parts, world_text
from ..state import DocumentSet, GenerationState


async def write_documents(state: GenerationState) -> dict:
    parts = [
        company_instruction(state["request"]),
        world_text(state["world"]),
        data_summary(state["data_plan"], state["data"], include_hidden=True),
        *revision_parts(state, with_errors=False),
    ]
    docs = await generate_structured(
        "generation", DocumentSet, load_prompt("generation/write_documents"), "\n\n".join(parts)
    )
    return {"documents": docs.documents}
