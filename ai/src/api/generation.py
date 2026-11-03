from ..graphs.generation import run_generation
from ..schemas import ProjectDraft, ProjectRequest


async def generate_project(request: ProjectRequest) -> ProjectDraft:
    """기업 업무 요청 → 과제 초안 (STEP 1~3)."""
    return await run_generation(request)


async def revise_project(request: ProjectRequest, draft: ProjectDraft, feedback: str) -> ProjectDraft:
    """기업의 [수정] 요청. 기존 초안과 코멘트를 반영해 다시 생성한다."""
    return await run_generation(request, previous_draft=draft, feedback=feedback)
