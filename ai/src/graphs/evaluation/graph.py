from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from ...schemas import EvaluationReport, SampleDataset, Submission, TaskSpec
from .nodes import build_report, check_submission, draft_review, run_tests
from .routers import route_after_check
from .state import EvaluationState


@lru_cache(maxsize=1)
def build_graph():
    g = StateGraph(EvaluationState)
    g.add_node("check_submission", check_submission)
    g.add_node("run_tests", run_tests)
    g.add_node("draft_review", draft_review)
    g.add_node("build_report", build_report)

    g.add_edge(START, "check_submission")
    g.add_conditional_edges(
        "check_submission",
        route_after_check,
        {"ok": "run_tests", "invalid": "build_report"},
    )
    g.add_edge("run_tests", "draft_review")
    g.add_edge("draft_review", "build_report")
    g.add_edge("build_report", END)
    return g.compile()


async def run_evaluation(
    task: TaskSpec, dataset: SampleDataset, submission: Submission
) -> EvaluationReport:
    final = await build_graph().ainvoke(
        {"task": task, "dataset": dataset, "submission": submission}
    )
    return final["report"]
