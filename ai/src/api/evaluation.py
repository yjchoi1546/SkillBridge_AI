from ..graphs.evaluation import run_evaluation
from ..schemas import EvaluationReport, SampleDataset, Submission, TaskSpec


async def evaluate_submission(
    task: TaskSpec, dataset: SampleDataset, submission: Submission
) -> EvaluationReport:
    """제출물 → 테스트 결과 + AI 평가 초안 (STEP 4)."""
    return await run_evaluation(task, dataset, submission)
