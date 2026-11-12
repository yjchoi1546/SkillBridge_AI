"""샘플 데이터 생성.

LLM 은 컬럼·범위·이상치 비율 같은 '설계(DatasetSpec)'만 만들고, 실제 행은 여기서 seed 고정으로
생성한다. LLM 이 CSV 행을 직접 쓰면 값이 들쭉날쭉해 사전 정의 테스트의 정답을 재현할 수 없다.
"""

import csv
import io
import random
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from ..schemas import HiddenCheck


class ColumnSpec(BaseModel):
    name: str
    dtype: Literal["string", "int", "float", "date", "bool"]
    description: str
    choices: list[str] | None = Field(default=None, description="string 컬럼의 후보 값")
    min: float | None = None
    max: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    null_rate: float = Field(default=0.0, ge=0.0, le=0.5, description="결측 비율")
    anomaly_rate: float = Field(default=0.0, ge=0.0, le=0.2, description="숫자 이상치 비율")


class DatasetSpec(BaseModel):
    filename: str
    columns: list[ColumnSpec]
    n_rows: int = Field(ge=10, le=5000)


def _value(col: ColumnSpec, rng: random.Random) -> str:
    if col.null_rate and rng.random() < col.null_rate:
        return ""
    match col.dtype:
        case "string":
            return rng.choice(col.choices) if col.choices else f"{col.name}_{rng.randint(1, 99)}"
        case "int" | "float":
            lo, hi = col.min if col.min is not None else 0, col.max if col.max is not None else 1000
            v = rng.uniform(lo, hi)
            if col.anomaly_rate and rng.random() < col.anomaly_rate:
                v *= rng.uniform(5, 10)
            return str(round(v)) if col.dtype == "int" else f"{v:.2f}"
        case "date":
            start = col.start_date or date(2026, 1, 1)
            end = col.end_date or start + timedelta(days=90)
            return (start + timedelta(days=rng.randint(0, max((end - start).days, 0)))).isoformat()
        case "bool":
            return rng.choice(["true", "false"])


def generate_csv(spec: DatasetSpec, seed: int) -> str:
    """같은 (spec, seed) 면 항상 같은 CSV 를 만든다."""
    rng = random.Random(seed)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([c.name for c in spec.columns])
    for _ in range(spec.n_rows):
        writer.writerow([_value(c, rng) for c in spec.columns])
    return buf.getvalue()


def hidden_checks_from_spec(spec: DatasetSpec) -> list[HiddenCheck]:
    """생성 설정에서 실제로 심긴 데이터 함정을 목록으로 만든다 (기업·평가 전용).

    LLM 설명이 아니라 생성기 설정에서 계산하므로, 목록에 있는 함정은 데이터에 실제로 있다.
    TODO(AI-A): A4 에서 중복 행·표기 변형·누락일 같은 함정을 추가하면 여기에도 반영한다.
    """
    checks: list[HiddenCheck] = []
    for col in spec.columns:
        if col.null_rate:
            checks.append(
                HiddenCheck(
                    id=f"H{len(checks) + 1}",
                    title=f"{col.name} 결측",
                    location=f"{spec.filename} 의 {col.name} 컬럼, 약 {col.null_rate:.0%} 행",
                    how_to_check="결측을 발견해 처리했고, 처리 기준(제외·대체 등)과 영향을 설명했는지 확인",
                )
            )
        if col.anomaly_rate and col.dtype in ("int", "float"):
            checks.append(
                HiddenCheck(
                    id=f"H{len(checks) + 1}",
                    title=f"{col.name} 이상치 (정상 범위의 5~10배)",
                    location=f"{spec.filename} 의 {col.name} 컬럼, 약 {col.anomaly_rate:.0%} 행",
                    how_to_check="이상치를 그대로 합산하지 않고, 판단 기준과 처리 방법을 설명했는지 확인",
                )
            )
    return checks
