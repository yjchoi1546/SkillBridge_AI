from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from ...core.errors import GenerationError
from ...schemas import ProjectDraft, ProjectRequest
from .nodes import (
    analyze_request,
    design_dataset,
    design_evaluation,
    design_project,
    validate_draft,
)
from .routers import route_after_validation
from .state import GenerationState


@lru_cache(maxsize=1)
def build_graph():
    g = StateGraph(GenerationState)
    g.add_node("analyze_request", analyze_request)
    g.add_node("design_project", design_project)
    g.add_node("design_dataset", design_dataset)
    g.add_node("design_evaluation", design_evaluation)
    g.add_node("validate_draft", validate_draft)

    g.add_edge(START, "analyze_request")
    g.add_edge("analyze_request", "design_project")
    g.add_edge("design_project", "design_dataset")
    g.add_edge("design_dataset", "design_evaluation")
    g.add_edge("design_evaluation", "validate_draft")
    g.add_conditional_edges(
        "validate_draft",
        route_after_validation,
        {"retry": "design_project", "done": END},
    )
    return g.compile()


async def run_generation(
    request: ProjectRequest,
    previous_draft: ProjectDraft | None = None,
    feedback: str | None = None,
) -> ProjectDraft:
    final = await build_graph().ainvoke(
        {
            "request": request,
            "previous_draft": previous_draft,
            "feedback": feedback,
            "errors": [],
            "attempts": 0,
        }
    )
    if final.get("errors"):
        raise GenerationError(final["errors"])
    return final["draft"]
