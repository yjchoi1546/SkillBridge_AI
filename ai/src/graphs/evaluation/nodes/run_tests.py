"""사전 정의 테스트 실행 — 샌드박스에 위임한다."""

from ....sandbox import get_runner
from ..state import EvaluationState


async def run_tests(state: EvaluationState) -> dict:
    results = await get_runner().run(state["task"], state["dataset"], state["submission"])
    return {"test_results": results}
