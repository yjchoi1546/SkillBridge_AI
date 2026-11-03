"""참여자 코드 제한 실행.

원칙: 참여자 코드는 절대 호스트에서 바로(subprocess 등) 실행하지 않는다.
네트워크 차단·시간/메모리 제한이 걸린 격리 환경(예: 일회용 Docker 컨테이너)에서만 돌린다.

TODO(AI 개발자 B):
- TestCase(kind="auto") 를 실제로 실행 가능한 형태로 만들 방법 결정
  (예: 데이터셋에서 정답을 미리 계산해 두고 출력과 비교 / 고정 pytest 템플릿).
  결정되면 schemas.py 의 TestCase 에 필드를 추가한다 (app 과 합의 후).
- 격리 실행 구현체 작성 후 get_runner() 교체.
"""

from typing import Protocol

from ..schemas import SampleDataset, Submission, TaskSpec, TestResult


class SandboxRunner(Protocol):
    async def run(
        self, task: TaskSpec, dataset: SampleDataset, submission: Submission
    ) -> list[TestResult]: ...


class NotConfiguredRunner:
    """샌드박스 구현 전 임시. 아무것도 실행하지 않고 전부 '미실행'으로 돌려준다."""

    async def run(
        self, task: TaskSpec, dataset: SampleDataset, submission: Submission
    ) -> list[TestResult]:
        return [
            TestResult(test_id=t.id, passed=None, detail="샌드박스 미구성 — 실행하지 않음")
            for t in task.tests
        ]


def get_runner() -> SandboxRunner:
    return NotConfiguredRunner()
