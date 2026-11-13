from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from ...core.errors import GenerationError
from ...core.tracing import annotate, langchain_callbacks
from ...schemas import GenerationResult, ProjectDraft, ProjectRequest
from .nodes import (
    analyze_request,
    design_data,
    design_world,
    finish_project,
    validate_draft,
    write_documents,
)
from .assembly import LEAK_PREFIX
from .routers import route_after_validation
from .state import GenerationState


@lru_cache(maxsize=1)
def build_graph():
    g = StateGraph(GenerationState)
    # LLM 호출은 순서대로 한 번에 하나씩 (무료 API 동시 요청 제한)
    steps = ["analyze_request", "design_world", "design_data", "write_documents", "finish_project", "validate_draft"]
    for name, fn in zip(steps, [analyze_request, design_world, design_data, write_documents, finish_project, validate_draft]):
        g.add_node(name, fn)
    g.add_edge(START, steps[0])
    for a, b in zip(steps, steps[1:]):
        g.add_edge(a, b)
    g.add_conditional_edges(
        "validate_draft",
        route_after_validation,
        {"retry": "design_world", "done": END},
    )
    return g.compile()


async def run_generation(
    request: ProjectRequest,
    previous_draft: ProjectDraft | None = None,
    feedback: str | None = None,
) -> GenerationResult:
    final = await build_graph().ainvoke(
        {
            "request": request,
            "previous_draft": previous_draft,
            "feedback": feedback,
            "errors": [],
            "attempts": 0,
        },
        config={"callbacks": langchain_callbacks(), "run_name": "generation-graph"},
    )
    # KPI 01 (필수 항목 충족률) — 몇 번 만에 검증을 통과했는지
    annotate(attempts=final.get("attempts", 0), validation_errors=final.get("errors", []))
    blocking = [e for e in final.get("errors", []) if not e.startswith(LEAK_PREFIX)]
    if blocking:
        raise GenerationError(blocking)
    return GenerationResult(
        draft=final["draft"],
        leak_report=final["leak_report"],
        evaluation_key=final["evaluation_key"],
    )
