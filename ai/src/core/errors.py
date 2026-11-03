class AIError(RuntimeError):
    """AI 영역에서 app 으로 올라가는 에러의 공통 부모."""


class ConfigError(AIError):
    """필수 설정이 비었거나 잘못됐을 때."""


class GenerationError(AIError):
    """재시도 후에도 과제 초안이 규칙 검증을 통과하지 못했을 때."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("과제 초안 검증 실패: " + "; ".join(errors))
