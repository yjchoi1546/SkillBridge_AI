"""llms.generate_structured 의 형식 오류 재시도."""

import asyncio

import pytest
from pydantic import BaseModel

from ai.src import llms


class Out(BaseModel):
    items: list[str]


class _StubModel:
    """첫 n 번은 스키마를 어기고(list 자리에 글머리표 문자열), 그다음엔 정상 응답."""

    def __init__(self, bad_times: int):
        self.bad_times = bad_times
        self.prompts: list[str] = []

    def with_structured_output(self, schema, **kwargs):
        return self

    async def ainvoke(self, messages):
        self.prompts.append(messages[-1][1])
        if len(self.prompts) <= self.bad_times:
            return Out.model_validate({"items": "- a\n- b"})  # ValidationError
        return Out(items=["a", "b"])


@pytest.fixture
def stub(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "exaone")
    monkeypatch.setenv("EXAONE_API_KEY", "k")
    monkeypatch.setenv("EXAONE_MODEL", "m")

    def install(bad_times: int) -> _StubModel:
        model = _StubModel(bad_times)
        monkeypatch.setattr(llms, "get_chat_model", lambda task: model)
        return model

    return install


def test_retries_with_error_feedback_then_succeeds(stub):
    model = stub(bad_times=1)
    out = asyncio.run(llms.generate_structured("generation", Out, "sys", "원래 요청"))

    assert out.items == ["a", "b"]
    assert len(model.prompts) == 2
    assert model.prompts[0] == "원래 요청"
    assert "직전 응답 형식 오류" in model.prompts[1] and "원래 요청" in model.prompts[1]


def test_gives_up_after_max_retries(stub):
    model = stub(bad_times=99)
    with pytest.raises(Exception):
        asyncio.run(llms.generate_structured("generation", Out, "sys", "u"))
    assert len(model.prompts) == llms.STRUCTURED_RETRIES + 1
