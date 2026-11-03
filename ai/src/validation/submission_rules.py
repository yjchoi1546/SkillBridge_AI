"""제출물 형식 검사. 통과하지 못하면 테스트·AI 평가를 돌리지 않는다."""

from ..schemas import Submission, TaskSpec

# LLM 에 넘길 제출물 총량 상한. 넘으면 잘라내지 않고 형식 미충족으로 돌려보낸다.
MAX_TOTAL_CHARS = 200_000


def check_submission(task: TaskSpec, submission: Submission) -> list[str]:
    errors: list[str] = []
    if not submission.files:
        errors.append("제출 파일이 없음")
    empty = [name for name, body in submission.files.items() if not body.strip()]
    if empty:
        errors.append(f"빈 파일: {empty}")
    total = sum(len(body) for body in submission.files.values())
    if total > MAX_TOTAL_CHARS:
        errors.append(f"제출물이 너무 큼 ({total:,}자 > {MAX_TOTAL_CHARS:,}자)")
    return errors
