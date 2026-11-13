"""자료실 데이터 생성기 (계약 v4).

LLM 은 '설계도(DataPlan)' 만 쓴다 — 표 구조, 표 사이 ID 관계, 데이터에 심을 사실.
실제 행은 여기서 seed 고정으로 만든다. 그래서
- 같은 설계도·seed 면 항상 같은 CSV 가 나오고 (정답 재현 가능),
- 심은 사실이 정확히 들어가며, 몇 행에 적용됐는지를 코드가 계산해 비공개 hidden_checks 에 남긴다.
LLM 이 행을 직접 쓰면 값이 들쭉날쭉하고, "심었다" 고 말한 사실이 데이터에 없을 수 있다.
"""

from __future__ import annotations

import ast
import csv
import io
import operator
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from ..schemas import DatasetColumn, HiddenCheck, SampleDataset

MAX_TABLES = 12
MAX_ROWS_PER_TABLE = 2500
MAX_TOTAL_ROWS = 6000  # App ↔ AI 호출 입력 제한(2.1MB) 안에 초안 전체가 들어가도록

Dtype = Literal["string", "int", "float", "date", "bool"]


class ColumnPlan(BaseModel):
    """열 하나를 어떻게 만들지.

    gen 별로 쓰는 값:
    - id: prefix (예: "ST-" → ST-001, ST-002 …)
    - list: choices 를 순서대로 돌려 쓴다 (기준 정보 표의 이름 등)
    - choice: choices 중 무작위 (weights 로 비율 조절)
    - ref: ref="표.열" 의 값 중 하나 (다른 표를 가리키는 열)
    - lookup: via(이 표의 ref 열)로 찾은 상대 행에서 ref="표.열" 값을 복사 (예: 지점코드 → 지점명)
    - int / float: min ~ max 무작위
    - date: start ~ end 무작위
    - derived: expr 계산식 (예: "qty * unit_price"). + - * / 와 round/min/max 만 쓸 수 있다
    - const: value 고정값
    """

    name: str
    dtype: Dtype
    description: str
    gen: Literal["id", "list", "choice", "ref", "lookup", "int", "float", "date", "derived", "const"]
    prefix: str | None = None
    choices: list[str] | None = None
    weights: list[float] | None = None
    ref: str | None = None
    via: str | None = None
    min: float | None = None
    max: float | None = None
    start: date | None = None
    end: date | None = None
    expr: str | None = None
    value: str | None = None
    null_rate: float = Field(default=0.0, ge=0.0, le=0.3, description="빈 칸 비율 (id·ref 열에는 적용 안 함)")


class TablePlan(BaseModel):
    name: str = Field(description="파일 이름(확장자 제외), 영문 소문자_밑줄. 예: sales_daily")
    description: str = Field(description="파일 목록에 보여 줄 한 줄 설명")
    kind: Literal["master", "transaction", "snapshot", "event"] = "transaction"
    rows: int = Field(ge=1, le=MAX_ROWS_PER_TABLE)
    columns: list[ColumnPlan]
    sort_by: str | None = None


class Condition(BaseModel):
    column: str
    value: str


class FactPlan(BaseModel):
    """데이터에 심을 사실 하나. 코드가 정확히 적용하고 적용된 행 수를 기록한다.

    kind 별로 쓰는 값 (대상 행 = table 에서 where 조건과 date_column 기간에 맞는 행):
    - scale_values: 대상 행의 column 을 factor 배 (예: 특정 고객 주문이 4월부터 0.6배)
    - drop_rows: 대상 행을 지운다 (count 가 있으면 그만큼만). 예: 하루치 누락
    - duplicate_rows: 대상 행 중 count 개를 똑같이 한 번 더 넣는다. 예: 중복 전송
    - outliers: 대상 행 중 count 개의 column 을 factor 배 (기본 8배)
    - name_variants: 대상 행의 column 값을 variants 중 하나로 rate 비율만큼 바꾼다. 예: '강남점' → '강남 점'
    - set_value: 대상 행의 column 을 value 로 (count 가 있으면 그만큼만)
    - same_value: keys(표 첫 열 값 목록)에 해당하는 행들의 column 을 같은 값으로. 예: 다른 거래처 둘이 같은 계좌
    """

    id: str = Field(description="예: H1")
    title: str = Field(description="무엇을 심었는지 한 줄")
    story: str = Field(default="", description="이 사실이 회사 이야기에서 뜻하는 것")
    kind: Literal["scale_values", "drop_rows", "duplicate_rows", "outliers", "name_variants", "set_value", "same_value"]
    table: str
    where: list[Condition] = Field(default_factory=list)
    date_column: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    column: str | None = None
    count: int | None = Field(default=None, ge=1)
    factor: float | None = None
    value: str | None = None
    variants: list[str] | None = None
    rate: float | None = Field(default=None, gt=0.0, le=1.0)
    keys: list[str] | None = None
    how_to_check: str = Field(description="참여자가 이 사실을 알아챘는지 확인하는 방법")
    public: bool = Field(default=False, description="True 면 참여자에게 미리 알리는 한계(data_notes)로 공개")


class DataPlan(BaseModel):
    tables: list[TablePlan]
    facts: list[FactPlan] = Field(default_factory=list)


@dataclass
class GeneratedData:
    datasets: list[SampleDataset] = field(default_factory=list)
    hidden_checks: list[HiddenCheck] = field(default_factory=list)
    public_notes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # "[data] …" — 생성 그래프가 설계도를 다시 쓰게 한다


# ── 설계도 검사 ───────────────────────────────────────────


def _split_ref(ref: str | None) -> tuple[str, str] | None:
    if not ref or "." not in ref:
        return None
    t, c = ref.split(".", 1)
    return t.strip(), c.strip()


def check_plan(plan: DataPlan) -> list[str]:
    errors: list[str] = []
    tables = {t.name: t for t in plan.tables}
    if len(tables) != len(plan.tables):
        errors.append("[data] 표 이름이 중복됨")
    if not 2 <= len(plan.tables) <= MAX_TABLES:
        errors.append(f"[data] 표는 2~{MAX_TABLES}개여야 함 (현재 {len(plan.tables)})")
    total = sum(t.rows for t in plan.tables)
    if total > MAX_TOTAL_ROWS:
        errors.append(f"[data] 전체 행 수 {total} 가 상한 {MAX_TOTAL_ROWS} 를 넘음 — 표별 rows 를 줄일 것")

    for t in plan.tables:
        cols = {c.name: c for c in t.columns}
        if len(cols) != len(t.columns):
            errors.append(f"[data] {t.name}: 열 이름 중복")
        if t.sort_by and t.sort_by not in cols:
            errors.append(f"[data] {t.name}: sort_by 열 {t.sort_by} 없음")
        for c in t.columns:
            where = f"[data] {t.name}.{c.name}"
            if c.gen in ("ref", "lookup"):
                target = _split_ref(c.ref)
                if not target or target[0] not in tables or target[1] not in {x.name for x in tables[target[0]].columns}:
                    errors.append(f"{where}: ref '{c.ref}' 가 없는 표·열을 가리킴 ('표.열' 형식)")
            if c.gen == "lookup":
                via = cols.get(c.via or "")
                if not via or via.gen != "ref":
                    errors.append(f"{where}: lookup 의 via 는 이 표의 ref 열이어야 함")
                elif _split_ref(via.ref) and _split_ref(c.ref) and _split_ref(via.ref)[0] != _split_ref(c.ref)[0]:
                    errors.append(f"{where}: via 가 가리키는 표와 ref 의 표가 다름")
            if c.gen in ("list", "choice") and not c.choices and c.dtype != "bool":
                errors.append(f"{where}: {c.gen} 에는 choices 가 필요함")
            if c.gen == "derived":
                try:
                    names = {n.id for n in ast.walk(ast.parse(c.expr or "", mode="eval")) if isinstance(n, ast.Name)}
                except SyntaxError:
                    errors.append(f"{where}: 계산식 '{c.expr}' 문법 오류")
                    continue
                missing = names - set(cols) - {"round", "min", "max"}
                if missing:
                    errors.append(f"{where}: 계산식에 없는 열 {sorted(missing)}")
            if c.gen == "const" and c.value is None:
                errors.append(f"{where}: const 에는 value 가 필요함")

    for f in plan.facts:
        where = f"[data] 사실 {f.id}"
        t = tables.get(f.table)
        if not t:
            errors.append(f"{where}: 표 {f.table} 없음")
            continue
        cols = {c.name for c in t.columns}
        used = [x.column for x in f.where] + [f.date_column, f.column]
        for name in used:
            if name and name not in cols:
                errors.append(f"{where}: {f.table} 에 열 {name} 없음")
        if f.kind in ("scale_values", "outliers", "name_variants", "set_value", "same_value") and not f.column:
            errors.append(f"{where}: {f.kind} 에는 column 이 필요함")
        if f.kind == "name_variants" and not f.variants:
            errors.append(f"{where}: name_variants 에는 variants 가 필요함")
        if f.kind == "same_value" and not f.keys:
            errors.append(f"{where}: same_value 에는 keys 가 필요함")
        if f.kind == "set_value" and f.value is None:
            errors.append(f"{where}: set_value 에는 value 가 필요함")
        if f.kind in ("duplicate_rows", "outliers") and not f.count:
            errors.append(f"{where}: {f.kind} 에는 count 가 필요함")

    if not errors and _order(plan) is None:
        errors.append("[data] 표 사이 참조가 순환함")
    return errors


def _order(plan: DataPlan) -> list[TablePlan] | None:
    deps = {
        t.name: {_split_ref(c.ref)[0] for c in t.columns if c.gen in ("ref", "lookup") and _split_ref(c.ref)} - {t.name}
        for t in plan.tables
    }
    done: list[str] = []
    while len(done) < len(deps):
        ready = [n for n, d in deps.items() if n not in done and d <= set(done)]
        if not ready:
            return None
        done.extend(sorted(ready))
    by_name = {t.name: t for t in plan.tables}
    return [by_name[n] for n in done]


# ── 행 생성 ───────────────────────────────────────────────

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
_FUNCS = {"round": round, "min": min, "max": max}


def _eval(expr: str, row: dict) -> float:
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.Name):
            return float(row[n.id])
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            right = ev(n.right)
            if isinstance(n.op, ast.Div) and right == 0:
                return 0.0
            return _OPS[type(n.op)](ev(n.left), right)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -ev(n.operand)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS:
            return _FUNCS[n.func.id](*[ev(a) for a in n.args])
        raise ValueError(f"허용되지 않는 계산식: {expr}")

    return ev(ast.parse(expr, mode="eval"))


def _cast(value: float, dtype: Dtype):
    return int(round(value)) if dtype == "int" else round(float(value), 2)


def _gen_table(t: TablePlan, rng: random.Random, done: dict[str, list[dict]], plans: dict[str, TablePlan]) -> list[dict]:
    width = max(3, len(str(t.rows)))
    rows: list[dict] = []
    for i in range(t.rows):
        row: dict = {}
        for c in t.columns:
            match c.gen:
                case "id":
                    row[c.name] = f"{c.prefix or ''}{i + 1:0{width}d}"
                case "list":
                    choices = c.choices or ["true", "false"]
                    row[c.name] = choices[i % len(choices)]
                case "choice":
                    choices = c.choices or ["true", "false"]
                    weights = c.weights if c.weights and len(c.weights) == len(choices) else None
                    row[c.name] = rng.choices(choices, weights=weights)[0]
                case "ref":
                    pt, pc = _split_ref(c.ref)
                    row[c.name] = rng.choice(done[pt])[pc]
                case "int" | "float":
                    lo = c.min if c.min is not None else 0
                    hi = c.max if c.max is not None else 1000
                    row[c.name] = _cast(rng.uniform(lo, hi), c.dtype)
                case "date":
                    start = c.start or date(2026, 1, 1)
                    end = c.end or start + timedelta(days=90)
                    row[c.name] = start + timedelta(days=rng.randint(0, max((end - start).days, 0)))
                case "const":
                    row[c.name] = c.value
                case _:
                    row[c.name] = None  # lookup / derived 는 아래에서
        for c in t.columns:  # lookup: 같은 행의 ref 값으로 상대 행을 찾아 복사
            if c.gen == "lookup":
                via = next(x for x in t.columns if x.name == c.via)
                pt, key = _split_ref(via.ref)
                _, pc = _split_ref(c.ref)
                parent = next((p for p in done[pt] if p[key] == row[via.name]), None)
                row[c.name] = parent[pc] if parent else ""
        for c in t.columns:  # derived: 선언 순서대로 (앞의 derived 를 뒤에서 쓸 수 있다)
            if c.gen == "derived":
                row[c.name] = _cast(_eval(c.expr or "0", row), c.dtype)
        rows.append(row)

    keys_used_elsewhere = {
        _split_ref(c.ref)[1]
        for p in plans.values()
        for c in p.columns
        if c.gen in ("ref", "lookup") and _split_ref(c.ref) and _split_ref(c.ref)[0] == t.name
    }
    for c in t.columns:  # 빈 칸은 키로 쓰이지 않는 열에만
        if c.null_rate and c.gen not in ("id", "ref") and c.name not in keys_used_elsewhere:
            for row in rows:
                if rng.random() < c.null_rate:
                    row[c.name] = ""
    return rows


# ── 사실 심기 ─────────────────────────────────────────────


def _matches(row: dict, f: FactPlan) -> bool:
    if any(str(row.get(w.column, "")) != w.value for w in f.where):
        return False
    if f.date_column:
        v = row.get(f.date_column)
        if not isinstance(v, date):
            return False
        if (f.date_from and v < f.date_from) or (f.date_to and v > f.date_to):
            return False
    return True


def _scope(f: FactPlan) -> str:
    parts = [f"{w.column}={w.value}" for w in f.where]
    if f.date_column and (f.date_from or f.date_to):
        parts.append(f"{f.date_column} {f.date_from or ''}~{f.date_to or ''}")
    return ", ".join(parts) or "전체"


def _apply(f: FactPlan, rows: list[dict], t: TablePlan, seed: int) -> tuple[int, str]:
    """사실을 적용하고 (영향 행 수, 위치 설명) 을 돌려준다."""
    rng = random.Random(f"{seed}:{f.id}")
    dtype = {c.name: c.dtype for c in t.columns}
    targets = [r for r in rows if _matches(r, f)]
    scope = _scope(f)

    def numeric(r, factor):
        v = r.get(f.column)
        if v in ("", None):
            return False
        r[f.column] = _cast(float(v) * factor, dtype[f.column])
        return True

    match f.kind:
        case "scale_values":
            n = sum(numeric(r, f.factor if f.factor is not None else 0.5) for r in targets)
            return n, f"{t.name}.csv · {scope} · {f.column} {f.factor}배 · {n}행"
        case "drop_rows":
            picked = rng.sample(targets, min(f.count, len(targets))) if f.count else targets
            ids = {id(r) for r in picked}
            rows[:] = [r for r in rows if id(r) not in ids]
            return len(picked), f"{t.name}.csv · {scope} · {len(picked)}행 삭제"
        case "duplicate_rows":
            picked = rng.sample(targets, min(f.count or 1, len(targets)))
            rows.extend(dict(r) for r in picked)
            return len(picked), f"{t.name}.csv · {scope} · {len(picked)}행이 두 번씩"
        case "outliers":
            picked = rng.sample(targets, min(f.count or 1, len(targets)))
            n = sum(numeric(r, f.factor or 8.0) for r in picked)
            return n, f"{t.name}.csv · {scope} · {f.column} {f.factor or 8.0}배 · {n}행"
        case "name_variants":
            n = 0
            for r in targets:
                if rng.random() < (f.rate or 0.3):
                    r[f.column] = rng.choice(f.variants)
                    n += 1
            if n == 0 and targets:
                rng.choice(targets)[f.column] = rng.choice(f.variants)
                n = 1
            return n, f"{t.name}.csv · {scope} · {f.column} 표기 {f.variants} · {n}행"
        case "set_value":
            picked = rng.sample(targets, min(f.count, len(targets))) if f.count else targets
            for r in picked:
                r[f.column] = f.value
            return len(picked), f"{t.name}.csv · {scope} · {f.column}={f.value} · {len(picked)}행"
        case "same_value":
            key = t.columns[0].name
            picked = [r for r in rows if str(r.get(key)) in set(f.keys or [])]
            value = f.value if f.value is not None else (picked[0][f.column] if picked else None)
            for r in picked:
                r[f.column] = value
            return len(picked), f"{t.name}.csv · {key} {f.keys} · {f.column} 같은 값 · {len(picked)}행"
    return 0, ""


# ── 진입점 ────────────────────────────────────────────────


def _to_csv(t: TablePlan, rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow([c.name for c in t.columns])
    for r in rows:
        w.writerow(["" if r.get(c.name) is None else (r[c.name].isoformat() if isinstance(r[c.name], date) else r[c.name]) for c in t.columns])
    return buf.getvalue()


def build_dataset(plan: DataPlan, seed: int) -> GeneratedData:
    """설계도 → CSV 여러 개 + 비공개 hidden_checks + 공개 한계. 같은 (plan, seed) 면 항상 같다."""
    out = GeneratedData(errors=check_plan(plan))
    if out.errors:
        return out
    rng = random.Random(seed)
    plans = {t.name: t for t in plan.tables}
    data: dict[str, list[dict]] = {}
    for t in _order(plan):
        data[t.name] = _gen_table(t, rng, data, plans)

    # 중복 행은 마지막에 만든다. 먼저 만들면 뒤의 사실(표기 변형 등)이 복사본 한쪽만 바꿔 '같은 행' 이 아니게 된다.
    for f in sorted(plan.facts, key=lambda x: x.kind == "duplicate_rows"):
        n, location = _apply(f, data[f.table], plans[f.table], seed)
        if n == 0:
            out.errors.append(f"[data] 사실 {f.id} 가 0행에 적용됨 — where·기간 조건이 실제 값과 맞는지 고칠 것")
        elif f.public:
            out.public_notes.append(f.title)
        else:
            out.hidden_checks.append(HiddenCheck(id=f.id, title=f.title, location=location, how_to_check=f.how_to_check))

    order = {f.id: i for i, f in enumerate(plan.facts)}
    out.hidden_checks.sort(key=lambda h: order.get(h.id, 0))

    for t in plan.tables:
        rows = data[t.name]
        if t.sort_by:
            rows.sort(key=lambda r: (str(r.get(t.sort_by) or ""),))
        out.datasets.append(
            SampleDataset(
                filename=f"{t.name}.csv",
                columns=[
                    DatasetColumn(
                        name=c.name,
                        dtype=c.dtype,
                        description=c.description,
                        references=c.ref if c.gen == "ref" else None,
                    )
                    for c in t.columns
                ],
                csv=_to_csv(t, rows),
                seed=seed,
                description=t.description,
            )
        )
    return out


__all__ = [
    "ColumnPlan",
    "Condition",
    "DataPlan",
    "FactPlan",
    "GeneratedData",
    "TablePlan",
    "build_dataset",
    "check_plan",
]
