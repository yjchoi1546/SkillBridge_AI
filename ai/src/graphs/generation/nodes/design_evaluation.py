"""STEP 3b — 과제별 평가 루브릭과 사전 정의 테스트 항목."""

import asyncio

from pydantic import BaseModel

from ....llms import generate_structured
from ....prompts import load_prompt
from ....schemas import RubricItem, TaskSpec, TestCase
from ..state import GenerationState, TaskOutline


class TaskEvaluation(BaseModel):
    rubric: list[RubricItem]
    tests: list[TestCase]


async def _design_one(task: TaskOutline, dataset_json: str) -> TaskSpec:
    user = f"과제:\n{task.model_dump_json(indent=2)}\n\n샘플 데이터 스키마:\n{dataset_json}"
    ev = await generate_structured(
        "generation", TaskEvaluation, load_prompt("generation/design_evaluation"), user
    )
    return TaskSpec(**task.model_dump(), rubric=ev.rubric, tests=ev.tests)


async def design_evaluation(state: GenerationState) -> dict:
    dataset_json = state["dataset_spec"].model_dump_json(indent=2)
    tasks = await asyncio.gather(*(_design_one(t, dataset_json) for t in state["outline"].tasks))
    return {"tasks": list(tasks)}
