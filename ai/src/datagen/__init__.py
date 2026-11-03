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
