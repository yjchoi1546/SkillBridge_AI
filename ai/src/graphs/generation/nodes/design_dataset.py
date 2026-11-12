"""STEP 3a — 샘플 데이터 설계(LLM) + 실제 행 생성(datagen, seed 고정)."""

import zlib

from ....datagen import DatasetSpec, generate_csv
from ....llms import generate_structured
from ....prompts import load_prompt
from ....schemas import DatasetColumn, SampleDataset
from ..request_input import format_request
from ..state import GenerationState


async def design_dataset(state: GenerationState) -> dict:
    user = (
        f"업무 요청:\n{format_request(state['request'])}\n\n"
        f"과제 구성:\n{state['outline'].model_dump_json(indent=2)}"
    )
    spec = await generate_structured(
        "generation", DatasetSpec, load_prompt("generation/design_dataset"), user
    )

    # 같은 요청이면 같은 데이터가 나오도록 요청 문장에서 seed 를 만든다.
    seed = zlib.crc32(state["request"].request_text.encode("utf-8"))
    dataset = SampleDataset(
        filename=spec.filename,
        columns=[DatasetColumn(name=c.name, dtype=c.dtype, description=c.description) for c in spec.columns],
        csv=generate_csv(spec, seed),
        seed=seed,
    )
    return {"dataset_spec": spec, "dataset": dataset}
